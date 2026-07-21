from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from fulfilltwin.backend.services.optimizer import RecoveryOptimizer


class RecoverySimulator:
    """Evaluates optimizer logic against fixed baselines over a benchmark dataset."""

    def __init__(self, optimizer: RecoveryOptimizer) -> None:
        self.optimizer = optimizer

    def _evaluate_no_intervention(self, scenario: dict[str, Any], backlog: float, breach: float) -> dict[str, Any]:
        estimated_reduction = 0.0
        residual_backlog = backlog
        service_penalty = residual_backlog * (2.8 + breach * 4.5)
        total_cost = service_penalty
        return {
            "name": "No intervention",
            "estimated_backlog_reduction": 0,
            "residual_backlog": round(residual_backlog),
            "estimated_total_cost": round(total_cost, 2),
            "requires_human_approval": False,
        }

    def simulate(self, df: pd.DataFrame, ml_predictions: list[dict[str, Any]]) -> dict[str, Any]:
        results: dict[str, dict[str, list[float]]] = {
            "no_intervention": {"backlog_reductions": [], "costs": [], "breaches": []},
            "fixed_balanced": {"backlog_reductions": [], "costs": [], "breaches": []},
            "fixed_service_first": {"backlog_reductions": [], "costs": [], "breaches": []},
            "fixed_cost_controlled": {"backlog_reductions": [], "costs": [], "breaches": []},
            "fulfilltwin_selected": {"backlog_reductions": [], "costs": [], "breaches": [], "approvals": []},
        }

        plan_selection_counts: dict[str, int] = {}
        ft_beats_baseline_count = 0
        total_scenarios = len(df)

        for idx in range(total_scenarios):
            scenario = df.iloc[idx].to_dict()
            pred = ml_predictions[idx]

            plans = self.optimizer.generate_plans(scenario, pred)
            no_int = self._evaluate_no_intervention(scenario, float(pred["predicted_backlog"]), float(pred["sla_breach_probability"]))

            # Map the generated plans
            plans_dict = {}
            for p in plans:
                norm_name = p["name"].lower().replace(" ", "_").replace("-", "_")
                # e.g. "balanced_recovery", "service_first_recovery", "cost_controlled_recovery"
                plans_dict[norm_name] = p

            best_plan = plans[0]

            plan_selection_counts[best_plan["name"]] = plan_selection_counts.get(best_plan["name"], 0) + 1

            # Compare against the average of fixed plans as baseline
            avg_fixed_cost = np.mean([
                plans_dict["balanced_recovery"]["estimated_total_cost"],
                plans_dict["service_first_recovery"]["estimated_total_cost"],
                plans_dict["cost_controlled_recovery"]["estimated_total_cost"]
            ])
            
            if best_plan["estimated_total_cost"] < avg_fixed_cost:
                ft_beats_baseline_count += 1

            def log_plan(group: str, plan: dict[str, Any]) -> None:
                # breach occurs if residual backlog > 2600 based on ml_engine threshold
                breach = 1 if plan["residual_backlog"] > 2600 else 0
                results[group]["backlog_reductions"].append(plan["estimated_backlog_reduction"])
                results[group]["costs"].append(plan["estimated_total_cost"])
                results[group]["breaches"].append(breach)

            log_plan("no_intervention", no_int)
            log_plan("fixed_balanced", plans_dict["balanced_recovery"])
            log_plan("fixed_service_first", plans_dict["service_first_recovery"])
            log_plan("fixed_cost_controlled", plans_dict["cost_controlled_recovery"])
            log_plan("fulfilltwin_selected", best_plan)

            results["fulfilltwin_selected"]["approvals"].append(1 if best_plan["requires_human_approval"] else 0)

        def agg(group: str) -> dict[str, float]:
            return {
                "mean_backlog_reduction": round(float(np.mean(results[group]["backlog_reductions"])), 2),
                "median_backlog_reduction": round(float(np.median(results[group]["backlog_reductions"])), 2),
                "mean_total_cost": round(float(np.mean(results[group]["costs"])), 2),
                "sla_breach_rate": round(float(np.mean(results[group]["breaches"])), 4),
            }

        no_int_agg = agg("no_intervention")
        ft_agg = agg("fulfilltwin_selected")

        summary = {
            "label": "simulated operational benchmark results",
            "mean_simulated_backlog_reduction": ft_agg["mean_backlog_reduction"],
            "median_simulated_backlog_reduction": ft_agg["median_backlog_reduction"],
            "mean_simulated_incident_cost_difference": round(ft_agg["mean_total_cost"] - no_int_agg["mean_total_cost"], 2),
            "sla_breach_difference": round(ft_agg["sla_breach_rate"] - no_int_agg["sla_breach_rate"], 4),
            "percentage_ft_beats_fixed_baseline": round(float(ft_beats_baseline_count / total_scenarios), 4),
            "plan_selection_distribution": {k: round(float(v / total_scenarios), 4) for k, v in plan_selection_counts.items()},
            "human_approval_rate": round(float(np.mean(results["fulfilltwin_selected"]["approvals"])), 4),
            "baselines": {
                "no_intervention": no_int_agg,
                "fixed_balanced": agg("fixed_balanced"),
                "fixed_service_first": agg("fixed_service_first"),
                "fixed_cost_controlled": agg("fixed_cost_controlled"),
            },
        }
        return summary
