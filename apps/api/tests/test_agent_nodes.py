"""Comprehensive unit and integration tests for all 5 specialized agent nodes.

Tests:
1. Agent 1: Market Scout Node (`run_market_scout`, `market_scout_node`)
2. Agent 2: Trend Analyst Node (`run_trend_analyst`, `trend_analyst_node`)
3. Agent 3: Pricing Strategist Node (`run_pricing_strategist`, `pricing_strategist_node`)
4. Agent 4: Chief Strategist Node (`run_chief_strategist`, `chief_strategist_node`)
5. Agent 5: Customer Persona Node (`run_customer_persona`, `customer_persona_node`)
"""

import pytest
from src.agents import (
    chief_strategist_node,
    customer_persona_node,
    market_scout_node,
    pricing_strategist_node,
    run_chief_strategist,
    run_customer_persona,
    run_market_scout,
    run_pricing_strategist,
    run_trend_analyst,
    trend_analyst_node,
)
from src.graph.state import ResellerState
from src.models.auth import BYOKCredentials
from src.models.item import ItemDescription


@pytest.fixture
def base_state() -> ResellerState:
    """Fixture providing a clean initialized ResellerState."""
    return {
        "user_input": "iPhone 13 Pro 128GB Mulus Bekas Garansi Resmi iBox",
        "item_description": ItemDescription(
            name="Apple iPhone 13 Pro 128GB",
            condition="Used - Good",
            estimated_retail_price=699.0,
            key_features=["128GB", "Sierra Blue", "Battery Health 87%", "iBox"],
            summary="iPhone 13 Pro in good working condition.",
            category="Electronics/Mobiles",
        ),
        "capital_cost": 8_500_000.0,
        "market_prices": [],
        "scout_summary": None,
        "trend_analysis": "",
        "pricing_strategy": {},
        "final_strategy": "",
        "customer_verdict": "",
        "errors": [],
        "agent_logs": [],
    }


# ============================================================================
# AGENT 1: MARKET SCOUT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_run_market_scout_async(base_state):
    res = await run_market_scout(base_state, mock=True)

    assert "market_prices" in res
    assert len(res["market_prices"]) > 0
    assert "scout_summary" in res
    assert res["scout_summary"]["overall_median_price"] > 0
    assert len(res["agent_logs"]) == 1
    assert res["agent_logs"][0]["agent"] == "scout"
    assert res["agent_logs"][0]["status"] == "completed"


def test_market_scout_sync(base_state):
    res = market_scout_node(base_state, mock=True)
    assert len(res["market_prices"]) > 0
    assert res["scout_summary"] is not None


@pytest.mark.asyncio
async def test_market_scout_with_string_item_and_fallback(base_state):
    base_state["item_description"] = "Sony WH-1000XM4 Headphone"
    res = await run_market_scout(base_state, mock=True)
    assert len(res["market_prices"]) > 0
    assert "Sony" in res["scout_summary"]["search_query_used"]


# ============================================================================
# AGENT 2: TREND ANALYST TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_run_trend_analyst_async(base_state):
    res = await run_trend_analyst(base_state, mock=True)

    assert "trend_analysis" in res
    assert len(res["trend_analysis"]) > 0
    assert "Demand Velocity" in res["trend_analysis"]
    assert len(res["agent_logs"]) == 1
    assert res["agent_logs"][0]["agent"] == "analyst"


def test_trend_analyst_sync(base_state):
    res = trend_analyst_node(base_state, mock=True)
    assert "trend_analysis" in res
    assert len(res["trend_analysis"]) > 0


# ============================================================================
# AGENT 3: PRICING STRATEGIST TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_run_pricing_strategist_financial_rules(base_state):
    # Populate mock scout summary
    base_state["scout_summary"] = {
        "overall_lowest_price": 10_000_000.0,
        "overall_highest_price": 13_000_000.0,
        "overall_average_price": 11_500_000.0,
        "overall_median_price": 11_500_000.0,
        "total_listings_found": 8,
        "best_platform_recommendation": "Tokopedia",
    }
    base_state["capital_cost"] = 8_000_000.0

    res = await run_pricing_strategist(base_state, mock=True)

    assert "pricing_strategy" in res
    strategy = res["pricing_strategy"]
    tiers = strategy["tiers"]

    assert "fast_sale" in tiers
    assert "patient_sale" in tiers
    assert "direct_sale" in tiers

    # 20% platform fee check for online tiers
    assert tiers["fast_sale"]["platform_fee_rate"] == 0.20
    assert tiers["patient_sale"]["platform_fee_rate"] == 0.20
    assert tiers["direct_sale"]["platform_fee_rate"] == 0.0

    # Max recommended buy price guarantees >=15% net margin
    assert strategy["target_buy_price"] > 0
    assert strategy["max_buy_price"] > 0

    # Capital cost calculations
    assert tiers["fast_sale"]["capital_cost"] == 8_000_000.0
    assert "projected_net_profit" in tiers["fast_sale"]
    assert "projected_roi_pct" in tiers["fast_sale"]

    # Check agent log
    assert len(res["agent_logs"]) == 1
    assert res["agent_logs"][0]["agent"] == "pricing"


def test_pricing_strategist_sync(base_state):
    base_state["scout_summary"] = {"overall_median_price": 5_000_000.0}
    res = pricing_strategist_node(base_state, mock=True)
    assert res["pricing_strategy"]["target_buy_price"] > 0


# ============================================================================
# AGENT 4: CHIEF STRATEGIST TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_run_chief_strategist_async(base_state):
    base_state["scout_summary"] = {
        "overall_lowest_price": 10_000_000.0,
        "overall_highest_price": 13_000_000.0,
        "overall_median_price": 11_500_000.0,
        "best_platform_recommendation": "Tokopedia",
    }
    base_state["trend_analysis"] = "High demand, fast liquidity in Indonesia."
    base_state["pricing_strategy"] = {
        "target_buy_price": 8_000_000.0,
        "tiers": {
            "fast_sale": {"listing_price": 9_800_000.0, "net_payout": 7_840_000.0},
            "patient_sale": {"listing_price": 11_500_000.0, "net_payout": 9_200_000.0},
            "direct_sale": {"listing_price": 10_900_000.0, "net_payout": 10_900_000.0},
        },
    }

    res = await run_chief_strategist(base_state, mock=True)

    assert "final_strategy" in res
    assert len(res["final_strategy"]) > 0
    assert "Master Resale Plan" in res["final_strategy"]
    assert "Pricing Schedule" in res["final_strategy"]
    assert "Photography" in res["final_strategy"]
    assert len(res["agent_logs"]) == 1
    assert res["agent_logs"][0]["agent"] == "chief"


def test_chief_strategist_sync(base_state):
    res = chief_strategist_node(base_state, mock=True)
    assert "final_strategy" in res
    assert len(res["final_strategy"]) > 0


# ============================================================================
# AGENT 5: CUSTOMER PERSONA TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_run_customer_persona_async_buy(base_state):
    base_state["scout_summary"] = {"overall_median_price": 11_500_000.0}
    base_state["pricing_strategy"] = {
        "tiers": {
            "fast_sale": {"listing_price": 10_000_000.0},
            "patient_sale": {"listing_price": 11_500_000.0},
        }
    }

    res = await run_customer_persona(base_state, mock=True)

    assert "customer_verdict" in res
    assert res["customer_verdict"] == "BUY"
    assert len(res["agent_logs"]) == 1
    assert res["agent_logs"][0]["agent"] == "customer"
    assert res["agent_logs"][0]["metadata"]["verdict"] == "BUY"


@pytest.mark.asyncio
async def test_run_customer_persona_pass_when_overpriced(base_state):
    base_state["scout_summary"] = {"overall_median_price": 5_000_000.0}
    base_state["pricing_strategy"] = {
        "tiers": {
            "fast_sale": {"listing_price": 7_500_000.0},  # 50% above market median
            "patient_sale": {"listing_price": 8_500_000.0},
        }
    }

    res = await run_customer_persona(base_state, mock=True)
    assert res["customer_verdict"] == "PASS"


def test_customer_persona_sync(base_state):
    res = customer_persona_node(base_state, mock=True)
    assert res["customer_verdict"] in ["BUY", "PASS"]


# ============================================================================
# FULL SEQUENTIAL AGENT PIPELINE RUN
# ============================================================================

@pytest.mark.asyncio
async def test_sequential_5_agent_pipeline_execution(base_state):
    """Test sequential flow of all 5 agent nodes passing updated state down the chain."""
    state = dict(base_state)

    # 1. Market Scout
    scout_out = await run_market_scout(state, mock=True)
    state.update(scout_out)
    assert len(state["market_prices"]) > 0
    assert state["scout_summary"] is not None

    # 2. Trend Analyst
    analyst_out = await run_trend_analyst(state, mock=True)
    state.update(analyst_out)
    assert len(state["trend_analysis"]) > 0

    # 3. Pricing Strategist
    pricing_out = await run_pricing_strategist(state, mock=True)
    state.update(pricing_out)
    assert state["pricing_strategy"]["target_buy_price"] > 0

    # 4. Chief Strategist
    chief_out = await run_chief_strategist(state, mock=True)
    state.update(chief_out)
    assert len(state["final_strategy"]) > 0

    # 5. Customer Persona
    customer_out = await run_customer_persona(state, mock=True)
    state.update(customer_out)
    assert state["customer_verdict"] in ["BUY", "PASS"]

    # All 5 agent logs present
    assert len(state["agent_logs"]) == 5
    agent_names = [log["agent"] for log in state["agent_logs"]]
    assert agent_names == ["scout", "analyst", "pricing", "chief", "customer"]
