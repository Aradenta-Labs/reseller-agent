import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.models.item import ItemDescription

client = TestClient(app)


def test_e2e_health_check():
    """Verify health endpoint returns status, service, and version."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["phase"] == "1"
    assert data["service"] == "reseller-agent-api"
    assert data["version"] == "0.1.0"
    assert data["environment"] == "development"


def test_e2e_byok_headers_and_mock_payload():
    """Verify acceptance of BYOK headers and deterministic mock schema parsing."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "mock_api_key_123",
        "X-LLM-Model": "mock-v1",
    }
    payload = {
        "text": "Sony WH-1000XM4 Wireless Noise Cancelling Headphones, Black. Used for 6 months.",
    }
    response = client.post("/api/parse-item", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["provider_used"] == "mock"
    assert data["model_used"] == "mock-v1"

    item = ItemDescription(**data["item"])
    assert item.name
    assert item.condition
    assert isinstance(item.key_features, list)
    assert len(item.key_features) > 0


def test_e2e_byok_headers_image_payload():
    """Verify acceptance of BYOK headers and base64 image payload."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "",
    }
    payload = {
        "image_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
    }
    response = client.post("/api/parse-item", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    item = ItemDescription(**data["item"])
    assert item.name
    assert item.category


def test_e2e_byok_openai_fallback_on_invalid_key():
    """Verify that when a live provider key fails/is mocked, graceful fallback is applied."""
    headers = {
        "X-LLM-Provider": "openai",
        "X-API-Key": "invalid-openai-key-for-test",
        "X-LLM-Model": "gpt-4o-mini",
    }
    payload = {
        "text": "Vintage Nike ACG Fleece Jacket Size L",
    }
    response = client.post("/api/parse-item", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    item = ItemDescription(**data["item"])
    assert item.name
    assert item.condition
