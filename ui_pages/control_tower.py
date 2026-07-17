from __future__ import annotations

import pandas as pd
import streamlit as st

from fulfilltwin.ui_helpers import get_client, render_prediction_metrics

st.title("Fulfillment Operations Control Tower")
st.write("A live operational view of warehouse events, recent digital-twin decisions, and human approval status.")
client = get_client()

st.subheader("Simulated event stream")
    
import streamlit.components.v1 as components
components.html(
    """
    <div id="timer-container" style="color: #94a3b8; font-family: sans-serif; font-size: 14px; padding-bottom: 8px;">
        🟢 Simulated event stream is live and monitoring warehouse conditions...
    </div>
    <script>
        function updateTimer() {
            var now = new Date();
            var secondsLeft = 60 - now.getSeconds();
            var container = document.getElementById('timer-container');
            if (secondsLeft <= 5 && secondsLeft > 0) {
                container.innerHTML = '⏳ Next batch of simulated events generating in: <strong style="color: #38bdf8;">' + secondsLeft + '</strong> seconds';
            } else {
                container.innerHTML = '🟢 Simulated event stream is live and monitoring warehouse conditions...';
            }
        }
        setInterval(updateTimer, 1000);
        updateTimer();
    </script>
    """,
    height=40
)

@st.fragment(run_every="5s")
def render_live_events():
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
        
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("### 🚨 Active Incident Triggers")
        st.info("💡 **Interactive Demo Flow:**\n1. **Click** any of the active alerts below.\n2. You will be automatically teleported to the Scenario Lab.\n3. Click **Run digital twin** to have the AI solve the exact disaster you clicked!")
        
        high_sev_events = [e for e in events if e["severity"] in ("CRITICAL", "HIGH")][:3]
        if not high_sev_events:
            st.success("No active critical or high-severity incidents detected.")
        else:
            for evt in high_sev_events:
                btn_label = f"Simulate {evt['severity']} {evt['type']} in {evt['zone']} Zone"
                if st.button(btn_label, type="primary" if evt["severity"] == "CRITICAL" else "secondary", key=evt["event_id"]):
                    st.session_state["mapped_event"] = evt
                    st.switch_page("ui_pages/scenario_lab.py")

    except Exception as exc:
        st.error(f"Could not load event stream: {exc}")

render_live_events()

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
