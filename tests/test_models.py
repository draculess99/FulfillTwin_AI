from pathlib import Path

from fulfilltwin.backend.services.ml_engine import OperationalMLEngine


def scenario():
    return {
        "order_volume_pct": 35,
        "absenteeism_pct": 9,
        "conveyor_capacity_pct": 48,
        "dock_congestion_pct": 55,
        "energy_price_pct": 20,
        "inventory_availability_pct": 91,
        "current_backlog": 1100,
        "workers": 145,
        "base_throughput": 1350,
        "horizon_hours": 6,
    }


def test_ml_engine_predicts(tmp_path: Path):
    engine = OperationalMLEngine(tmp_path, seed=7, rows=700)
    result = engine.predict(scenario())
    assert result["predicted_backlog"] >= 0
    assert 0 <= result["sla_breach_probability"] <= 1
    assert 0 <= result["anomaly_score"] <= 1
    assert engine.metrics["regression_r2"] > 0.5
