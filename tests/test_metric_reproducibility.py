import pytest
from fulfilltwin.backend.services.ml_engine import OperationalMLEngine
from fulfilltwin.backend.services.benchmark_engine import BenchmarkEngine

def test_benchmark_reproducibility(tmp_path):
    ml = OperationalMLEngine(tmp_path, seed=42, rows=50)
    
    engine1 = BenchmarkEngine(ml, tmp_path, seed=123)
    res1 = engine1.run_benchmark(n_resamples=1)
    
    engine2 = BenchmarkEngine(ml, tmp_path, seed=123)
    res2 = engine2.run_benchmark(n_resamples=1)
    
    # The output from the same seed should be perfectly identical
    assert res1["metrics"]["regression_mae"]["value"] == res2["metrics"]["regression_mae"]["value"]
    assert res1["operational_benchmark"]["mean_simulated_backlog_reduction"] == res2["operational_benchmark"]["mean_simulated_backlog_reduction"]
