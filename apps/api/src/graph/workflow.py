"""LangGraph workflow definition for the Reseller AI multi-agent swarm.

Orchestration architecture:
- Entry point (START): Dispatches parallel execution to `market_scout` and `trend_analyst`.
- Fan-in: `market_scout` and `trend_analyst` both feed into `pricing_strategist`.
- Sequential pipeline: `pricing_strategist` -> `chief_strategist` -> `customer_persona` -> END.
"""

import logging
from typing import Any, Dict, List, Optional

from langgraph.graph import END, START, StateGraph

from src.agents.analyst import run_trend_analyst
from src.agents.customer import run_customer_persona
from src.agents.scout import run_market_scout
from src.agents.strategist import run_chief_strategist, run_pricing_strategist
from src.graph.state import ResellerState
from src.models.auth import BYOKCredentials

logger = logging.getLogger("reseller_api.graph.workflow")


def create_reseller_graph(
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
    platforms: Optional[List[str]] = None,
    **kwargs: Any,
):
    """Construct and compile the 5-agent LangGraph workflow.

    Nodes:
      - `market_scout`: Scrapes and aggregates market pricing (Tokopedia, Shopee, FB Marketplace).
      - `trend_analyst`: Analyzes search trends, hype velocity, and seasonality.
      - `pricing_strategist`: Computes 3 price tiers, margins, 20% platform fee, ROI.
      - `chief_strategist`: Synthesizes final master action plan and listing advice.
      - `customer_persona`: Evaluates value skeptically and produces BUY/PASS verdict.

    Flow:
      START -> [market_scout, trend_analyst] -> pricing_strategist -> chief_strategist -> customer_persona -> END
    """
    workflow = StateGraph(ResellerState)

    # Wrap agent runners into async node callables capturing closures/kwargs
    async def market_scout_node(state: ResellerState) -> Dict[str, Any]:
        return await run_market_scout(
            state,
            credentials=credentials,
            mock=mock,
            platforms=platforms,
        )

    async def trend_analyst_node(state: ResellerState) -> Dict[str, Any]:
        return await run_trend_analyst(
            state,
            credentials=credentials,
            mock=mock,
            tavily_api_key=kwargs.get("tavily_api_key"),
            serper_api_key=kwargs.get("serper_api_key"),
        )

    async def pricing_strategist_node(state: ResellerState) -> Dict[str, Any]:
        return await run_pricing_strategist(
            state,
            credentials=credentials,
            mock=mock,
        )

    async def chief_strategist_node(state: ResellerState) -> Dict[str, Any]:
        return await run_chief_strategist(
            state,
            credentials=credentials,
            mock=mock,
        )

    async def customer_persona_node(state: ResellerState) -> Dict[str, Any]:
        return await run_customer_persona(
            state,
            credentials=credentials,
            mock=mock,
        )

    # 1. Add nodes
    workflow.add_node("market_scout", market_scout_node)
    workflow.add_node("trend_analyst", trend_analyst_node)
    workflow.add_node("pricing_strategist", pricing_strategist_node)
    workflow.add_node("chief_strategist", chief_strategist_node)
    workflow.add_node("customer_persona", customer_persona_node)

    # 2. Add edges
    # Parallel start: START -> market_scout AND START -> trend_analyst
    workflow.add_edge(START, "market_scout")
    workflow.add_edge(START, "trend_analyst")

    # Fan-in: both market_scout and trend_analyst connect to pricing_strategist
    workflow.add_edge("market_scout", "pricing_strategist")
    workflow.add_edge("trend_analyst", "pricing_strategist")

    # Sequential chain: pricing_strategist -> chief_strategist -> customer_persona -> END
    workflow.add_edge("pricing_strategist", "chief_strategist")
    workflow.add_edge("chief_strategist", "customer_persona")
    workflow.add_edge("customer_persona", END)

    return workflow.compile()


async def run_reseller_orchestration(
    initial_state: Dict[str, Any],
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
    platforms: Optional[List[str]] = None,
    **kwargs: Any,
) -> ResellerState:
    """Instantiate and execute the full LangGraph swarm workflow.

    Args:
        initial_state: Initial state dictionary for ResellerState.
        credentials: User BYOK credentials.
        mock: Force mock/simulated tools.
        platforms: Target scraping marketplaces.
        kwargs: Optional extra arguments.

    Returns:
        Final accumulated ResellerState dictionary.
    """
    app = create_reseller_graph(
        credentials=credentials,
        mock=mock,
        platforms=platforms,
        **kwargs,
    )

    # Clean / ensure required initial keys
    state_payload: ResellerState = {
        "user_input": initial_state.get("user_input", ""),
        "item_description": initial_state.get("item_description", {}),
        "capital_cost": initial_state.get("capital_cost"),
        "market_prices": initial_state.get("market_prices", []),
        "scout_summary": initial_state.get("scout_summary"),
        "trend_analysis": initial_state.get("trend_analysis", ""),
        "pricing_strategy": initial_state.get("pricing_strategy", {}),
        "final_strategy": initial_state.get("final_strategy", ""),
        "customer_verdict": initial_state.get("customer_verdict", "PASS"),
        "errors": initial_state.get("errors", []),
        "agent_logs": initial_state.get("agent_logs", []),
    }

    final_state = await app.ainvoke(state_payload)
    return final_state
