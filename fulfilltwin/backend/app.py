from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS

from fulfilltwin.config import ARTIFACT_DIR, KNOWLEDGE_DIR, settings
from fulfilltwin.backend.services.council import AgentCouncil
from fulfilltwin.backend.services.expert_system import ExpertSystem
from fulfilltwin.backend.services.llm import LLMProvider
from fulfilltwin.backend.services.memory import JsonMemoryStore
from fulfilltwin.backend.services.ml_engine import OperationalMLEngine
from fulfilltwin.backend.services.optimizer import RecoveryOptimizer
from fulfilltwin.backend.services.rag import LocalRagEngine

REQUIRED_FIELDS = {
    "order_volume_pct": (-30, 100),
    "absenteeism_pct": (0, 45),
    "conveyor_capacity_pct": (20, 110),
    "dock_congestion_pct": (0, 100),
    "energy_price_pct": (-30, 160),
    "inventory_availability_pct": (40, 100),
    "current_backlog": (0, 15000),
    "workers": (20, 500),
    "base_throughput": (200, 5000),
    "horizon_hours": (1, 24),
}


def _validate_scenario(payload: dict[str, Any]) -> dict[str, float]:
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError(f"Missing scenario fields: {', '.join(missing)}")
    result: dict[str, float] = {}
    for field, (low, high) in REQUIRED_FIELDS.items():
        value = float(payload[field])
        if not low <= value <= high:
            raise ValueError(f"{field} must be between {low} and {high}")
        result[field] = value
    return result


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__)
    if test_config:
        app.config.update(test_config)
    CORS(app)

    memory = JsonMemoryStore(settings.memory_file, settings.max_memory_records)
    rag = LocalRagEngine(KNOWLEDGE_DIR)
    ml = OperationalMLEngine(ARTIFACT_DIR, settings.model_seed, settings.training_rows)
    llm = LLMProvider(settings)
    council = AgentCouncil(ml, ExpertSystem(), rag, RecoveryOptimizer(), llm, memory)

    @app.get("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "service": "FulfillTwin AI API",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "models_ready": bool(ml.metrics),
                "knowledge_chunks": len(rag.chunks),
            }
        )

    @app.get("/api/config/models")
    def models():
        return jsonify(llm.available_models())

    @app.post("/api/scenario/run")
    def run_scenario():
        try:
            payload = request.get_json(force=True) or {}
            scenario = _validate_scenario(payload.get("scenario", payload))
            provider = str(payload.get("provider", "LOCAL"))
            model = str(payload.get("model", "expert-system-v1"))
            return jsonify(council.run(scenario, provider=provider, model=model))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception as exc:
            app.logger.exception("Scenario execution failed")
            return jsonify({"error": f"Scenario execution failed: {type(exc).__name__}: {exc}"}), 500

    @app.post("/api/scenario/approve/<run_id>")
    def approve_scenario(run_id: str):
        updated = memory.approve_run(run_id)
        if not updated:
            return jsonify({"error": "Run not found"}), 404
        return jsonify({"status": "approved", "run": updated})

    @app.post("/api/rag/search")
    def rag_search():
        payload = request.get_json(force=True) or {}
        query = str(payload.get("query", ""))
        top_k = int(payload.get("top_k", 5))
        return jsonify({"query": query, "results": rag.search(query, max(1, min(top_k, 10)))})

    @app.post("/api/rag/refresh")
    def rag_refresh():
        rag.refresh()
        return jsonify({"status": "refreshed", "knowledge_chunks": len(rag.chunks)})

    @app.get("/api/memory")
    def list_memory():
        limit = int(request.args.get("limit", "25"))
        return jsonify({"runs": memory.list(max(1, min(limit, 100)))})

    @app.delete("/api/memory")
    def clear_memory():
        memory.clear()
        return jsonify({"status": "cleared"})

    @app.get("/api/model-card")
    def model_card():
        return jsonify(ml.model_card())

    @app.post("/api/models/retrain")
    def retrain():
        return jsonify({"status": "retrained", "metrics": ml.train()})

    @app.get("/api/events")
    def events():
        count = max(5, min(int(request.args.get("count", "12")), 50))
        rng = random.Random(int(datetime.now(timezone.utc).timestamp() // 60))
        event_types = ["ORDER_SURGE", "CONVEYOR_ALERT", "LABOR_UPDATE", "TRAILER_ARRIVAL", "REPLENISHMENT_DELAY", "ENERGY_SIGNAL"]
        rows = []
        for idx in range(count):
            event = rng.choice(event_types)
            severity = rng.choices(["INFO", "WATCH", "HIGH", "CRITICAL"], weights=[45, 30, 20, 5])[0]
            rows.append(
                {
                    "event_id": f"EVT-{rng.randint(10000, 99999)}",
                    "type": event,
                    "severity": severity,
                    "zone": rng.choice(["Inbound", "Receive", "Pick", "Pack", "Sort", "Outbound", "Yard"]),
                    "value": round(rng.uniform(0.2, 1.0), 2),
                    "minutes_ago": idx * rng.randint(1, 4),
                }
            )
        return jsonify({"events": rows})

    return app


if __name__ == "__main__":
    create_app().run(host=settings.api_host, port=settings.api_port, debug=False)
