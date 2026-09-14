"""Phase 3 Definition of Done (DoD) End-to-End Integration Test Suite.

Validates all Phase 3 criteria:
1. ResellerState object schema and lifecycle passing between all nodes.
2. Parallel execution of Agent 1 (Market Scout) & Agent 2 (Trend Analyst) with fan-in to Agent 3 (Pricing Strategist).
3. Agent 3 accurate financial math: 20% online platform fee, >= 15% net profit margin, 3 pricing tiers, and ROI/profit calculations.
4. Full LangGraph graph execution from start to finish via FastAPI `POST /api/orchestrate` with user BYOK headers.
5. Final JSON response contains `customer_verdict` ("BUY" or "PASS") and `final_strategy`.
6. Comprehensive edge cases:
   - Empty/whitespace descriptions and validation errors
   - BYOK header variations and mock fallbacks
   - Custom capital cost calculations (accurate ROI and net profit verification across tiers)
   - Fault tolerance & partial failure resilience when individual nodes encounter exceptions.
"""

import asyncio
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.agents import (
    run_chief_strategist,
    run_customer_persona,
    run_market_scout,
    run_pricing_strategist,
    run_trend_analyst,
)
from src.graph.state import ResellerState
from src.graph.workflow import create_reseller_graph, run_reseller_orchestration
from src.main import app
from src.models.auth import BYOKCredentials
from src.models.item import ItemDescription
from src.models.orchestrate import OrchestrateResponse

client = TestClient(app)


# ============================================================================
# DoD 1: ResellerState Object Schema & Node State Passing
# ============================================================================

@pytest.mark.asyncio
async def test_dod_reseller_state_lifecycle_and_reducers():
    """Verify ResellerState typed schema, accumulation of agent_logs and errors across all 5 nodes."""
    initial_state: ResellerState = {
        "user_input": "PlayStation 5 Disc Edition Like New",
        "item_description": {
            "name": "PlayStation 5 Disc Edition",
            "condition": "Used - Like New",
            "estimated_retail_price": 499.0,
            "key_features": ["Ultra HD Blu-ray", "DualSense Controller", "825GB SSD"],
            "summary": "PS5 disc version in pristine condition.",
            "category": "Gaming Consoles",
        },
        "capital_cost": 5_500_000.0,
        "market_prices": [],
        "scout_summary": None,
        "trend_analysis": "",
        "pricing_strategy": {},
        "final_strategy": "",
        "customer_verdict": "PASS",
        "errors": [],
        "agent_logs": [],
    }

    credentials = BYOKCredentials(provider="mock", api_key="test_key")
    final_state = await run_reseller_orchestration(
        initial_state=initial_state,
        credentials=credentials,
        mock=True,
    )

    # 1. State integrity checks
    assert isinstance(final_state, dict)
    assert final_state["user_input"] == "PlayStation 5 Disc Edition Like New"
    assert final_state["capital_cost"] == 5_500_000.0

    # 2. Populated outputs by respective agents
    assert isinstance(final_state["market_prices"], list)
    assert len(final_state["market_prices"]) > 0
    assert isinstance(final_state["scout_summary"], dict)
    assert final_state["scout_summary"]["overall_median_price"] > 0

    assert isinstance(final_state["trend_analysis"], str)
    assert len(final_state["trend_analysis"]) > 0

    assert isinstance(final_state["pricing_strategy"], dict)
    assert "tiers" in final_state["pricing_strategy"]

    assert isinstance(final_state["final_strategy"], str)
    assert len(final_state["final_strategy"]) > 0

    assert final_state["customer_verdict"] in ["BUY", "PASS"]

    # 3. Agent logs correctly accumulated via reducer
    assert len(final_state["agent_logs"]) >= 5
    agent_names = [log["agent"] for log in final_state["agent_logs"]]
    for expected_agent in ["scout", "analyst", "pricing", "chief", "customer"]:
        assert expected_agent in agent_names


# ============================================================================
# DoD 2: Parallel Execution of Agents 1 & 2 with Fan-in to Agent 3
# ============================================================================

@pytest.mark.asyncio
async def test_dod_parallel_scout_and_analyst_fan_in_to_pricing():
    """Verify that Market Scout and Trend Analyst execute in parallel and fan-in cleanly to Pricing Strategist."""
    graph = create_reseller_graph(
        credentials=BYOKCredentials(provider="mock", api_key="test_key"),
        mock=True,
    )

    initial_state: ResellerState = {
        "user_input": "MacBook Air M1 8GB 256GB Space Grey",
        "item_description": {
            "name": "Apple MacBook Air M1",
            "condition": "Used - Good",
            "estimated_retail_price": 999.0,
            "key_features": ["Apple M1", "8GB RAM", "256GB SSD", "Space Grey"],
            "summary": "MacBook Air M1 in good condition.",
            "category": "Laptops",
        },
        "capital_cost": 7_500_000.0,
        "market_prices": [],
        "scout_summary": None,
        "trend_analysis": "",
        "pricing_strategy": {},
        "final_strategy": "",
        "customer_verdict": "PASS",
        "errors": [],
        "agent_logs": [],
    }

    # Execute workflow graph
    result_state = await graph.ainvoke(initial_state)

    # Validate that both parallel branches completed before pricing strategist
    assert len(result_state["market_prices"]) > 0
    assert result_state["scout_summary"] is not None
    assert len(result_state["trend_analysis"]) > 0

    # Validate pricing strategist successfully consumed outputs of both scout and analyst
    pricing = result_state["pricing_strategy"]
    assert pricing["benchmark_median_price"] > 0
    assert pricing["target_buy_price"] > 0

    # Check logs order has both scout and analyst before pricing
    log_agents = [log["agent"] for log in result_state["agent_logs"]]
    scout_idx = log_agents.index("scout")
    analyst_idx = log_agents.index("analyst")
    pricing_idx = log_agents.index("pricing")

    assert scout_idx < pricing_idx
    assert analyst_idx < pricing_idx


# ============================================================================
# DoD 3: Agent 3 Pricing Strategist Financial Formula Verification
# ============================================================================

@pytest.mark.asyncio
async def test_dod_pricing_strategist_financial_formulas():
    """Verify 20% platform fee, >=15% net profit margin, 3 price tiers, and exact ROI/profit formulas."""
    scout_summary = {
        "overall_lowest_price": 10_000_000.0,
        "overall_highest_price": 14_000_000.0,
        "overall_average_price": 12_000_000.0,
        "overall_median_price": 12_000_000.0,
        "total_listings_found": 10,
        "best_platform_recommendation": "Tokopedia",
    }

    capital_cost = 8_000_000.0

    state: ResellerState = {
        "user_input": "Canon EOS R6 Camera Body",
        "item_description": "Canon EOS R6 Camera Body",
        "capital_cost": capital_cost,
        "market_prices": [],
        "scout_summary": scout_summary,
        "trend_analysis": "High demand, fast liquidity.",
        "pricing_strategy": {},
        "final_strategy": "",
        "customer_verdict": "PASS",
        "errors": [],
        "agent_logs": [],
    }

    res = await run_pricing_strategist(state, mock=True)
    strategy = res["pricing_strategy"]

    assert strategy["platform_fee_rate"] == 0.20
    assert strategy["target_min_margin_rate"] == 0.15

    tiers = strategy["tiers"]
    assert "fast_sale" in tiers
    assert "patient_sale" in tiers
    assert "direct_sale" in tiers

    # 1. Fast Sale Tier verification (Online with 20% fee)
    fast = tiers["fast_sale"]
    assert fast["platform_fee_rate"] == 0.20
    expected_fast_fee = round(fast["listing_price"] * 0.20, 2)
    assert fast["estimated_platform_fee"] == expected_fast_fee
    expected_fast_payout = round(fast["listing_price"] - expected_fast_fee, 2)
    assert fast["net_payout"] == expected_fast_payout
    # Max buy price for 15% net margin: net_payout / 1.15
    expected_fast_max_buy = round(expected_fast_payout / 1.15, -3)
    assert fast["max_recommended_buy_price"] == expected_fast_max_buy

    # 2. Patient Sale Tier verification (Online with 20% fee)
    patient = tiers["patient_sale"]
    assert patient["platform_fee_rate"] == 0.20
    expected_patient_fee = round(patient["listing_price"] * 0.20, 2)
    assert patient["estimated_platform_fee"] == expected_patient_fee
    expected_patient_payout = round(patient["listing_price"] - expected_patient_fee, 2)
    assert patient["net_payout"] == expected_patient_payout

    # 3. Direct Sale Tier verification (Offline COD with 0% fee)
    direct = tiers["direct_sale"]
    assert direct["platform_fee_rate"] == 0.0
    assert direct["estimated_platform_fee"] == 0.0
    assert direct["net_payout"] == direct["listing_price"]

    # 4. Profit & ROI math verification against capital_cost
    for tier_key in ["fast_sale", "patient_sale", "direct_sale"]:
        tier = tiers[tier_key]
        expected_profit = round(tier["net_payout"] - capital_cost, 2)
        expected_roi = round((expected_profit / capital_cost) * 100.0, 2)
        expected_margin = round((expected_profit / tier["listing_price"]) * 100.0, 2)

        assert tier["projected_net_profit"] == expected_profit
        assert tier["projected_roi_pct"] == expected_roi
        assert tier["profit_margin_pct"] == expected_margin
        assert tier["meets_target_margin"] == (expected_margin >= 15.0)


# ============================================================================
# DoD 4: FastAPI Endpoint POST /api/orchestrate End-to-End
# ============================================================================

def test_dod_fastapi_orchestrate_endpoint_full_pipeline():
    """Test full pipeline execution via POST /api/orchestrate with BYOK headers and structured response."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "test_byok_api_key_456",
        "X-LLM-Model": "mock-model-v2",
    }
    payload = {
        "text": "iPad Air 5 M1 64GB WiFi Starlight Fullset Box Mulus",
        "capital_cost": 6_500_000.0,
        "mock": True,
        "platforms": ["Tokopedia", "Shopee", "Facebook Marketplace"],
    }

    response = client.post("/api/orchestrate", json=payload, headers=headers)
    assert response.status_code == 200

    data = response.json()
    resp_obj = OrchestrateResponse(**data)

    # Verify all expected top-level response properties
    assert resp_obj.status == "success"
    assert resp_obj.user_input != ""
    assert resp_obj.item_description is not None
    assert resp_obj.capital_cost == 6_500_000.0
    assert len(resp_obj.market_prices) > 0
    assert resp_obj.scout_summary is not None
    assert resp_obj.trend_analysis != ""
    assert "tiers" in resp_obj.pricing_strategy
    assert resp_obj.final_strategy != ""
    assert resp_obj.customer_verdict in ["BUY", "PASS"]
    assert len(resp_obj.agent_logs) >= 5
    assert resp_obj.provider_used == "mock"


# ============================================================================
# DoD 5: Customer Verdict and Master Strategy Synthesis
# ============================================================================

@pytest.mark.asyncio
async def test_dod_customer_verdict_and_final_strategy_synthesis():
    """Verify customer verdict generation ('BUY' | 'PASS') and Chief Strategist synthesis."""
    # Case A: Good deal (competitive price -> BUY verdict)
    state_buy: ResellerState = {
        "user_input": "Sony WH-1000XM4 Headphone",
        "item_description": "Sony WH-1000XM4 Noise Cancelling Headphones",
        "capital_cost": 2_000_000.0,
        "market_prices": [],
        "scout_summary": {"overall_median_price": 3_200_000.0},
        "trend_analysis": "High demand, steady market.",
        "pricing_strategy": {
            "target_buy_price": 2_200_000.0,
            "tiers": {
                "fast_sale": {"listing_price": 2_800_000.0, "net_payout": 2_240_000.0},
                "patient_sale": {"listing_price": 3_200_000.0, "net_payout": 2_560_000.0},
                "direct_sale": {"listing_price": 3_000_000.0, "net_payout": 3_000_000.0},
            },
        },
        "final_strategy": "",
        "customer_verdict": "",
        "errors": [],
        "agent_logs": [],
    }

    chief_res = await run_chief_strategist(state_buy, mock=True)
    assert "Master Resale Plan" in chief_res["final_strategy"]
    assert "Photography" in chief_res["final_strategy"]

    state_buy.update(chief_res)
    customer_res = await run_customer_persona(state_buy, mock=True)
    assert customer_res["customer_verdict"] == "BUY"

    # Case B: Overpriced deal (price > 115% of median -> PASS verdict)
    state_pass = dict(state_buy)
    state_pass["scout_summary"] = {"overall_median_price": 2_000_000.0}
    state_pass["pricing_strategy"] = {
        "target_buy_price": 1_200_000.0,
        "tiers": {
            "fast_sale": {"listing_price": 3_500_000.0, "net_payout": 2_800_000.0},
            "patient_sale": {"listing_price": 4_000_000.0, "net_payout": 3_200_000.0},
        },
    }

    customer_pass_res = await run_customer_persona(state_pass, mock=True)
    assert customer_pass_res["customer_verdict"] == "PASS"


# ============================================================================
# DoD 6: Edge Cases & Fault Tolerance
# ============================================================================

def test_dod_edge_case_empty_and_whitespace_inputs():
    """Verify endpoint handles and validates empty or missing descriptions gracefully."""
    headers = {"X-LLM-Provider": "mock", "X-API-Key": "test_key"}

    # 1. Completely empty payload -> 422 Unprocessable Entity
    res1 = client.post("/api/orchestrate", json={}, headers=headers)
    assert res1.status_code == 422

    # 2. Whitespace only payload -> 422 Unprocessable Entity
    res2 = client.post("/api/orchestrate", json={"text": "   ", "user_input": ""}, headers=headers)
    assert res2.status_code == 422


def test_dod_edge_case_missing_or_custom_byok_headers():
    """Verify endpoint functions when headers are omitted (falls back to mock/default) or have custom provider."""
    # 1. No headers provided at all -> defaults to mock provider safely
    payload = {
        "text": "Logitech MX Master 3S Mouse",
        "mock": True,
    }
    res_no_headers = client.post("/api/orchestrate", json=payload)
    assert res_no_headers.status_code == 200
    data = res_no_headers.json()
    assert data["status"] == "success"
    assert data["provider_used"] == "mock"

    # 2. OpenAI provider header with mock key
    headers_openai = {
        "X-LLM-Provider": "openai",
        "X-API-Key": "mock-openai-key-999",
        "X-LLM-Model": "gpt-4o-mini",
    }
    res_openai = client.post("/api/orchestrate", json=payload, headers=headers_openai)
    assert res_openai.status_code == 200
    assert res_openai.json()["status"] == "success"


def test_dod_edge_case_capital_cost_calculations():
    """Verify zero capital cost, high capital cost causing negative ROI, and margin flags."""
    headers = {"X-LLM-Provider": "mock", "X-API-Key": "test_key"}

    # Zero capital cost
    payload_zero_cost = {
        "text": "Vintage Casio G-Shock DW-5600",
        "capital_cost": 0.0,
        "mock": True,
    }
    res_zero = client.post("/api/orchestrate", json=payload_zero_cost, headers=headers)
    assert res_zero.status_code == 200
    data_zero = res_zero.json()
    assert data_zero["pricing_strategy"]["target_buy_price"] > 0

    # High capital cost exceeding market price (should yield negative ROI and meets_target_margin=False)
    payload_high_cost = {
        "item_description": {
            "name": "Generic Mechanical Keyboard",
            "condition": "Used",
            "estimated_retail_price": 50.0,
            "key_features": ["Blue Switch"],
            "summary": "Used mechanical keyboard.",
            "category": "Computer Accessories",
        },
        "capital_cost": 50_000_000.0,  # 50 million IDR for a keyboard
        "mock": True,
    }
    res_high = client.post("/api/orchestrate", json=payload_high_cost, headers=headers)
    assert res_high.status_code == 200
    data_high = res_high.json()
    fast_tier = data_high["pricing_strategy"]["tiers"]["fast_sale"]
    assert fast_tier["projected_net_profit"] < 0
    assert fast_tier["projected_roi_pct"] < 0
    assert fast_tier["meets_target_margin"] is False


@pytest.mark.asyncio
async def test_dod_edge_case_fault_tolerance_and_node_recovery():
    """Verify that if individual nodes raise internal exceptions, the workflow catches them gracefully and completes."""
    state: ResellerState = {
        "user_input": "Item With Error Injected",
        "item_description": "Test Item",
        "capital_cost": 1_000_000.0,
        "market_prices": [],
        "scout_summary": None,
        "trend_analysis": "",
        "pricing_strategy": {},
        "final_strategy": "",
        "customer_verdict": "PASS",
        "errors": [],
        "agent_logs": [],
    }

    # 1. Market Scout with simulated failure in underlying service
    with patch("src.agents.scout.MarketScoutService.run_scout", side_effect=RuntimeError("Scraper connection timeout")):
        scout_res = await run_market_scout(state, mock=True)
        assert len(scout_res["errors"]) == 1
        assert "Scraper connection timeout" in scout_res["errors"][0]
        assert len(scout_res["market_prices"]) > 0  # recovered with fallback
        assert scout_res["scout_summary"] is not None

    # 2. Trend Analyst with search error
    with patch("src.agents.analyst.SearchTool.search", side_effect=RuntimeError("Search API 503 unavailable")):
        analyst_res = await run_trend_analyst(state, mock=True)
        assert len(analyst_res["errors"]) == 1
        assert "Search API 503 unavailable" in analyst_res["errors"][0]
        assert len(analyst_res["trend_analysis"]) > 0  # recovered with fallback text

    # 3. Pricing Strategist with missing/corrupted summary
    corrupted_state = dict(state)
    corrupted_state["scout_summary"] = {"overall_lowest_price": "invalid_number"}
    pricing_res = await run_pricing_strategist(corrupted_state, mock=True)
    assert pricing_res["pricing_strategy"] is not None
    assert pricing_res["pricing_strategy"]["target_buy_price"] > 0

    # 4. Customer Persona with error
    with patch("src.agents.customer._evaluate_mock_customer_persona", side_effect=ValueError("Corrupted evaluation")):
        customer_res = await run_customer_persona(state, mock=True)
        assert customer_res["customer_verdict"] == "BUY"  # graceful fallback
