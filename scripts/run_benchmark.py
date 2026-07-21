import sys
from pathlib import Path

# Ensure the root project directory is on the path so fulfilltwin can be imported
sys.path.append(str(Path(__file__).resolve().parent.parent))

from fulfilltwin.config import ARTIFACT_DIR, settings
from fulfilltwin.backend.services.ml_engine import OperationalMLEngine
from fulfilltwin.backend.services.benchmark_engine import BenchmarkEngine

def main():
    print("Loading FulfillTwin MLEngine...")
    ml = OperationalMLEngine(ARTIFACT_DIR, settings.model_seed, settings.training_rows)
    
    print("Initializing Benchmark Engine...")
    engine = BenchmarkEngine(ml, ARTIFACT_DIR, seed=999)
    
    print("Running 1,000-scenario benchmark with 95% bootstrap confidence intervals...")
    results = engine.run_benchmark(n_resamples=1000)
    
    print("\nBenchmark completed successfully.")
    print(f"Sample size: {results['metadata']['sample_size']}")
    print(f"Positive Class Rate: {results['metadata']['positive_class_rate']}")
    print("\nMetrics:")
    for k, v in results['metrics'].items():
        print(f"  {k}: {v['value']} [95% CI: {v['ci_lower']} - {v['ci_upper']}]")
        
    print("\nResults saved to artifacts/benchmark_results.json and artifacts/benchmark_results.csv")

if __name__ == "__main__":
    main()
