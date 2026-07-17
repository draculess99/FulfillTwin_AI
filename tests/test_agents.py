from fulfilltwin.backend.services.agents import AGENTS, AgentContext


def test_all_agents_return_structured_reports():
    context = AgentContext(
        scenario={"absenteeism_pct": 20, "workers": 150, "conveyor_capacity_pct": 50, "dock_congestion_pct": 75, "inventory_availability_pct": 80, "energy_price_pct": 60},
        predictions={"predicted_backlog": 3500, "sla_breach_probability": 0.8, "anomaly_score": 0.7, "operating_regime": "equipment-constrained"},
        rules=[{"severity": "critical"}],
        rag=[{"citation": "test"}],
        plans=[{"labor_reallocation": 25, "overtime_hours": 2, "maintenance_priority": "critical", "release_throttle_pct": 20, "energy_shift_pct": 15, "estimated_total_cost": 10000, "residual_backlog": 2000, "estimated_backlog_reduction": 1500}],
    )
    reports = [agent.report(context) for agent in AGENTS]
    assert len(reports) >= 6
    assert all(report["agent"] and report["actions"] for report in reports)
