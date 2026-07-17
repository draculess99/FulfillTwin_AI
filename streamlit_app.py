from __future__ import annotations

import streamlit as st

from fulfilltwin.ui_helpers import get_client

st.set_page_config(page_title="FulfillTwin AI", page_icon="🏭", layout="wide")

st.sidebar.title("FulfillTwin AI")
st.sidebar.caption("Human–robot workforce digital twin and incident command")

client = get_client()
try:
    health = client.health()
    st.sidebar.success(f"API online · {health['knowledge_chunks']} RAG chunks")
except Exception as exc:
    st.sidebar.error(f"API unavailable: {exc}")

try:
    model_config = client.models()
except Exception:
    model_config = {"LOCAL": ["expert-system-v1"], "GROQ": [], "GEMINI": [], "keys_configured": {}}

if "total_tokens" not in st.session_state:
    st.session_state["total_tokens"] = 0

st.sidebar.markdown("---")
token_cols = st.sidebar.columns([2, 1])
token_placeholder = token_cols[0].empty()
if token_cols[1].button("Reset", key="reset_tokens_btn"):
    st.session_state["total_tokens"] = 0
    st.rerun()

provider = st.sidebar.selectbox("Decision narrative", ["LOCAL", "GROQ", "GEMINI"], index=0)
models = model_config.get(provider, ["expert-system-v1"]) or ["expert-system-v1"]
model = st.sidebar.selectbox("Model", models)
st.session_state["provider"] = provider
st.session_state["model"] = model
if provider != "LOCAL" and not model_config.get("keys_configured", {}).get(provider, False):
    st.sidebar.warning(f"{provider} API key is not configured; local expert-system fallback will be used.")

pages = {
    "Operations": [
        st.Page("ui_pages/control_tower.py", title="Control Tower", icon="🏭", default=True),
        st.Page("ui_pages/scenario_lab.py", title="Scenario Lab", icon="🧪"),
        st.Page("ui_pages/agent_council.py", title="Agent Council", icon="🤖"),
    ],
    "Trust & Models": [
        st.Page("ui_pages/knowledge_center.py", title="Knowledge Center", icon="📚"),
        st.Page("ui_pages/model_ops.py", title="Model Ops", icon="📈"),
    ],
}

navigation = st.navigation(pages)
navigation.run()

# Fill the placeholder after the page has run so it reflects any tokens added during the run
token_placeholder.metric("Tokens Used", f"{st.session_state['total_tokens']:,}")
