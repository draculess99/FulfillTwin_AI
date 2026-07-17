from __future__ import annotations

import streamlit as st

from fulfilltwin.ui_helpers import get_client, plans_dataframe, render_agents, render_prediction_metrics

st.title("Multi-Agent Incident Council")
st.write("Inspect each specialist agent, the arbiter's chosen plan, and the evidence used to reach the recommendation.")
client = get_client()

result = st.session_state.get("last_result")
if not result:
    try:
        rows = client.memory(1)["runs"]
        result = rows[0] if rows else None
    except Exception as exc:
        st.error(str(exc))

if not result:
    st.info("Run a scenario first. The council will then preserve its complete decision in JSON memory.")
    st.stop()

render_prediction_metrics(result)
render_agents(result["agent_reports"])

st.subheader("Arbiter recommendation")
plan = result["recommended_plan"]
left, right = st.columns([2, 1])
left.success(f"Recommended: {plan['name']}")
left.dataframe(plans_dataframe(result["candidate_plans"]), use_container_width=True, hide_index=True)
right.metric("Estimated incident cost", f"${plan['estimated_total_cost']:,.0f}")
right.metric("Backlog reduction", f"{plan['estimated_backlog_reduction']:,}")
right.metric("Residual backlog", f"{plan['residual_backlog']:,}")
right.write(f"Approval status: **{result['approval']['status']}**")

st.subheader("Expert-system rules")
for rule in result["expert_rules"]:
    st.write(f"**{rule['severity'].upper()} · {rule['rule_id']}** — {rule['message']}")
    st.caption(rule["recommended_action"])

st.subheader("Retrieved internal evidence")
for evidence in result["rag_evidence"]:
    with st.expander(f"{evidence['citation']} · relevance {evidence['score']:.2f}"):
        st.write(evidence["text"])
