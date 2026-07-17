from __future__ import annotations

import os
from typing import Any

import requests


class ApiClient:
    def __init__(self, base_url: str | None = None, timeout: int = 90) -> None:
        self.base_url = (base_url or os.getenv("FULFILLTWIN_API_URL", "http://127.0.0.1:5000")).rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = requests.request(method, f"{self.base_url}{path}", timeout=self.timeout, **kwargs)
        try:
            data = response.json()
        except ValueError:
            data = {"error": response.text or f"HTTP {response.status_code}"}
        if not response.ok:
            raise RuntimeError(data.get("error", f"HTTP {response.status_code}"))
        return data

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def models(self) -> dict[str, Any]:
        return self._request("GET", "/api/config/models")

    def run_scenario(self, scenario: dict[str, Any], provider: str, model: str) -> dict[str, Any]:
        return self._request("POST", "/api/scenario/run", json={"scenario": scenario, "provider": provider, "model": model})

    def approve_scenario(self, run_id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/scenario/approve/{run_id}")

    def search_rag(self, query: str, top_k: int = 5) -> dict[str, Any]:
        return self._request("POST", "/api/rag/search", json={"query": query, "top_k": top_k})

    def refresh_rag(self) -> dict[str, Any]:
        return self._request("POST", "/api/rag/refresh")

    def memory(self, limit: int = 25) -> dict[str, Any]:
        return self._request("GET", f"/api/memory?limit={limit}")

    def clear_memory(self) -> dict[str, Any]:
        return self._request("DELETE", "/api/memory")

    def model_card(self) -> dict[str, Any]:
        return self._request("GET", "/api/model-card")

    def retrain(self) -> dict[str, Any]:
        return self._request("POST", "/api/models/retrain")

    def events(self, count: int = 12) -> dict[str, Any]:
        return self._request("GET", f"/api/events?count={count}")
