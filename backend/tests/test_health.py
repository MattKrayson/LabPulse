def test_health_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "LabPulse"
    assert body["database"] == "ok"
    assert "timestamp" in body
