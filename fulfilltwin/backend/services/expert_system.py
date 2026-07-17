from __future__ import annotations

from typing import Any


class ExpertSystem:
    """Deterministic warehouse operating rules that always run."""

    def evaluate(self, scenario: dict[str, float], predictions: dict[str, Any]) -> list[dict[str, Any]]:
        rules: list[dict[str, Any]] = []

        def add(rule_id: str, severity: str, message: str, action: str) -> None:
            rules.append(
                {
                    "rule_id": rule_id,
                    "severity": severity,
                    "message": message,
                    "recommended_action": action,
                }
            )

        if scenario["absenteeism_pct"] >= 18:
            add("LABOR-001", "critical", "Labor availability is below the safe operating band.", "Freeze nonessential indirect assignments and rebalance certified associates.")
        elif scenario["absenteeism_pct"] >= 10:
            add("LABOR-002", "high", "Absenteeism may create downstream starvation.", "Move cross-trained labor to the forecast bottleneck before backlog acceleration.")

        if scenario["conveyor_capacity_pct"] <= 55:
            add("EQUIP-001", "critical", "Material-handling capacity is severely degraded.", "Activate manual bypass lanes and sequence maintenance recovery by SLA exposure.")
        elif scenario["conveyor_capacity_pct"] <= 80:
            add("EQUIP-002", "high", "Conveyor constraint is likely to reduce realized throughput.", "Reduce release rate and route priority work through healthy zones.")

        if scenario["dock_congestion_pct"] >= 70:
            add("DOCK-001", "high", "Dock congestion threatens inbound and outbound flow.", "Prioritize departure-critical trailers and hold low-value yard moves.")

        if scenario["inventory_availability_pct"] <= 75:
            add("INV-001", "high", "Inventory availability may increase shorts and rework.", "Expedite replenishment for high-velocity SKUs and suppress low-confidence releases.")

        if scenario["energy_price_pct"] >= 50:
            add("ENERGY-001", "medium", "Energy cost is materially above baseline.", "Shift discretionary charging and noncritical loads outside the peak window.")

        if float(predictions["sla_breach_probability"]) >= 0.70:
            add("SLA-001", "critical", "The predicted SLA-breach probability exceeds 70%.", "Require incident-command approval and execute the lowest-cost viable recovery plan.")
        elif float(predictions["sla_breach_probability"]) >= 0.45:
            add("SLA-002", "high", "Service-level performance is at material risk.", "Open an incident, assign owners, and review the recovery plan within 15 minutes.")

        if not rules:
            add("OPS-000", "low", "The operation is within modeled control limits.", "Continue monitoring and preserve labor flexibility.")
        return rules
