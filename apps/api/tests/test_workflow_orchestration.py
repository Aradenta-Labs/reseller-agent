"""Unit and integration tests for LangGraph workflow and FastAPI orchestration endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.graph.workflow import create_reseller_graph, run_reseller_orchestration
from src.main import app
from src.models.auth import BYOKCredentials
from src.models.orchestrate import OrchestrateRequest, OrchestrateResponse

client = TestClient(app)


@pytest.mark.asyncio
async def test_langgraph_workflow_compilation_and_execution():
    """Verify that create_reseller_graph compiles and executes all 5 nodes correctly in mock mode."""
    credentials = BYOKCredentials(provider="mock", api_key="test_key")
    initial_state = {
        "user_input": "Sony PlayStation 5 Disc Edition Bekas Like New",
        "item_description": {
            "name": "Sony PlayStation 5 Disc Edition",
            "condition": "Used - Like New",
            "estimated_retail_price": 499.0,
            "key_features": ["Disc Edition", "White", "Fullset Box"],
            "summary": "PS5 disc edition in great condition.",
            "category": "Gaming Consoles",
        },
        "capital_cost": 5_500_000.0,
    }

    final_state = await run_reseller_orchestration(
        initial_state=initial_state,
        credentials=credentials,
        mock=True,
    )

    # 1. Check market scout populated
    assert "market_prices" in final_state
    assert len(final_state["market_prices"]) > 0
    assert final_state["scout_summary"] is not None

    # 2. Check trend analyst populated
    assert "trend_analysis" in final_state
    assert len(final_state["trend_analysis"]) > 0

    # 3. Check pricing strategist populated (with 3 tiers)
    assert "pricing_strategy" in final_state
    pricing = final_state["pricing_strategy"]
    assert "tiers" in pricing
    assert "fast_sale" in pricing["tiers"]
    assert "patient_sale" in pricing["tiers"]
    assert "direct_sale" in pricing["tiers"]
    assert "target_buy_price" in pricing

    # 4. Check chief strategist populated
    assert "final_strategy" in final_state
    assert len(final_state["final_strategy"]) > 0

    # 5. Check customer persona populated with verdict
    assert "customer_verdict" in final_state
    assert final_state["customer_verdict"] in ["BUY", "PASS"]

    # 6. Check all agent logs collected
    assert "agent_logs" in final_state
    agent_names = [log["agent"] for log in final_state["agent_logs"]]
    assert "scout" in agent_names
    assert "analyst" in agent_names
    assert "pricing" in agent_names
    assert "chief" in agent_names
    assert "customer" in agent_names


def test_api_orchestrate_endpoint_with_text():
    """Test POST /api/orchestrate with unstructured text and mock BYOK credentials."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "test_mock_key_123",
        "X-LLM-Model": "mock-v1",
    }
    payload = {
        "text": "Nintendo Switch OLED White Joy-Con Mulus Fullset Box",
        "capital_cost": 3_200_000.0,
        "mock": True,
    }

    response = client.post("/api/orchestrate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    resp = OrchestrateResponse(**data)
    assert resp.status == "success"
    assert resp.item_description is not None
    assert resp.scout_summary is not None
    assert len(resp.market_prices) > 0
    assert resp.trend_analysis != ""
    assert "tiers" in resp.pricing_strategy
    assert resp.final_strategy != ""
    assert resp.customer_verdict in ["BUY", "PASS"]
    assert len(resp.agent_logs) >= 5


def test_api_orchestrate_endpoint_with_structured_item():
    """Test POST /api/orchestrate with pre-parsed item_description dict."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "test_mock_key_123",
    }
    payload = {
        "item_description": {
            "name": "Fujifilm X-T30 Mirrorless Camera Body Only",
            "condition": "Used - Good",
            "estimated_retail_price": 799.0,
            "key_features": ["26.1MP", "4K Video", "Black"],
            "summary": "Fujifilm X-T30 body in black condition.",
            "category": "Cameras & Lenses",
        },
        "capital_cost": 8_000_000.0,
        "mock": True,
    }

    response = client.post("/api/orchestrate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["customer_verdict"] in ["BUY", "PASS"]
    assert "tiers" in data["pricing_strategy"]
    assert len(data["market_prices"]) > 0


def test_api_orchestrate_validation_error_on_empty_input():
    """Test POST /api/orchestrate fails validation (HTTP 422) if no text/image/item is given."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "test_mock_key_123",
    }
    payload = {}

    response = client.post("/api/orchestrate", json=payload, headers=headers)
    assert response.status_code == 422
