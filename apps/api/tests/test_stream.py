"""Tests for Server-Sent Events (SSE) streaming orchestration endpoint and generator."""

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.graph.workflow import stream_reseller_orchestration
from src.main import app
from src.models.auth import BYOKCredentials

client = TestClient(app)


@pytest.mark.asyncio
async def test_stream_reseller_orchestration_generator_sequence():
    """Verify that stream_reseller_orchestration yields AGENT_START, AGENT_COMPLETE for all nodes, and FINAL_RESULT."""
    initial_state = {
        "user_input": "Sony WH-1000XM4 Wireless Noise Cancelling Headphones",
        "item_description": {
            "name": "Sony WH-1000XM4",
            "condition": "Used - Like New",
            "estimated_retail_price": 349.0,
            "key_features": ["ANC", "30hr battery", "Bluetooth 5.0"],
            "summary": "Pristine headphones.",
            "category": "Audio",
        },
        "capital_cost": 2_000_000.0,
    }

    events = []
    async for event in stream_reseller_orchestration(initial_state, mock=True):
        events.append(event)

    assert len(events) >= 11  # 5 starts + 5 completes + 1 final result

    event_types = [e["type"] for e in events]
    assert "AGENT_START" in event_types
    assert "AGENT_COMPLETE" in event_types
    assert "FINAL_RESULT" in event_types
    assert event_types[-1] == "FINAL_RESULT"

    # Verify all 5 agents executed
    start_agents = [e["agent"] for e in events if e["type"] == "AGENT_START"]
    complete_agents = [e["agent"] for e in events if e["type"] == "AGENT_COMPLETE"]

    expected_agents = [
        "market_scout",
        "trend_analyst",
        "pricing_strategist",
        "chief_strategist",
        "customer_persona",
    ]
    for agent in expected_agents:
        assert agent in start_agents
        assert agent in complete_agents

    # Verify FINAL_RESULT contains required fields
    final_event = events[-1]
    assert final_event["type"] == "FINAL_RESULT"
    assert final_event["status"] == "success"
    assert final_event["verdict"] in ["BUY", "PASS"]
    assert final_event["final_strategy"] != ""
    assert "tiers" in final_event["pricing_strategy"]
    assert len(final_event["market_prices"]) > 0
    assert final_event["scout_summary"] is not None
    assert final_event["trend_analysis"] != ""
    assert len(final_event["agent_logs"]) >= 5


@pytest.mark.asyncio
async def test_stream_reseller_orchestration_error_handling():
    """Verify that unhandled exceptions during streaming yield an ERROR event gracefully."""
    initial_state = {
        "user_input": "Corrupted input triggering error",
    }

    with patch("src.graph.workflow.create_reseller_graph", side_effect=RuntimeError("Graph compilation exploded")):
        events = []
        async for event in stream_reseller_orchestration(initial_state, mock=True):
            events.append(event)

        assert len(events) == 1
        assert events[0]["type"] == "ERROR"
        assert "Graph compilation exploded" in events[0]["error"]
        assert "Swarm orchestration failed" in events[0]["message"]


def test_api_orchestrate_stream_endpoint_sse_output():
    """Test POST /api/orchestrate/stream returns valid text/event-stream SSE events."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "test_stream_key",
    }
    payload = {
        "text": "Nintendo Switch OLED Neon Blue/Red",
        "capital_cost": 3_000_000.0,
        "mock": True,
    }

    response = client.post("/api/orchestrate/stream", json=payload, headers=headers)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]

    # Parse SSE stream text lines
    lines = response.text.strip().split("\n\n")
    assert len(lines) >= 11

    parsed_events = []
    for line in lines:
        line_clean = line.strip()
        if line_clean.startswith("data: "):
            json_str = line_clean[6:]
            parsed_events.append(json.loads(json_str))

    types = [e["type"] for e in parsed_events]
    assert "AGENT_START" in types
    assert "AGENT_COMPLETE" in types
    assert "FINAL_RESULT" in types
    assert types[-1] == "FINAL_RESULT"

    final_result = parsed_events[-1]
    assert final_result["verdict"] in ["BUY", "PASS"]
    assert "tiers" in final_result["pricing_strategy"]
    assert len(final_result["market_prices"]) > 0


def test_api_orchestrate_stream_endpoint_with_structured_item():
    """Test POST /api/orchestrate/stream with structured item_description."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "test_stream_key",
    }
    payload = {
        "item_description": {
            "name": "Fujifilm X-T30 Body",
            "condition": "Used - Good",
            "estimated_retail_price": 799.0,
            "key_features": ["26.1MP", "4K Video"],
            "summary": "Clean Fujifilm camera body.",
            "category": "Cameras & Lenses",
        },
        "capital_cost": 7_500_000.0,
        "mock": True,
    }

    response = client.post("/api/orchestrate/stream", json=payload, headers=headers)
    assert response.status_code == 200

    lines = response.text.strip().split("\n\n")
    events = [json.loads(line.strip()[6:]) for line in lines if line.strip().startswith("data: ")]

    assert len(events) >= 11
    final_event = events[-1]
    assert final_event["type"] == "FINAL_RESULT"
    assert final_event["verdict"] in ["BUY", "PASS"]


def test_api_orchestrate_stream_validation_error():
    """Test POST /api/orchestrate/stream validates empty inputs returning 422."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "test_stream_key",
    }
    payload = {}

    response = client.post("/api/orchestrate/stream", json=payload, headers=headers)
    assert response.status_code == 422
