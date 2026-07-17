from __future__ import annotations

from typing import Any


class RecoveryOptimizer:
    """Transparent candidate-plan optimizer using deterministic cost scoring."""

    def generate_plans(self, scenario: dict[str, float], predictions: dict[str, Any]) -> list[dict[str, Any]]:
        backlog = float(predictions["predicted_backlog"])
        breach = float(predictions["sla_breach_probability"])
        plans = [
            {
                "name": "Balanced recovery",
                "labor_reallocation": min(30, round(max(4, scenario["absenteeism_pct"] * 0.8 + scenario["order_volume_pct"] * 0.12))),
                "overtime_hours": 2 if breach >= 0.45 else 0,
                "release_throttle_pct": 15 if scenario["conveyor_capacity_pct"] < 75 else 5,
                "maintenance_priority": "high" if scenario["conveyor_capacity_pct"] < 75 else "normal",
                "energy_shift_pct": 15 if scenario["energy_price_pct"] > 35 else 5,
            },
            {
                "name": "Service-first recovery",
                "labor_reallocation": min(45, round(max(8, scenario["absenteeism_pct"] + scenario["order_volume_pct"] * 0.18))),
                "overtime_hours": 4 if breach >= 0.55 else 2,
                "release_throttle_pct": 8 if scenario["conveyor_capacity_pct"] >= 60 else 22,
                "maintenance_priority": "critical" if scenario["conveyor_capacity_pct"] < 65 else "high",
                "energy_shift_pct": 5,
            },
            {
                "name": "Cost-controlled recovery",
                "labor_reallocation": min(22, round(max(3, scenario["absenteeism_pct"] * 0.55))),
                "overtime_hours": 0,
                "release_throttle_pct": 25 if scenario["conveyor_capacity_pct"] < 80 else 12,
                "maintenance_priority": "high" if scenario["conveyor_capacity_pct"] < 60 else "normal",
                "energy_shift_pct": 28 if scenario["energy_price_pct"] > 25 else 12,
            },
        ]
        for plan in plans:
            capacity_gain = plan["labor_reallocation"] * 16 + plan["overtime_hours"] * scenario["workers"] * 2.2
            throttle_loss = plan["release_throttle_pct"] * 7
            estimated_reduction = max(0, min(backlog * 0.72, capacity_gain + throttle_loss))
            labor_cost = plan["labor_reallocation"] * 38 + plan["overtime_hours"] * scenario["workers"] * 9.5
            maintenance_cost = {"normal": 300, "high": 1200, "critical": 2600}[plan["maintenance_priority"]]
            energy_savings = plan["energy_shift_pct"] * max(0, scenario["energy_price_pct"]) * 1.3
            residual_backlog = max(0, backlog - estimated_reduction)
            service_penalty = residual_backlog * (2.8 + breach * 4.5)
            total_cost = labor_cost + maintenance_cost + service_penalty - energy_savings
            plan.update(
                {
                    "estimated_backlog_reduction": round(estimated_reduction),
                    "residual_backlog": round(residual_backlog),
                    "estimated_total_cost": round(max(0, total_cost), 2),
                    "requires_human_approval": plan["overtime_hours"] > 0 or plan["labor_reallocation"] >= 20,
                }
            )
        return sorted(plans, key=lambda item: item["estimated_total_cost"])
