import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_health_check():
    """Test GET /api/health returns status ok and phase 1."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["phase"] == "1"
    assert data["service"] == "reseller-agent-api"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"
