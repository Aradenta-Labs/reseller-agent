"""LangGraph workflow definition for the Reseller AI multi-agent swarm.

Orchestration architecture:
- Entry point (START): Dispatches parallel execution to `market_scout` and `trend_analyst`.
- Fan-in: `market_scout` and `trend_analyst` both feed into `pricing_strategist`.
- Sequential pipeline: `pricing_strategist` -> `chief_strategist` -> `customer_persona` -> END.
"""

import datetime
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

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


NODE_METADATA: Dict[str, Dict[str, str]] = {
    "market_scout": {
        "display_name": "Market Scout",
        "start_status": "Searching Tokopedia, Shopee, and FB Marketplace...",
    },
    "trend_analyst": {
        "display_name": "Trend Analyst",
        "start_status": "Analyzing search trends, hype velocity, and seasonality...",
    },
    "pricing_strategist": {
        "display_name": "Pricing Strategist",
        "start_status": "Calculating 3 price tiers, margins, and platform fees...",
    },
    "chief_strategist": {
        "display_name": "Chief Strategist",
        "start_status": "Synthesizing master action plan and listing playbook...",
    },
    "customer_persona": {
        "display_name": "Customer Persona",
        "start_status": "Evaluating buyer objections and determining BUY/PASS verdict...",
    },
}


async def stream_reseller_orchestration(
    initial_state: Dict[str, Any],
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
    platforms: Optional[List[str]] = None,
    **kwargs: Any,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute the LangGraph swarm workflow and stream real-time events at node boundaries.

    Yields:
        - `AGENT_START`: emitted when an agent node starts executing.
        - `AGENT_COMPLETE`: emitted when an agent node finishes with its output data.
        - `FINAL_RESULT`: emitted upon successful completion of the full workflow with final state.
        - `ERROR`: emitted if an unhandled exception occurs during execution.
    """
    try:
        app = create_reseller_graph(
            credentials=credentials,
            mock=mock,
            platforms=platforms,
            **kwargs,
        )

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

        tracked_nodes = set(NODE_METADATA.keys())
        accumulated_state: Dict[str, Any] = dict(state_payload)

        async for event in app.astream_events(state_payload, version="v2"):
            node_name = event.get("name")
            event_type = event.get("event")

            if node_name in tracked_nodes:
                meta = NODE_METADATA[node_name]
                display_name = meta["display_name"]
                now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

                if event_type == "on_chain_start":
                    yield {
                        "type": "AGENT_START",
                        "agent": node_name,
                        "agent_name": display_name,
                        "status": meta["start_status"],
                        "timestamp": now_iso,
                    }
                elif event_type == "on_chain_end":
                    node_output = event.get("data", {}).get("output")
                    if isinstance(node_output, dict):
                        # Merge into accumulated state for the final result
                        for k, v in node_output.items():
                            if k == "agent_logs" or k == "errors":
                                existing_list = accumulated_state.get(k, [])
                                accumulated_state[k] = (existing_list or []) + (v or [])
                            else:
                                accumulated_state[k] = v

                    # Determine completion summary message
                    result_summary = ""
                    if node_name == "market_scout":
                        count = len(accumulated_state.get("market_prices", []))
                        result_summary = f"Gathered {count} marketplace listings."
                    elif node_name == "trend_analyst":
                        result_summary = "Market demand and hype velocity analyzed."
                    elif node_name == "pricing_strategist":
                        pricing = accumulated_state.get("pricing_strategy", {})
                        max_buy = pricing.get("max_buy_price", pricing.get("target_buy_price"))
                        result_summary = f"Formulated 3 price tiers (Max buy: Rp {max_buy:,.0f})." if max_buy else "Formulated 3 price tiers."
                    elif node_name == "chief_strategist":
                        result_summary = "Synthesized master resale playbook."
                    elif node_name == "customer_persona":
                        verdict = accumulated_state.get("customer_verdict", "PASS")
                        result_summary = f"Evaluated listing value (Verdict: {verdict})."

                    yield {
                        "type": "AGENT_COMPLETE",
                        "agent": node_name,
                        "agent_name": display_name,
                        "result": result_summary,
                        "data": node_output if isinstance(node_output, dict) else {},
                        "timestamp": now_iso,
                    }

        # Workflow finished, emit FINAL_RESULT
        final_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        yield {
            "type": "FINAL_RESULT",
            "status": "success",
            "verdict": accumulated_state.get("customer_verdict", "PASS"),
            "customer_verdict": accumulated_state.get("customer_verdict", "PASS"),
            "final_strategy": accumulated_state.get("final_strategy", ""),
            "pricing_strategy": accumulated_state.get("pricing_strategy", {}),
            "market_prices": accumulated_state.get("market_prices", []),
            "scout_summary": accumulated_state.get("scout_summary"),
            "trend_analysis": accumulated_state.get("trend_analysis", ""),
            "user_input": accumulated_state.get("user_input", ""),
            "item_description": accumulated_state.get("item_description", {}),
            "capital_cost": accumulated_state.get("capital_cost"),
            "agent_logs": accumulated_state.get("agent_logs", []),
            "errors": accumulated_state.get("errors", []),
            "timestamp": final_iso,
        }

    except Exception as e:
        logger.error("Error during streaming reseller orchestration: %s", str(e), exc_info=True)
        yield {
            "type": "ERROR",
            "error": str(e),
            "message": f"Swarm orchestration failed: {str(e)}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

