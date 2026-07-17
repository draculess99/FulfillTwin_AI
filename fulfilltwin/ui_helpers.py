from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from .api_client import ApiClient


@st.cache_resource
def get_client() -> ApiClient:
    return ApiClient()


def severity_icon(severity: str) -> str:
    return {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(severity.lower(), "⚪")


def render_prediction_metrics(result: dict[str, Any]) -> None:
    p = result["predictions"]
    cols = st.columns(4)
    cols[0].metric("Predicted backlog", f"{p['predicted_backlog']:,}")
    cols[1].metric("SLA breach risk", f"{p['sla_breach_probability']:.1%}")
    cols[2].metric("Anomaly score", f"{p['anomaly_score']:.2f}")
    cols[3].metric("Operating regime", p["operating_regime"].replace("-", " ").title())


def render_agents(reports: list[dict[str, Any]]) -> None:
    for report in reports:
        with st.expander(f"{severity_icon(report['severity'])} {report['agent']} — {report['finding']}"):
            st.caption(report["role"])
            st.markdown("**Recommended actions**")
            for action in report["actions"]:
                st.write(f"• {action}")
            st.markdown("**Evidence**")
            for evidence in report["evidence"]:
                st.write(f"• {evidence}")


def plans_dataframe(plans: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for p in plans:
        rows.append(
            {
                "Plan": p["name"],
                "Labor moved": p["labor_reallocation"],
                "OT hours": p["overtime_hours"],
                "Release throttle": f"{p['release_throttle_pct']}%",
                "Backlog reduction": p["estimated_backlog_reduction"],
                "Residual backlog": p["residual_backlog"],
                "Estimated cost": p["estimated_total_cost"],
                "Approval": "Required" if p["requires_human_approval"] else "Within guardrails",
            }
        )
    return pd.DataFrame(rows)
