from __future__ import annotations

import pandas as pd
import streamlit as st

from fulfilltwin.ui_helpers import get_client

st.title("Model Ops & Governance")
st.write("Review the traditional ML models, validation metrics, intended use, limitations, and JSON decision memory.")
client = get_client()

try:
    card = client.model_card()
    metrics = card["metrics"]
    cols = st.columns(4)
    cols[0].metric("XGBoost regression R²", f"{metrics['regression_r2']:.3f}")
    cols[1].metric("Regression MAE", f"{metrics['regression_mae']:,.0f}")
    cols[2].metric("Classifier ROC-AUC", f"{metrics['classification_roc_auc']:.3f}")
    cols[3].metric("Classifier accuracy", f"{metrics['classification_accuracy']:.3f}")

    st.subheader("Model stack")
    st.dataframe(pd.DataFrame([{"Task": k, "Model": v} for k, v in metrics["models"].items()]), use_container_width=True, hide_index=True)

    st.subheader("Model card")
    st.write(card["purpose"])
    st.markdown("**Approved uses**")
    for item in card["approved_uses"]:
        st.write(f"• {item}")
    st.markdown("**Prohibited uses**")
    for item in card["prohibited_uses"]:
        st.write(f"• {item}")
    st.markdown("**Limitations**")
    for item in card["limitations"]:
        st.write(f"• {item}")

    if st.button("Retrain synthetic baseline models"):
        with st.spinner("Retraining XGBoost, Isolation Forest, and K-means..."):
            response = client.retrain()
        st.success(f"Retrained on {response['metrics']['training_rows']:,} synthetic rows")
        st.rerun()
except Exception as exc:
    st.warning("⚠️ Cannot connect to the FulfillTwin backend API. Please ensure the backend server is running.")
    if st.button("🔄 Retry Connection", key="retry_models"):
        st.rerun()

st.subheader("JSON decision memory")
try:
    runs = client.memory(50)["runs"]
    st.write(f"Stored decisions: **{len(runs)}**")
    if runs:
        st.json(runs[0], expanded=False)
    if st.button("Clear decision memory"):
        client.clear_memory()
        st.success("Memory cleared")
        st.rerun()
except Exception as exc:
    st.warning("⚠️ Cannot connect to the FulfillTwin backend API. Please ensure the backend server is running.")
    if st.button("🔄 Retry Connection", key="retry_memory"):
        st.rerun()
