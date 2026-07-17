from __future__ import annotations

import streamlit as st

from fulfilltwin.ui_helpers import get_client, plans_dataframe, render_agents, render_prediction_metrics

st.title("Scenario Lab")
st.write("Stress the digital twin, forecast the operational impact, and compare human-reviewable recovery plans.")
client = get_client()

# Inject custom CSS to make the Scenario Preset dropdown more prominent
st.markdown("""
<style>
/* Target the selectbox to make it taller and a different color */
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background-color: rgba(56, 189, 248, 0.15) !important;
    border: 2px solid #38bdf8 !important;
    border-radius: 8px;
    min-height: 55px !important;
    display: flex;
    align-items: center;
}
div[data-testid="stSelectbox"] label {
    font-weight: bold;
    color: #38bdf8 !important;
    font-size: 1.1rem;
}
</style>
""", unsafe_allow_html=True)

presets = {
    "Demand spike + conveyor failure": {"order_volume_pct": 35, "absenteeism_pct": 9, "conveyor_capacity_pct": 48, "dock_congestion_pct": 55, "energy_price_pct": 20, "inventory_availability_pct": 91, "current_backlog": 1100, "workers": 145, "base_throughput": 1350, "horizon_hours": 6},
    "Labor shortage": {"order_volume_pct": 18, "absenteeism_pct": 24, "conveyor_capacity_pct": 92, "dock_congestion_pct": 38, "energy_price_pct": 8, "inventory_availability_pct": 95, "current_backlog": 650, "workers": 132, "base_throughput": 1280, "horizon_hours": 8},
    "Dock congestion + inventory delay": {"order_volume_pct": 12, "absenteeism_pct": 7, "conveyor_capacity_pct": 86, "dock_congestion_pct": 82, "energy_price_pct": 15, "inventory_availability_pct": 66, "current_backlog": 900, "workers": 155, "base_throughput": 1420, "horizon_hours": 7},
    "Energy-price shock": {"order_volume_pct": 9, "absenteeism_pct": 6, "conveyor_capacity_pct": 94, "dock_congestion_pct": 30, "energy_price_pct": 95, "inventory_availability_pct": 96, "current_backlog": 350, "workers": 150, "base_throughput": 1320, "horizon_hours": 6},
}

preset_name = st.selectbox("Scenario preset", list(presets))
preset = presets[preset_name]
with st.form("scenario_form"):
    left, middle, right = st.columns(3)
    order_volume_pct = left.slider("Order volume change (%)", -30, 100, int(preset["order_volume_pct"]))
    absenteeism_pct = left.slider("Absenteeism (%)", 0, 45, int(preset["absenteeism_pct"]))
    conveyor_capacity_pct = left.slider("Conveyor capacity (%)", 20, 110, int(preset["conveyor_capacity_pct"]))
    dock_congestion_pct = middle.slider("Dock congestion (%)", 0, 100, int(preset["dock_congestion_pct"]))
    energy_price_pct = middle.slider("Energy price change (%)", -30, 160, int(preset["energy_price_pct"]))
    inventory_availability_pct = middle.slider("Inventory availability (%)", 40, 100, int(preset["inventory_availability_pct"]))
    current_backlog = right.number_input("Current backlog", 0, 15000, int(preset["current_backlog"]), 100)
    workers = right.number_input("Workers scheduled", 20, 500, int(preset["workers"]), 5)
    base_throughput = right.number_input("Baseline units/hour", 200, 5000, int(preset["base_throughput"]), 50)
    horizon_hours = right.slider("Forecast horizon (hours)", 1, 24, int(preset["horizon_hours"]))
    submitted = st.form_submit_button("Run digital twin", type="primary")

if submitted:
    scenario = {
        "order_volume_pct": order_volume_pct,
        "absenteeism_pct": absenteeism_pct,
        "conveyor_capacity_pct": conveyor_capacity_pct,
        "dock_congestion_pct": dock_congestion_pct,
        "energy_price_pct": energy_price_pct,
        "inventory_availability_pct": inventory_availability_pct,
        "current_backlog": current_backlog,
        "workers": workers,
        "base_throughput": base_throughput,
        "horizon_hours": horizon_hours,
    }
    with st.spinner("Running models, expert rules, RAG retrieval, optimizer, and agent council..."):
        try:
            result = client.run_scenario(scenario, st.session_state.get("provider", "LOCAL"), st.session_state.get("model", "expert-system-v1"))
            st.session_state["last_result"] = result
            
            # Accumulate tokens used
            tokens = result.get("executive_brief", {}).get("tokens", 0)
            st.session_state["total_tokens"] = st.session_state.get("total_tokens", 0) + tokens
        except Exception as exc:
            st.error(str(exc))

result = st.session_state.get("last_result")
if result:
    render_prediction_metrics(result)
    st.subheader("Executive incident brief")
    brief = result["executive_brief"]
    if brief.get("warning"):
        st.warning(brief["warning"])
    st.write(brief["text"])
    approval = result["approval"]
    if approval["required"]:
        st.error(f"Human approval required — {approval['reason']}")
    else:
        st.success("Plan remains within configured guardrails.")
    st.subheader("Recovery plan comparison")
    st.dataframe(plans_dataframe(result["candidate_plans"]), use_container_width=True, hide_index=True)
    st.subheader("Agent reports")
    render_agents(result["agent_reports"])
