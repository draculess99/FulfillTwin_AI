import pytest
import pandas as pd
from fulfilltwin.backend.services.optimizer import RecoveryOptimizer
from fulfilltwin.backend.services.recovery_simulator import RecoverySimulator

def test_optimizer_baseline_comparisons():
    optimizer = RecoveryOptimizer()
    simulator = RecoverySimulator(optimizer)
    
    df = pd.DataFrame([{
        "order_volume_pct": 50,
        "absenteeism_pct": 20,
        "conveyor_capacity_pct": 60,
        "dock_congestion_pct": 50,
        "energy_price_pct": 20,
        "inventory_availability_pct": 80,
        "current_backlog": 1000,
        "workers": 100,
        "base_throughput": 1500,
        "horizon_hours": 8,
    }])
    
    preds = [{
        "predicted_backlog": 3000,
        "sla_breach_probability": 0.8
    }]
    
    results = simulator.simulate(df, preds)
    
    assert "label" in results
    assert results["label"] == "simulated operational benchmark results"
    assert "mean_simulated_backlog_reduction" in results
    assert "baselines" in results
    assert "no_intervention" in results["baselines"]
