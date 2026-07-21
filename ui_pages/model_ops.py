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
    
    st.subheader("Model Performance")
    
    st.info("These results were generated using held-out synthetic fulfillment-center scenarios. They demonstrate prototype behavior and are not production or real-world warehouse performance.")
    
    cols = st.columns(4)
    cols[0].metric("XGBoost regression R²", f"{metrics.get('regression_r2', 0):.3f}")
    cols[1].metric("Regression MAE", f"{metrics.get('regression_mae', 0):,.2f}")
    cols[2].metric("Classifier ROC-AUC", f"{metrics.get('classification_roc_auc', 0):.3f}")
    cols[3].metric("Classifier accuracy", f"{metrics.get('classification_accuracy', 0):.3f}")

    st.subheader("Baseline Comparison")
    baselines = metrics.get("baselines", {})
    if baselines:
        bcols = st.columns(2)
        with bcols[0]:
            st.markdown("**Regression (MAE)**")
            st.write(f"• **XGBoost**: {metrics['regression_mae']:.2f}")
            st.write(f"• **Dummy (Mean)**: {baselines['dummy_regression_mae']:.2f}")
            st.write(f"• **Linear Regression**: {baselines['linear_regression_mae']:.2f}")
            st.success(f"Improvement vs Dummy: {baselines['xgboost_mae_improvement_vs_dummy']:.2f}")
        with bcols[1]:
            st.markdown("**Classification (Accuracy)**")
            st.write(f"• **XGBoost**: {metrics['classification_accuracy']:.4f}")
            st.write(f"• **Dummy (Majority)**: {baselines['dummy_classification_accuracy']:.4f}")
            st.write(f"• **Logistic Regression**: {baselines['logistic_regression_accuracy']:.4f}")
            st.success(f"Improvement vs Dummy: {baselines['xgboost_acc_improvement_vs_dummy']:.4f}")
            
    st.subheader("Confusion Matrix")
    cm = metrics.get("confusion_matrix")
    if cm:
        st.dataframe(pd.DataFrame(cm, columns=["Predicted: No Breach", "Predicted: Breach"], index=["Actual: No Breach", "Actual: Breach"]))

    st.subheader("Evaluation Dataset Disclosure")
    st.write(f"**Data Source:** {metrics.get('data_source', 'synthetic fulfillment-center scenarios')}")
    st.write(f"**Evaluation Type:** {metrics.get('evaluation_type', 'held-out synthetic validation')}")
    st.write(f"**Training Rows:** {metrics.get('training_rows', 0):,}")
    st.write(f"**Test Rows:** {metrics.get('test_rows', 0):,}")
    st.write(f"**Positive Class Rate:** {metrics.get('positive_class_rate', 0)}")
    st.write(f"**Evaluation Timestamp:** {metrics.get('evaluation_timestamp', 'N/A')}")

    st.markdown("---")
    
    st.subheader("Independent Operational Benchmark")
    try:
        benchmark = client.benchmark_results()
        ob = benchmark.get("operational_benchmark")
        if ob:
            st.write(f"*{ob['label']}*")
            b_cols = st.columns(3)
            b_cols[0].metric("Mean Simulated Backlog Reduction", f"{ob['mean_simulated_backlog_reduction']:,.0f}")
            b_cols[1].metric("Median Simulated Backlog Reduction", f"{ob['median_simulated_backlog_reduction']:,.0f}")
            b_cols[2].metric("Mean Simulated Incident Cost Difference", f"${ob['mean_simulated_incident_cost_difference']:,.2f}")
            
            b_cols2 = st.columns(3)
            b_cols2[0].metric("SLA-Breach Difference", f"{ob['sla_breach_difference']:.4f}")
            b_cols2[1].metric("FulfillTwin vs Baseline Win-Rate", f"{ob['percentage_ft_beats_fixed_baseline']:.1%}")
            b_cols2[2].metric("Human Approval Rate", f"{ob['human_approval_rate']:.1%}")
            
            st.write("**Out-of-Sample Benchmark Model Performance**")
            bm_metrics = benchmark.get("metrics", {})
            if bm_metrics:
                m_cols = st.columns(4)
                m_cols[0].metric("Benchmark R²", f"{bm_metrics.get('regression_r2', {}).get('value', 0):.3f}")
                m_cols[1].metric("Benchmark MAE", f"{bm_metrics.get('regression_mae', {}).get('value', 0):,.2f}")
                m_cols[2].metric("Benchmark ROC-AUC", f"{bm_metrics.get('classification_roc_auc', {}).get('value', 0):.3f}")
                m_cols[3].metric("Benchmark Accuracy", f"{bm_metrics.get('classification_accuracy', {}).get('value', 0):.3f}")
                st.write("")

            st.write("**Plan-Selection Distribution**")
            st.json(ob.get("plan_selection_distribution", {}))
            
        st.subheader("Benchmark Metadata")
        meta = benchmark.get("metadata", {})
        if meta:
            st.write(f"**Seed:** {meta.get('evaluation_seed')}")
            st.write(f"**Sample Size:** {meta.get('sample_size')}")
            st.write(f"**Description:** {meta.get('data_description')}")
            st.write(f"**Timestamp:** {meta.get('evaluation_timestamp')}")
            
        st.subheader("Download Results as JSON or CSV")
        import os
        json_path = "fulfilltwin/backend/artifacts/benchmark_results.json"
        csv_path = "fulfilltwin/backend/artifacts/benchmark_results.csv"
        
        d_cols = st.columns(2)
        if os.path.exists(json_path):
            with open(json_path, "rb") as f:
                d_cols[0].download_button("Download Results as JSON", f, file_name="benchmark_results.json", mime="application/json")
        if os.path.exists(csv_path):
            with open(csv_path, "rb") as f:
                d_cols[1].download_button("Download Results as CSV", f, file_name="benchmark_results.csv", mime="text/csv")
                
    except Exception as e:
        st.info("No benchmark results found. Run the benchmark to generate them.")
        
    st.write("")
    if st.button("🔄 Run Operational Benchmark"):
        with st.spinner("Running benchmark (1000 scenarios)..."):
            client.run_benchmark()
        st.rerun()

    st.markdown("---")

    st.subheader("Model stack")
    st.dataframe(pd.DataFrame([{"Task": k, "Model": v} for k, v in metrics.get("models", {}).items()]), use_container_width=True, hide_index=True)

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
    st.warning(f"⚠️ Cannot connect to the FulfillTwin backend API. Exception: {exc}")
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
