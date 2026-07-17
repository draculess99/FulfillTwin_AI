from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import IsolationForest
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBClassifier, XGBRegressor
except Exception:  # pragma: no cover
    XGBClassifier = None  # type: ignore[assignment]
    XGBRegressor = None  # type: ignore[assignment]


FEATURES = [
    "order_volume_pct",
    "absenteeism_pct",
    "conveyor_capacity_pct",
    "dock_congestion_pct",
    "energy_price_pct",
    "inventory_availability_pct",
    "current_backlog",
    "workers",
    "base_throughput",
    "horizon_hours",
]

REGIME_NAMES = {
    0: "stable",
    1: "labor-constrained",
    2: "equipment-constrained",
    3: "demand-surge",
}


class OperationalMLEngine:
    """XGBoost + anomaly detection + clustering for tabular operations data."""

    def __init__(self, artifact_dir: Path, seed: int = 42, rows: int = 3500) -> None:
        self.artifact_dir = artifact_dir
        self.seed = seed
        self.rows = rows
        self.bundle_path = artifact_dir / "model_bundle.joblib"
        self.metrics_path = artifact_dir / "metrics.json"
        self.regressor = None
        self.classifier = None
        self.scaler = None
        self.clusterer = None
        self.anomaly = None
        self.metrics: dict[str, Any] = {}
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.load_or_train()

    def load_or_train(self) -> None:
        try:
            bundle = joblib.load(self.bundle_path)
            self.regressor = bundle["regressor"]
            self.classifier = bundle["classifier"]
            self.scaler = bundle["scaler"]
            self.clusterer = bundle["clusterer"]
            self.anomaly = bundle["anomaly"]
            self.metrics = json.loads(self.metrics_path.read_text(encoding="utf-8"))
        except Exception:
            self.train()

    def _generate_training_data(self) -> pd.DataFrame:
        rng = np.random.default_rng(self.seed)
        n = self.rows
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

    def train(self) -> dict[str, Any]:
        if XGBRegressor is None or XGBClassifier is None:
            raise RuntimeError("xgboost is required. Install dependencies from requirements.txt")
        df = self._generate_training_data()
        X = df[FEATURES]
        y_reg = df["future_backlog"]
        y_cls = df["sla_breach"]
        X_train, X_test, y_reg_train, y_reg_test, y_cls_train, y_cls_test = train_test_split(
            X, y_reg, y_cls, test_size=0.22, random_state=self.seed, stratify=y_cls
        )
        self.regressor = XGBRegressor(
            n_estimators=260,
            max_depth=5,
            learning_rate=0.045,
            subsample=0.88,
            colsample_bytree=0.88,
            objective="reg:squarederror",
            random_state=self.seed,
            n_jobs=2,
        )
        self.classifier = XGBClassifier(
            n_estimators=240,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=self.seed,
            n_jobs=2,
        )
        self.regressor.fit(X_train, y_reg_train)
        self.classifier.fit(X_train, y_cls_train)
        reg_pred = self.regressor.predict(X_test)
        cls_prob = self.classifier.predict_proba(X_test)[:, 1]
        cls_pred = (cls_prob >= 0.5).astype(int)

        self.scaler = StandardScaler().fit(X_train)
        scaled_train = self.scaler.transform(X_train)
        self.clusterer = KMeans(n_clusters=4, random_state=self.seed, n_init=20).fit(scaled_train)
        self.anomaly = IsolationForest(
            n_estimators=220,
            contamination=0.06,
            random_state=self.seed,
            n_jobs=2,
        ).fit(scaled_train)

        try:
            auc = float(roc_auc_score(y_cls_test, cls_prob))
        except ValueError:
            auc = 0.0
        self.metrics = {
            "training_rows": int(len(df)),
            "regression_mae": round(float(mean_absolute_error(y_reg_test, reg_pred)), 2),
            "regression_r2": round(float(r2_score(y_reg_test, reg_pred)), 4),
            "classification_accuracy": round(float(accuracy_score(y_cls_test, cls_pred)), 4),
            "classification_roc_auc": round(auc, 4),
            "breach_rate": round(float(y_cls.mean()), 4),
            "features": FEATURES,
            "models": {
                "backlog": "XGBoost Regressor",
                "sla_risk": "XGBoost Classifier",
                "anomaly": "Isolation Forest",
                "operating_regime": "K-means (k=4)",
            },
        }
        joblib.dump(
            {
                "regressor": self.regressor,
                "classifier": self.classifier,
                "scaler": self.scaler,
                "clusterer": self.clusterer,
                "anomaly": self.anomaly,
            },
            self.bundle_path,
        )
        self.metrics_path.write_text(json.dumps(self.metrics, indent=2), encoding="utf-8")
        return self.metrics

    def predict(self, scenario: dict[str, Any]) -> dict[str, Any]:
        if any(model is None for model in [self.regressor, self.classifier, self.scaler, self.clusterer, self.anomaly]):
            self.load_or_train()
        row = pd.DataFrame([{feature: float(scenario[feature]) for feature in FEATURES}])
        backlog = max(0.0, float(self.regressor.predict(row)[0]))
        breach_prob = float(self.classifier.predict_proba(row)[0, 1])
        scaled = self.scaler.transform(row)
        cluster = int(self.clusterer.predict(scaled)[0])
        anomaly_decision = float(self.anomaly.decision_function(scaled)[0])
        anomaly_score = 1.0 / (1.0 + math.exp(6.0 * anomaly_decision))
        importances = dict(zip(FEATURES, [float(v) for v in self.classifier.feature_importances_]))
        top_factors = sorted(importances.items(), key=lambda item: item[1], reverse=True)[:5]
        return {
            "predicted_backlog": round(backlog),
            "sla_breach_probability": round(breach_prob, 4),
            "anomaly_score": round(float(anomaly_score), 4),
            "operating_regime": REGIME_NAMES.get(cluster, f"regime-{cluster}"),
            "top_model_factors": [{"feature": key, "importance": round(value, 4)} for key, value in top_factors],
        }

    def model_card(self) -> dict[str, Any]:
        return {
            "purpose": "Predict short-horizon fulfillment backlog and SLA-breach risk from tabular operating conditions.",
            "approved_uses": ["scenario planning", "incident triage", "human-reviewed labor and recovery recommendations"],
            "prohibited_uses": ["automatic discipline", "individual worker scoring", "safety-critical control without human approval"],
            "limitations": [
                "The bundled model is trained on synthetic data and must be retrained on site-specific history before production use.",
                "Predictions outside the training distribution should be treated as low confidence.",
                "Clustering labels describe operating regimes, not employee performance.",
            ],
            "metrics": self.metrics,
        }
