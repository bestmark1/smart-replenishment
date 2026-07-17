from fastapi.testclient import TestClient

from smart_replenishment.api.main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "ok"
    assert "champion_model" in json_data
