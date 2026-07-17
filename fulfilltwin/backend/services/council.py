from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from .agents import AGENTS, AgentContext
from .expert_system import ExpertSystem
from .llm import LLMProvider
from .memory import JsonMemoryStore
from .ml_engine import OperationalMLEngine
from .optimizer import RecoveryOptimizer
from .rag import LocalRagEngine


class AgentCouncil:
    def __init__(
        self,
        ml: OperationalMLEngine,
        expert: ExpertSystem,
        rag: LocalRagEngine,
        optimizer: RecoveryOptimizer,
        llm: LLMProvider,
        memory: JsonMemoryStore,
    ) -> None:
        self.ml = ml
        self.expert = expert
        self.rag = rag
        self.optimizer = optimizer
        self.llm = llm
        self.memory = memory

    def run(self, scenario: dict[str, Any], provider: str = "LOCAL", model: str = "expert-system-v1") -> dict[str, Any]:
        normalized = {key: float(value) for key, value in scenario.items()}
        predictions = self.ml.predict(normalized)
        rules = self.expert.evaluate(normalized, predictions)
        query = self._rag_query(normalized, predictions, rules)
        rag_results = self.rag.search(query, top_k=5)
        plans = self.optimizer.generate_plans(normalized, predictions)
        context = AgentContext(normalized, predictions, rules, rag_results, plans)
        agent_reports = [agent.report(context) for agent in AGENTS]
        best_plan = plans[0]
        approval_required = bool(best_plan["requires_human_approval"] or predictions["sla_breach_probability"] >= 0.45)
        local_brief = self._local_brief(predictions, rules, best_plan, approval_required)
        prompt = self._llm_prompt(normalized, predictions, rules, rag_results, agent_reports, plans)
        narrative = self.llm.generate(provider, model, prompt, local_brief)
        result = {
            "run_id": str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "scenario": normalized,
            "predictions": predictions,
            "expert_rules": rules,
            "rag_evidence": rag_results,
            "agent_reports": agent_reports,
            "candidate_plans": plans,
            "recommended_plan": best_plan,
            "approval": {
                "required": approval_required,
                "status": "PENDING" if approval_required else "PRE-APPROVED_WITHIN_GUARDRAILS",
                "reason": "Consequential labor/overtime action or elevated SLA risk" if approval_required else "Plan remains inside configured guardrails",
            },
            "executive_brief": narrative,
        }
        self.memory.append(result)
        return result

    @staticmethod
    def _rag_query(s: dict[str, float], p: dict[str, Any], rules: list[dict[str, Any]]) -> str:
        severe = " ".join(rule["message"] for rule in rules if rule["severity"] in {"critical", "high"})
        return (
            f"warehouse incident demand surge {s['order_volume_pct']} absenteeism {s['absenteeism_pct']} "
            f"conveyor capacity {s['conveyor_capacity_pct']} dock congestion {s['dock_congestion_pct']} "
            f"inventory {s['inventory_availability_pct']} SLA backlog recovery safety approval {severe}"
        )

    @staticmethod
    def _local_brief(p: dict[str, Any], rules: list[dict[str, Any]], plan: dict[str, Any], approval: bool) -> str:
        critical = sum(1 for rule in rules if rule["severity"] == "critical")
        return (
            f"Incident assessment: projected backlog {p['predicted_backlog']:,}; SLA-breach probability "
            f"{p['sla_breach_probability']:.0%}; operating regime {p['operating_regime']}. "
            f"The expert system identified {critical} critical controls. Recommend '{plan['name']}', "
            f"which is estimated to reduce backlog by {plan['estimated_backlog_reduction']:,} units at a total "
            f"incident cost of ${plan['estimated_total_cost']:,.0f}. "
            f"Human approval is {'required' if approval else 'not required under current guardrails'} before execution."
        )

    @staticmethod
    def _llm_prompt(
        scenario: dict[str, Any],
        predictions: dict[str, Any],
        rules: list[dict[str, Any]],
        rag: list[dict[str, Any]],
        agents: list[dict[str, Any]],
        plans: list[dict[str, Any]],
    ) -> str:
        payload = {
            "scenario": scenario,
            "predictions": predictions,
            "expert_rules": rules,
            "rag_evidence": [{"citation": r["citation"], "text": r["text"]} for r in rag],
            "agent_reports": agents,
            "candidate_plans": plans,
        }
        return (
            "Create a concise incident-command brief with these sections: Situation, Model Evidence, "
            "Agent Consensus, Recommended Plan, Guardrails, and Next Measurement. Use only supplied facts; "
            "cite internal evidence by its citation label; never claim automatic execution.\n\n"
            + json.dumps(payload, indent=2)
        )
