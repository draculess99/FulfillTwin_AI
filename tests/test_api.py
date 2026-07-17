from fulfilltwin.backend.app import create_app


def test_health_endpoint():
    app = create_app({"TESTING": True})
    client = app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_scenario_validation():
    app = create_app({"TESTING": True})
    client = app.test_client()
    response = client.post("/api/scenario/run", json={"scenario": {"order_volume_pct": 10}})
    assert response.status_code == 400
