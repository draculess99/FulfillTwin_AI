from __future__ import annotations

import csv
import datetime
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    recall_score,
    r2_score,
    roc_auc_score,
)

from fulfilltwin.backend.services.ml_engine import FEATURES, OperationalMLEngine
from fulfilltwin.backend.services.optimizer import RecoveryOptimizer
from fulfilltwin.backend.services.recovery_simulator import RecoverySimulator


class BenchmarkEngine:
    def __init__(self, ml_engine: OperationalMLEngine, artifact_dir: Path, seed: int = 999) -> None:
        self.ml_engine = ml_engine
        self.artifact_dir = artifact_dir
        self.seed = seed
        self.n_scenarios = 1000
        self.json_path = artifact_dir / "benchmark_results.json"
        self.csv_path = artifact_dir / "benchmark_results.csv"

    def _generate_benchmark_data(self) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)
        n = self.n_scenarios

        df = pd.DataFrame(
            {
                "order_volume_pct": rng.normal(8, 28, n).clip(-30, 90),
                "absenteeism_pct": rng.beta(2, 8, n) * 38,
                "conveyor_capacity_pct": rng.normal(88, 16, n).clip(25, 110),
                "dock_congestion_pct": rng.beta(2.5, 3.5, n) * 100,
                "energy_price_pct": rng.normal(15, 35, n).clip(-25, 140),
                "inventory_availability_pct": rng.normal(92, 10, n).clip(45, 100),
                "current_backlog": rng.gamma(3.5, 210, n).clip(0, 5000),
                "workers": rng.integers(45, 260, n),
                "base_throughput": rng.normal(1300, 300, n).clip(500, 2600),
                "horizon_hours": rng.integers(1, 13, n),
            }
        )

        presets = rng.integers(0, 4, n)
        # 1: Labor-constrained
        df.loc[presets == 1, "absenteeism_pct"] = rng.normal(30, 5, sum(presets == 1)).clip(15, 45)
        # 2: Equipment-constrained
        df.loc[presets == 2, "conveyor_capacity_pct"] = rng.normal(45, 10, sum(presets == 2)).clip(20, 65)
        # 3: Demand-surge
        df.loc[presets == 3, "order_volume_pct"] = rng.normal(60, 15, sum(presets == 3)).clip(30, 100)

        demand = df["base_throughput"] * (1 + df["order_volume_pct"] / 100)
        labor_factor = (1 - df["absenteeism_pct"] / 100).clip(0.45, 1)
        equipment_factor = (df["conveyor_capacity_pct"] / 100).clip(0.25, 1.05)
        inventory_factor = (df["inventory_availability_pct"] / 100).clip(0.45, 1)
        dock_factor = (1 - 0.38 * df["dock_congestion_pct"] / 100).clip(0.55, 1)
        worker_factor = (df["workers"] / 145).clip(0.45, 1.65)
        effective = df["base_throughput"] * labor_factor * equipment_factor * inventory_factor * dock_factor * worker_factor
        horizon_load = (demand - effective) * df["horizon_hours"]
        nonlinear = 0.08 * np.maximum(df["order_volume_pct"], 0) ** 2 + 12 * np.maximum(df["absenteeism_pct"] - 12, 0)
        noise = rng.normal(0, 110, n)
        df["future_backlog"] = (df["current_backlog"] + horizon_load + nonlinear + noise).clip(0, 15000)
        df["sla_breach"] = (
            (df["future_backlog"] > 2600)
            | ((df["conveyor_capacity_pct"] < 55) & (df["order_volume_pct"] > 15))
            | ((df["absenteeism_pct"] > 22) & (df["current_backlog"] > 900))
        ).astype(int)
        return df

    def run_benchmark(self, n_resamples: int = 1000) -> dict[str, Any]:
        df = self._generate_benchmark_data()
        X = df[FEATURES]
        y_reg = df["future_backlog"].values
        y_cls = df["sla_breach"].values

        reg_pred = self.ml_engine.regressor.predict(X)
        cls_prob = self.ml_engine.classifier.predict_proba(X)[:, 1]
        cls_pred = (cls_prob >= 0.5).astype(int)

        def calc_metrics(y_r, p_r, y_c, p_c, p_c_prob):
            try:
                auc = float(roc_auc_score(y_c, p_c_prob))
            except ValueError:
                auc = 0.0
            return {
                "regression_mae": float(mean_absolute_error(y_r, p_r)),
                "regression_rmse": float(np.sqrt(mean_squared_error(y_r, p_r))),
                "regression_r2": float(r2_score(y_r, p_r)),
                "classification_accuracy": float(accuracy_score(y_c, p_c)),
                "classification_balanced_accuracy": float(balanced_accuracy_score(y_c, p_c)),
                "classification_precision": float(precision_score(y_c, p_c, zero_division=0)),
                "classification_recall": float(recall_score(y_c, p_c, zero_division=0)),
                "classification_f1": float(f1_score(y_c, p_c, zero_division=0)),
                "classification_roc_auc": auc,
            }

        point_estimates = calc_metrics(y_reg, reg_pred, y_cls, cls_pred, cls_prob)

        rng = np.random.default_rng(self.seed)
        bootstraps = {k: [] for k in point_estimates.keys()}
        
        # Calculate 95% bootstrap confidence intervals
        for _ in range(n_resamples):
            indices = rng.choice(len(df), size=len(df), replace=True)
            bm = calc_metrics(
                y_reg[indices], reg_pred[indices], y_cls[indices], cls_pred[indices], cls_prob[indices]
            )
            for k, v in bm.items():
                bootstraps[k].append(v)

        metrics = {}
        for k, v in point_estimates.items():
            lower = float(np.percentile(bootstraps[k], 2.5))
            upper = float(np.percentile(bootstraps[k], 97.5))
            metrics[k] = {
                "value": round(v, 4),
                "ci_lower": round(lower, 4),
                "ci_upper": round(upper, 4),
            }

        # Prepare ML predictions for simulator
        ml_predictions = []
        for r, p in zip(reg_pred, cls_prob):
            ml_predictions.append({
                "predicted_backlog": float(max(0, r)),
                "sla_breach_probability": float(p)
            })
            
        simulator = RecoverySimulator(RecoveryOptimizer())
        sim_results = simulator.simulate(df, ml_predictions)

        results = {
            "metadata": {
                "evaluation_seed": self.seed,
                "evaluation_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "model_version": "v1.0-xgb",
                "data_description": "held-out synthetic validation scenarios covering 4 presets",
                "sample_size": self.n_scenarios,
                "bootstrap_resamples": n_resamples,
                "positive_class_rate": round(float(y_cls.mean()), 4),
            },
            "metrics": metrics,
            "confusion_matrix": confusion_matrix(y_cls, cls_pred).tolist(),
            "operational_benchmark": sim_results
        }

        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        self.json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

        with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value", "CI_Lower_95", "CI_Upper_95"])
            for k, v in metrics.items():
                writer.writerow([k, v["value"], v["ci_lower"], v["ci_upper"]])
            
            # Append simulator results to CSV as well
            writer.writerow([])
            writer.writerow(["Operational Benchmark", "Value", "", ""])
            writer.writerow(["mean_simulated_backlog_reduction", sim_results["mean_simulated_backlog_reduction"], "", ""])
            writer.writerow(["median_simulated_backlog_reduction", sim_results["median_simulated_backlog_reduction"], "", ""])
            writer.writerow(["mean_simulated_incident_cost_difference", sim_results["mean_simulated_incident_cost_difference"], "", ""])
            writer.writerow(["sla_breach_difference", sim_results["sla_breach_difference"], "", ""])
            writer.writerow(["percentage_ft_beats_fixed_baseline", sim_results["percentage_ft_beats_fixed_baseline"], "", ""])
            writer.writerow(["human_approval_rate", sim_results["human_approval_rate"], "", ""])

        return results
