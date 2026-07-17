from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentContext:
    scenario: dict[str, float]
    predictions: dict[str, Any]
    rules: list[dict[str, Any]]
    rag: list[dict[str, Any]]
    plans: list[dict[str, Any]]


class BaseAgent:
    name = "Base Agent"
    role = "General operations"

    def report(self, context: AgentContext) -> dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def _result(name: str, role: str, severity: str, finding: str, actions: list[str], evidence: list[str]) -> dict[str, Any]:
        return {
            "agent": name,
            "role": role,
            "severity": severity,
            "finding": finding,
            "actions": actions,
            "evidence": evidence,
        }


class DemandForecastAgent(BaseAgent):
    name = "Demand Forecast Agent"
    role = "Backlog and SLA forecasting"

    def report(self, c: AgentContext) -> dict[str, Any]:
        p = c.predictions
        prob = float(p["sla_breach_probability"])
        severity = "critical" if prob >= 0.7 else "high" if prob >= 0.45 else "medium" if prob >= 0.25 else "low"
        return self._result(
            self.name, self.role, severity,
            f"The model predicts a backlog of {p['predicted_backlog']:,} units and a {prob:.0%} SLA-breach probability.",
            ["Stage recovery capacity before the modeled peak.", "Reforecast after every material intervention."],
            [f"Operating regime: {p['operating_regime']}", f"Anomaly score: {p['anomaly_score']:.2f}"],
        )


class WorkforceAgent(BaseAgent):
    name = "Workforce Agent"
    role = "Labor allocation and fatigue controls"

    def report(self, c: AgentContext) -> dict[str, Any]:
        absent = c.scenario["absenteeism_pct"]
        plan = c.plans[0]
        severity = "critical" if absent >= 20 else "high" if absent >= 12 else "medium" if absent >= 7 else "low"
        return self._result(
            self.name, self.role, severity,
            f"Absenteeism is {absent:.1f}%; the lowest-cost viable plan reallocates {plan['labor_reallocation']} associates.",
            ["Use certified cross-trained associates first.", "Require manager approval before overtime or large reassignments."],
            [f"Workers scheduled: {c.scenario['workers']:.0f}", f"Proposed overtime: {plan['overtime_hours']} hours"],
        )


class EquipmentRecoveryAgent(BaseAgent):
    name = "Equipment Recovery Agent"
    role = "Conveyor and material-handling recovery"

    def report(self, c: AgentContext) -> dict[str, Any]:
        capacity = c.scenario["conveyor_capacity_pct"]
        severity = "critical" if capacity <= 50 else "high" if capacity <= 75 else "medium" if capacity <= 90 else "low"
        return self._result(
            self.name, self.role, severity,
            f"Material-handling capacity is {capacity:.0f}% of baseline.",
            ["Sequence maintenance by SLA exposure.", "Use release throttling to prevent downstream gridlock."],
            [f"Recommended maintenance priority: {c.plans[0]['maintenance_priority']}", f"Release throttle: {c.plans[0]['release_throttle_pct']}%"],
        )


class DockFlowAgent(BaseAgent):
    name = "Dock Flow Agent"
    role = "Trailer, yard, and dock prioritization"

    def report(self, c: AgentContext) -> dict[str, Any]:
        congestion = c.scenario["dock_congestion_pct"]
        severity = "critical" if congestion >= 85 else "high" if congestion >= 65 else "medium" if congestion >= 40 else "low"
        return self._result(
            self.name, self.role, severity,
            f"Dock congestion is {congestion:.0f}% and may restrict both replenishment and departures.",
            ["Prioritize departure-critical trailers.", "Protect replenishment for high-velocity inventory."],
            [f"Inventory availability: {c.scenario['inventory_availability_pct']:.0f}%"],
        )


class EnergyAgent(BaseAgent):
    name = "Energy Agent"
    role = "Energy-aware operating plan"

    def report(self, c: AgentContext) -> dict[str, Any]:
        price = c.scenario["energy_price_pct"]
        severity = "high" if price >= 80 else "medium" if price >= 35 else "low"
        return self._result(
            self.name, self.role, severity,
            f"Energy price is {price:+.0f}% versus baseline.",
            ["Shift discretionary charging outside the peak window.", "Do not curtail safety or recovery-critical equipment."],
            [f"Recommended shiftable load: {c.plans[0]['energy_shift_pct']}%"],
        )


class SafetyGovernanceAgent(BaseAgent):
    name = "Safety & Governance Agent"
    role = "Guardrails, auditability, and human approval"

    def report(self, c: AgentContext) -> dict[str, Any]:
        critical_rules = sum(1 for rule in c.rules if rule["severity"] == "critical")
        severity = "critical" if critical_rules else "high" if any(r["severity"] == "high" for r in c.rules) else "low"
        return self._result(
            self.name, self.role, severity,
            f"The expert system produced {len(c.rules)} control findings, including {critical_rules} critical rules.",
            ["Keep all consequential actions human-approved.", "Do not use outputs for individual worker discipline."],
            [f"RAG evidence retrieved: {len(c.rag)} chunks", "Decision will be written to JSON memory"],
        )


class FinanceAgent(BaseAgent):
    name = "Finance Agent"
    role = "Recovery cost and service-loss trade-off"

    def report(self, c: AgentContext) -> dict[str, Any]:
        plan = c.plans[0]
        return self._result(
            self.name, self.role, "medium" if plan["estimated_total_cost"] > 10000 else "low",
            f"The best scored plan has an estimated total incident cost of ${plan['estimated_total_cost']:,.0f}.",
            ["Compare at least three recovery strategies.", "Track realized cost and backlog reduction after approval."],
            [f"Residual backlog: {plan['residual_backlog']:,}", f"Estimated reduction: {plan['estimated_backlog_reduction']:,}"],
        )


AGENTS = [
    DemandForecastAgent(),
    WorkforceAgent(),
    EquipmentRecoveryAgent(),
    DockFlowAgent(),
    EnergyAgent(),
    SafetyGovernanceAgent(),
    FinanceAgent(),
]
