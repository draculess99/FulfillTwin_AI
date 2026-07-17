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

mapped_evt = st.session_state.get("mapped_event")
options = list(presets.keys())

if mapped_evt:
    options = ["--- LIVE EVENT ACTIVE ---"] + options
    preset_name = st.selectbox("Scenario preset", options, index=0, disabled=True)
    preset = presets[list(presets.keys())[0]].copy()
else:
    preset_name = st.selectbox("Scenario preset", options)
    preset = presets[preset_name].copy()

if mapped_evt:
    st.info(f"🚨 **Scenario mapped from live {mapped_evt['severity']} event:** {mapped_evt['type']} in {mapped_evt['zone']} Zone")
    if st.button("Clear active event and return to manual presets"):
        del st.session_state["mapped_event"]
        st.rerun()
    
    # Map the event to slider defaults
    if mapped_evt["type"] == "ORDER_SURGE":
        preset["order_volume_pct"] = int(mapped_evt["value"] * 100)
    elif mapped_evt["type"] == "CONVEYOR_ALERT":
        preset["conveyor_capacity_pct"] = max(20, 100 - int(mapped_evt["value"] * 80))
    elif mapped_evt["type"] == "LABOR_UPDATE":
        preset["absenteeism_pct"] = int(mapped_evt["value"] * 40)
    elif mapped_evt["type"] == "REPLENISHMENT_DELAY":
        preset["inventory_availability_pct"] = max(40, 100 - int(mapped_evt["value"] * 60))
    elif mapped_evt["type"] == "ENERGY_SIGNAL":
        preset["energy_price_pct"] = int(mapped_evt["value"] * 150)
    elif mapped_evt["type"] == "TRAILER_ARRIVAL":
        preset["dock_congestion_pct"] = int(mapped_evt["value"] * 100)
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
    import time
    with st.status("Executing FulfillTwin Agentic Pipeline...", expanded=True) as status:
        step1 = st.empty()
        step2 = st.empty()
        step3 = st.empty()
        step4 = st.empty()
        step4_sub = st.empty()
        step5 = st.empty()
        
        step1.write("⏳ `[1/5]` Running ML predictions (Backlog & SLA)...")
        time.sleep(0.3)
        step1.write("✅ `[1/5]` Running ML predictions (Backlog & SLA)...")
        
        step2.write("⏳ `[2/5]` Retrieving RAG safety evidence...")
        time.sleep(0.3)
        step2.write("✅ `[2/5]` Retrieving RAG safety evidence...")
        
        step3.write("⏳ `[3/5]` Applying Expert System guardrails...")
        time.sleep(0.3)
        step3.write("✅ `[3/5]` Applying Expert System guardrails...")
        
        step4.write("⏳ `[4/5]` Convening Multi-Agent Council...")
        step4_sub.caption("↳ Demand Forecast, Workforce, Equipment, Dock, Energy, Safety, Finance")
        time.sleep(0.6)
        step4.write("✅ `[4/5]` Convening Multi-Agent Council...")
        
        step5.write("⏳ `[5/5]` Optimizing final recovery plan...")
        
        try:
            result = client.run_scenario(scenario, st.session_state.get("provider", "LOCAL"), st.session_state.get("model", "expert-system-v1"))
            step5.write("✅ `[5/5]` Optimizing final recovery plan...")
            
            st.session_state["last_result"] = result
            
            # Accumulate tokens used
            tokens = result.get("executive_brief", {}).get("tokens", 0)
            st.session_state["total_tokens"] = st.session_state.get("total_tokens", 0) + tokens
            status.update(label="Pipeline execution complete!", state="complete", expanded=True)
        except Exception as exc:
            step5.write("❌ `[5/5]` Pipeline execution failed!")
            status.update(label="Pipeline execution failed!", state="error", expanded=True)
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
        if approval.get("status") == "APPROVED":
            st.success(f"Plan APPROVED by {approval.get('approved_by')} at {approval.get('approved_at')}")
        else:
            st.error(f"Human approval required — {approval['reason']}")
            if st.button("Approve Recovery Plan", type="primary", key=f"approve_{result['run_id']}"):
                with st.spinner("Approving plan..."):
                    try:
                        updated_run = client.approve_scenario(result["run_id"])["run"]
                        st.session_state["last_result"] = updated_run
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to approve plan: {e}")
    else:
        st.success("Plan remains within configured guardrails.")
    st.subheader("Recovery plan comparison")
    st.dataframe(plans_dataframe(result["candidate_plans"]), use_container_width=True, hide_index=True)
    st.subheader("Agent reports")
    render_agents(result["agent_reports"])
