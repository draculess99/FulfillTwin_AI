import json
import re
from pathlib import Path

def update_portfolio():
    index_path = Path(r"d:\Work\Main-Landing-Page\index.html")
    benchmark_path = Path(r"d:\Work\Springboard\ANTIGRAVITY-SCRATCH\FulfillTwin\FulfillTwin_AI\fulfilltwin\backend\artifacts\benchmark_results.json")
    metrics_path = Path(r"d:\Work\Springboard\ANTIGRAVITY-SCRATCH\FulfillTwin\FulfillTwin_AI\fulfilltwin\backend\artifacts\metrics.json")
    
    data = None
    source = ""
    if benchmark_path.exists():
        data = json.loads(benchmark_path.read_text(encoding="utf-8"))
        source = "benchmark_results.json"
    elif metrics_path.exists():
        data = json.loads(metrics_path.read_text(encoding="utf-8"))
        source = "metrics.json"
    else:
        print("No metrics artifacts found.")
        return

    m = data.get("metrics", data)
    meta = data.get("metadata", data)

    # get raw values
    acc = m.get("classification_accuracy", 0)
    roc = m.get("classification_roc_auc", 0)
    r2 = m.get("regression_r2", 0)
    
    # handle nested dicts
    if isinstance(acc, dict): acc = acc.get("value", 0)
    if isinstance(roc, dict): roc = roc.get("value", 0)
    if isinstance(r2, dict): r2 = r2.get("value", 0)
    
    if not acc:
        print("classification_accuracy missing, cannot update.")
        return

    test_rows = meta.get("test_rows", meta.get("sample_size", None))
    
    acc_pct = f"{acc * 100:.1f}%"
    roc_fmt = f"{roc:.3f}"
    r2_fmt = f"{r2:.3f}"
    
    disclosure = "Synthetic holdout validation"
    if test_rows is not None:
        disclosure += f" &middot; {test_rows} scenarios"
        
    block = f"""<!-- FULFILLTWIN_METRICS_START -->
        <div class="project-proof" aria-label="Generated model result">
          <div class="proof-main">{acc_pct} SLA-breach prediction accuracy</div>
          <div class="proof-sub">ROC-AUC {roc_fmt} &middot; Backlog R&sup2; {r2_fmt}</div>
          <div class="proof-note">{disclosure}</div>
        </div>
        <p class="project-impact">
          7 specialist agents &middot; 4 disruption scenarios &middot; 3 recovery strategies
        </p>
        <!-- FULFILLTWIN_METRICS_END -->"""
        
    content = index_path.read_text(encoding="utf-8")
    
    # if markers don't exist, replace the card-desc
    if "<!-- FULFILLTWIN_METRICS_START -->" not in content:
        pattern = r'<p class="card-desc">\s*A production-oriented digital twin that simulates disruptions, mathematically forecasts impact, and convenes a\s*multi-agent AI council to orchestrate optimal recovery\.\s*</p>'
        replacement = f"""<p class="card-desc">
          Simulates fulfillment-center disruptions and combines predictive machine learning, seven specialist agents, operating rules, RAG, and human approval to recommend recovery strategies.
        </p>
{block}"""
        content = re.sub(pattern, replacement, content)
    else:
        # replace existing block
        content = re.sub(
            r"<!-- FULFILLTWIN_METRICS_START -->.*?<!-- FULFILLTWIN_METRICS_END -->",
            block,
            content,
            flags=re.DOTALL
        )
        
    index_path.write_text(content, encoding="utf-8")
    print(f"Updated index.html using {source}")

if __name__ == "__main__":
    update_portfolio()
