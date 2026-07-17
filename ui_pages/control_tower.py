from __future__ import annotations

import pandas as pd
import streamlit as st

from fulfilltwin.ui_helpers import get_client, render_prediction_metrics

st.title("Fulfillment Operations Control Tower")
st.write("A live operational view of warehouse events, recent digital-twin decisions, and human approval status.")
client = get_client()

try:
    events = client.events(15)["events"]
    df = pd.DataFrame(events)
    critical = int((df["severity"] == "CRITICAL").sum())
    high = int((df["severity"] == "HIGH").sum())
    cols = st.columns(4)
    cols[0].metric("Events in window", len(df))
    cols[1].metric("Critical alerts", critical)
    cols[2].metric("High alerts", high)
    cols[3].metric("Zones observed", df["zone"].nunique())
    st.subheader("Simulated event stream")
    st.dataframe(df, use_container_width=True, hide_index=True)
except Exception as exc:
    st.error(f"Could not load event stream: {exc}")

st.subheader("Recent digital-twin decisions")
try:
    runs = client.memory(10)["runs"]
    if not runs:
        st.info("No scenario has been run yet. Open Scenario Lab to create the first incident simulation.")
    else:
        latest = runs[0]
        render_prediction_metrics(latest)
        rows = []
        for run in runs:
            rows.append(
                {
                    "Time": run["created_at"],
                    "Run": run["run_id"][:8],
                    "Regime": run["predictions"]["operating_regime"],
                    "Backlog": run["predictions"]["predicted_backlog"],
                    "SLA risk": run["predictions"]["sla_breach_probability"],
                    "Plan": run["recommended_plan"]["name"],
                    "Approval": run["approval"]["status"],
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
except Exception as exc:
    st.error(f"Could not load JSON memory: {exc}")
