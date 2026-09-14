import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from src.main import app
from src.models.item import ItemDescription

client = TestClient(app)


def test_parse_item_validation_error_empty_payload():
    """Test POST /api/parse-item returns 422 when neither text nor image_base64 is provided."""
    response = client.post("/api/parse-item", json={})
    assert response.status_code == 422


def test_parse_item_mock_mode_with_text():
    """Test POST /api/parse-item with mock/test credentials and text input."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "test_key",
    }
    payload = {
        "text": "Used iPhone 13 Pro in good condition with minor scratches"
    }
    response = client.post("/api/parse-item", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["provider_used"] == "mock"
    assert "iPhone 13 Pro" in data["item"]["name"]
    assert data["item"]["condition"] == "Used - Good"
    assert data["item"]["estimated_retail_price"] == 699.0


def test_parse_item_mock_mode_with_image():
    """Test POST /api/parse-item with image base64 input."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "test_key",
    }
    payload = {
        "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    }
    response = client.post("/api/parse-item", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "item" in data
    assert data["item"]["name"] is not None


@patch("src.routes.parser.LLMService")
def test_parse_item_with_mocked_llm_service(mock_llm_service_class):
    """Test POST /api/parse-item using a mocked LLMService."""
    mock_service_instance = MagicMock()
    mock_service_instance.provider = "openai"
    mock_service_instance.model = "gpt-4o-mini"
    mock_service_instance.parse_item_description.return_value = ItemDescription(
        name="Nike Air Max 90",
        condition="New",
        estimated_retail_price=130.0,
        key_features=["Classic design", "Air cushioning"],
        summary="Brand new Nike Air Max 90 sneakers",
        category="Footwear"
    )
    mock_llm_service_class.return_value = mock_service_instance

    headers = {
        "X-LLM-Provider": "openai",
        "X-API-Key": "sk-test12345",
        "X-LLM-Model": "gpt-4o-mini",
    }
    payload = {"text": "Brand new Nike Air Max 90"}

    response = client.post("/api/parse-item", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["provider_used"] == "openai"
    assert data["model_used"] == "gpt-4o-mini"
    assert data["item"]["name"] == "Nike Air Max 90"
    assert data["item"]["estimated_retail_price"] == 130.0
