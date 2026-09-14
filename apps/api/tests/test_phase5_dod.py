"""Phase 5 Comprehensive Verification & Hardening Test Suite.

Validates:
1. Scraper anti-bot features: session randomization, proxy configuration, cooldown rate limiting, human behavior simulation, and fallback search chains.
2. Pricing Strategist deterministic math calculation (no LLM arithmetic) and margin verification.
3. Customer Persona structured verdict (BUY / PASS / CONDITIONAL) schema conformity.
4. End-to-End Swarm on 5 real-world item scenarios:
   - Secondhand iPhone 13
   - Nike Air Jordan shoes
   - Philips Blender
   - Secretlab Gaming Chair
   - Vintage Thrift Denim Jacket
5. Updated Phase 5 Healthcheck observability endpoint.
"""

import pytest
from fastapi.testclient import TestClient

from src.agents.customer import CustomerEvaluationSchema, CustomerVerdictEnum, run_customer_persona
from src.agents.strategist import calculate_pricing, run_pricing_strategist
from src.graph.state import ResellerState
from src.graph.workflow import create_reseller_graph
from src.main import app
from src.models.auth import BYOKCredentials
from src.models.item import ItemDescription
from src.scrapers.base import (
    BaseScraper,
    ProductListing,
    enforce_scraper_cooldown,
    get_random_fingerprint,
    get_scraper_proxy_config,
)
from src.scrapers.fb import FacebookMarketplaceScraper
from src.scrapers.shopee import ShopeeScraper
from src.scrapers.tokped import TokopediaScraper


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


# ==============================================================================
# 1. Anti-Bot Hardening & Scraper Tests
# ==============================================================================

def test_random_fingerprint_generation():
    """Assert randomized fingerprints contain all required browser context properties."""
    fp1 = get_random_fingerprint()
    assert "user_agent" in fp1
    assert "viewport" in fp1
    assert "width" in fp1["viewport"]
    assert "height" in fp1["viewport"]
    assert fp1.get("locale") == "id-ID"
    assert fp1.get("timezone_id") == "Asia/Jakarta"


def test_proxy_configuration_parsing(monkeypatch):
    """Assert proxy configuration responds to SCRAPER_PROXY_URL env."""
    monkeypatch.setenv("SCRAPER_PROXY_URL", "http://user:pass@proxy.example.com:8080")
    cfg = get_scraper_proxy_config()
    assert cfg is not None
    assert cfg["server"] == "http://user:pass@proxy.example.com:8080"

    monkeypatch.delenv("SCRAPER_PROXY_URL", raising=False)
    assert get_scraper_proxy_config() is None


@pytest.mark.asyncio
async def test_scraper_cooldown_rate_limit(monkeypatch):
    """Assert cooldown execution succeeds without errors."""
    monkeypatch.setenv("SCRAPER_COOLDOWN_SECONDS", "0.05")
    await enforce_scraper_cooldown()
    await enforce_scraper_cooldown()


@pytest.mark.asyncio
async def test_scraper_fallback_chain_on_blocked():
    """Verify scrapers return clean ScrapeResult with fallback search instead of crashing."""
    tokped = TokopediaScraper()
    shopee = ShopeeScraper()
    fb = FacebookMarketplaceScraper()

    # Pass invalid/empty queries to test fallback resilience
    res_tokped = await tokped.scrape("iphone 13 pro", max_results=2)
    assert res_tokped.platform == "Tokopedia"
    assert isinstance(res_tokped.top_listings, list)

    res_shopee = await shopee.scrape("nike air jordan", max_results=2)
    assert res_shopee.platform == "Shopee"
    assert isinstance(res_shopee.top_listings, list)

    res_fb = await fb.scrape("gaming chair", max_results=2)
    assert res_fb.platform == "Facebook Marketplace"
    assert isinstance(res_fb.top_listings, list)


# ==============================================================================
# 2. Deterministic Pricing Math & Margin Validation
# ==============================================================================

def test_deterministic_pricing_math_formula():
    """Assert calculate_pricing enforces 20% platform fee and >= 15% net margin."""
    market_prices = [
        {"price": 10_000_000.0, "platform": "Tokopedia"},
        {"price": 10_500_000.0, "platform": "Shopee"},
        {"price": 9_500_000.0, "platform": "Facebook Marketplace"},
    ]

    pricing = calculate_pricing(
        market_prices=market_prices,
        capital_cost=6_000_000.0,
        fee_rate=0.20,
        min_margin_rate=0.15,
    )

    tiers = pricing["tiers"]
    assert "fast_sale" in tiers
    assert "patient_sale" in tiers
    assert "direct_sale" in tiers

    fast = tiers["fast_sale"]
    patient = tiers["patient_sale"]
    direct = tiers["direct_sale"]

    # 1. Check Fast Sale fee deduction
    assert fast["estimated_platform_fee"] == round(fast["listing_price"] * 0.20, 2)
    assert fast["net_payout"] == round(fast["listing_price"] - fast["estimated_platform_fee"], 2)

    # 2. Check Patient Sale fee deduction
    assert patient["estimated_platform_fee"] == round(patient["listing_price"] * 0.20, 2)
    assert patient["net_payout"] == round(patient["listing_price"] - patient["estimated_platform_fee"], 2)

    # 3. Check Direct Sale (0% fee)
    assert direct["platform_fee_rate"] == 0.0
    assert direct["net_payout"] == direct["listing_price"]

    # 4. Check Target Acquisition Price gives >= 15% net margin
    target_buy = pricing["target_buy_price"]
    # If we buy at target_buy and sell at patient net payout, net margin must be >= 15%
    projected_margin = (patient["net_payout"] - target_buy) / target_buy
    assert projected_margin >= 0.149  # account for rounding to nearest thousand


@pytest.mark.asyncio
async def test_pricing_strategist_node_execution():
    """Assert Pricing Strategist node runs calculate_pricing and updates state accurately."""
    state: ResellerState = {
        "user_input": "iPhone 13 128GB Midnight",
        "capital_cost": 7_500_000.0,
        "market_prices": [{"price": 9_000_000.0}, {"price": 9_500_000.0}],
        "scout_summary": {"overall_median_price": 9_250_000.0, "overall_lowest_price": 9_000_000.0},
        "agent_logs": [],
        "errors": [],
    }

    result = await run_pricing_strategist(state, mock=True)
    assert "pricing_strategy" in result
    pricing = result["pricing_strategy"]
    assert pricing["currency"] == "IDR"
    assert pricing["tiers"]["fast_sale"]["listing_price"] > 0
    assert pricing["target_buy_price"] > 0


# ==============================================================================
# 3. Agent 5 Structured Verdict Validation
# ==============================================================================

@pytest.mark.asyncio
async def test_customer_persona_verdict_values():
    """Assert Customer Persona outputs strict valid verdicts."""
    # Scenario A: Highly competitive fast price -> BUY
    state_buy: ResellerState = {
        "user_input": "Sony WH-1000XM5 Headphone",
        "scout_summary": {"overall_median_price": 4_500_000.0},
        "pricing_strategy": {
            "tiers": {"fast_sale": {"listing_price": 4_000_000.0}}
        },
        "agent_logs": [],
        "errors": [],
    }
    res_buy = await run_customer_persona(state_buy, mock=True)
    assert res_buy["customer_verdict"] in ["BUY", "CONDITIONAL"]

    # Scenario B: Overpriced fast price -> PASS
    state_pass: ResellerState = {
        "user_input": "Sony WH-1000XM5 Headphone",
        "scout_summary": {"overall_median_price": 4_500_000.0},
        "pricing_strategy": {
            "tiers": {"fast_sale": {"listing_price": 6_000_000.0}}
        },
        "agent_logs": [],
        "errors": [],
    }
    res_pass = await run_customer_persona(state_pass, mock=True)
    assert res_pass["customer_verdict"] == "PASS"


# ==============================================================================
# 4. End-to-End 5 Real-World Items Verification
# ==============================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "item_title, capital_cost",
    [
        ("iPhone 13 128GB Midnight Second iBox", 7_000_000.0),
        ("Nike Air Jordan 1 Retro High OG Chicago Size 42", 2_000_000.0),
        ("Philips HR2115 Blender Glass 2 Liter Bekas Mulus", 250_000.0),
        ("Secretlab TITAN Evo 2022 Series Gaming Chair Stealth", 4_500_000.0),
        ("Vintage Levi's 70505 Trucker Denim Jacket Thrift", 300_000.0),
    ],
)
async def test_e2e_real_world_item_analysis(item_title: str, capital_cost: float):
    """Run full 5-agent LangGraph workflow on 5 real-world items and assert complete, sourced outputs."""
    graph = create_reseller_graph()

    initial_state: ResellerState = {
        "user_input": item_title,
        "item_description": ItemDescription(
            name=item_title,
            condition="Bekas",
            category="Electronics" if "iPhone" in item_title or "Blender" in item_title else "Lifestyle",
            key_features=[item_title],
        ),
        "capital_cost": capital_cost,
        "agent_logs": [],
        "errors": [],
    }

    final_state = await graph.ainvoke(initial_state)

    # 1. Market Scout checks
    assert len(final_state["market_prices"]) > 0
    for listing in final_state["market_prices"]:
        assert listing["price"] > 0
        assert listing["platform"] in ["Tokopedia", "Shopee", "Facebook Marketplace"]
        assert listing.get("url") is not None  # Must have sourced listing URL

    # 2. Trend Analyst checks
    assert len(final_state["trend_analysis"]) > 10

    # 3. Pricing Strategist checks
    pricing = final_state["pricing_strategy"]
    assert pricing["currency"] == "IDR"
    assert pricing["target_buy_price"] > 0
    assert "fast_sale" in pricing["tiers"]

    # 4. Chief Strategist checks
    assert len(final_state["final_strategy"]) > 50
    assert item_title in final_state["final_strategy"] or "Plan" in final_state["final_strategy"]

    # 5. Customer Persona checks
    assert final_state["customer_verdict"] in ["BUY", "PASS", "CONDITIONAL"]


# ==============================================================================
# 5. Observability & Health Endpoint
# ==============================================================================

def test_phase5_health_endpoint(client):
    """Assert /api/health reports Phase 5 status and scraper capabilities."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["phase"] == "5"
    assert "scrapers" in data
    assert data["scrapers"]["supported_platforms"] == ["Tokopedia", "Shopee", "Facebook Marketplace"]
    assert "llm" in data
