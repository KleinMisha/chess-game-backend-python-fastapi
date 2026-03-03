"""unit test for health check: src/api/v1/health.py"""

from fastapi.testclient import TestClient

from src.main import app

# Setup test client:
client = TestClient(app)


# -- SIMPLE TEST OF HEALTH CHECK ---
def test_health_check() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
