import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.models.item import ItemDescription
from src.models.scout import MarketScoutReport

client = TestClient(app)


def test_e2e_health_check():
    """Verify health endpoint returns status, service, and version."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "phase" in data
    assert data["service"] == "reseller-agent-api"
    assert "version" in data
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


def test_e2e_market_scout_search():
    """Verify Market Scout search endpoint returns comprehensive cross-platform report."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "test_key",
    }
    payload = {
        "text": "Apple MacBook Air M1 2020 8GB 256GB mulus fullset",
        "mock": True,
        "max_results_per_platform": 5,
    }
    response = client.post("/api/scout/search", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    report = MarketScoutReport(**data)
    assert report.total_listings_found > 0
    assert report.overall_lowest_price > 0
    assert report.overall_highest_price >= report.overall_lowest_price
    assert report.best_platform_recommendation in ["Tokopedia", "Shopee", "Facebook Marketplace"]
    assert len(report.platform_results) == 3


def test_e2e_full_analyze_flow():
    """Verify full multi-stage analysis flow: Item parsing + Market Scout Agent."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "test_key",
    }
    payload = {
        "text": "Dijual sepatu Nike Air Jordan 1 Retro High Chicago size 42 kondisi like new dengan box",
        "mock": True,
    }
    response = client.post("/api/analyze", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "parsed_item" in data
    assert "scout_report" in data

    parsed = ItemDescription(**data["parsed_item"])
    assert "Jordan" in parsed.name or "Nike" in parsed.name

    report = MarketScoutReport(**data["scout_report"])
    assert report.total_listings_found > 0
    assert report.overall_average_price > 0
    assert report.summary_insights is not None
