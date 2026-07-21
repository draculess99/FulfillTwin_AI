import pytest
from pathlib import Path
from fulfilltwin.backend.services.ml_engine import OperationalMLEngine
from fulfilltwin.backend.services.benchmark_engine import BenchmarkEngine

def test_benchmark_engine_metrics_generation(tmp_path):
    # Train the ML engine briefly
    ml = OperationalMLEngine(tmp_path, seed=42, rows=100)
    engine = BenchmarkEngine(ml, tmp_path, seed=99)
    # Use smaller resamples for fast testing
    results = engine.run_benchmark(n_resamples=2)
    
    # Check all metrics are generated
    assert "metrics" in results
    assert "metadata" in results
    assert "operational_benchmark" in results
    
    metrics = results["metrics"]
    assert "regression_mae" in metrics
    assert "classification_accuracy" in metrics
    
    # Values should be valid (not nan)
    for m in metrics.values():
        assert "value" in m
        assert "ci_lower" in m
        assert "ci_upper" in m
        assert m["ci_lower"] <= m["ci_upper"]

def test_benchmark_dataset_separation(tmp_path):
    ml = OperationalMLEngine(tmp_path, seed=42, rows=100)
    engine = BenchmarkEngine(ml, tmp_path, seed=999)
    df_train = ml._generate_training_data()
    df_bench = engine._generate_benchmark_data()
    # Basic check they are not the same (seeds differ)
    assert not df_train.equals(df_bench)
