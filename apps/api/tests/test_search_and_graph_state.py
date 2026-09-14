"""Unit tests for search tool and graph state definitions."""

import pytest
from src.graph.state import ResellerState, AgentLogEntry
from src.models.item import ItemDescription
from src.models.orchestrate import OrchestrateRequest, OrchestrateResponse
from src.tools.search import SearchTool, SearchFindings, SearchSnippet


@pytest.mark.asyncio
async def test_search_tool_mock_mode():
    tool = SearchTool()
    findings = await tool.search(query="iPhone 13 128GB", mock=True)

    assert isinstance(findings, SearchFindings)
    assert findings.provider == "mock"
    assert len(findings.results) > 0
    assert findings.demand_velocity in ["Low", "Medium", "High"]
    assert len(findings.trend_signals) > 0
    assert findings.summary is not None


@pytest.mark.asyncio
async def test_search_tool_with_item_description():
    tool = SearchTool()
    item = ItemDescription(
        name="Nike Dunk Low Panda",
        condition="Like New",
        key_features=["Size 42", "Fullset Box"],
        category="Fashion/Sneakers",
    )
    findings = await tool.search(item=item, mock=True)

    assert isinstance(findings, SearchFindings)
    assert "Nike Dunk Low Panda" in findings.query
    assert findings.demand_velocity == "High"
    assert len(findings.results) >= 2


@pytest.mark.asyncio
async def test_search_tool_fallback_when_no_keys():
    # Without API keys, search should gracefully fallback to mock findings
    tool = SearchTool(tavily_api_key=None, serper_api_key=None)
    findings = await tool.search(query="Sony WH-1000XM4")

    assert isinstance(findings, SearchFindings)
    assert findings.provider == "mock"
    assert len(findings.results) > 0


def test_reseller_state_definition():
    state: ResellerState = {
        "user_input": "iPhone 13 128GB Mulus",
        "item_description": "iPhone 13 128GB",
        "capital_cost": 7500000.0,
        "market_prices": [{"title": "iPhone 13", "price": 8500000.0, "platform": "Tokopedia"}],
        "scout_summary": {"overall_median_price": 8500000.0},
        "trend_analysis": "High demand, strong liquidity",
        "pricing_strategy": {"fast_sale": 8000000.0, "patient_sale": 8500000.0},
        "final_strategy": "List on Tokopedia and Facebook Marketplace",
        "customer_verdict": "BUY",
        "errors": [],
        "agent_logs": [{"agent": "scout", "status": "completed", "message": "Scraped 10 listings"}],
    }

    assert state["user_input"] == "iPhone 13 128GB Mulus"
    assert state["customer_verdict"] == "BUY"
    assert len(state["agent_logs"]) == 1


def test_orchestrate_request_validation():
    req = OrchestrateRequest(user_input="MacBook Pro M1 2020", capital_cost=10000000.0, mock=True)
    assert req.user_input == "MacBook Pro M1 2020"
    assert req.capital_cost == 10000000.0
    assert req.mock is True

    # Empty inputs should raise validation error
    with pytest.raises(ValueError):
        OrchestrateRequest()


def test_orchestrate_response_model():
    res = OrchestrateResponse(
        status="success",
        user_input="iPhone 13",
        item_description="iPhone 13 128GB",
        capital_cost=7000000.0,
        final_strategy="Test strategy",
        customer_verdict="BUY",
        errors=[],
        agent_logs=[{"agent": "scout", "status": "completed", "message": "Done"}],
    )
    assert res.customer_verdict == "BUY"
    assert len(res.agent_logs) == 1
    assert res.agent_logs[0].agent == "scout"
