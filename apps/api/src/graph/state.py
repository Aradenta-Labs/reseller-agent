"""State schema definitions for LangGraph multi-agent reseller swarm."""

import operator
from typing import Annotated, Any, Dict, List, Optional, Union
from typing_extensions import TypedDict


class AgentLogEntry(TypedDict, total=False):
    """Execution log entry for an individual agent in the swarm."""

    agent: str
    status: str  # 'running', 'completed', 'failed', 'skipped'
    message: str
    timestamp: Optional[str]
    metadata: Optional[Dict[str, Any]]


def merge_dicts(left: Optional[Dict[str, Any]], right: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Custom reducer for dict state updates."""
    merged = dict(left or {})
    if right:
        merged.update(right)
    return merged


class ResellerState(TypedDict, total=False):
    """Central state object flowing through all nodes in the Reseller Agent swarm.

    Attributes:
        user_input: Raw initial prompt or query from user.
        item_description: Structured or summarized item description (ItemDescription dict or string).
        capital_cost: Optional buying/acquisition capital cost specified by user.
        market_prices: List of scraped/found market listings (Populated by Agent 1: Market Scout).
        scout_summary: Structured market scout summary (lowest, highest, median, platform stats).
        trend_analysis: Market trend, hype velocity, and seasonal demand analysis (Populated by Agent 2: Trend Analyst).
        pricing_strategy: Strategic pricing tiers, margin calculation, platform fee breakdowns (Populated by Agent 3: Pricing Strategist).
        final_strategy: Synthesized master action plan, photography tips, listing recommendations (Populated by Agent 4: Chief Strategist).
        customer_verdict: Buyer persona verdict ('BUY' | 'PASS') and critical objection review (Populated by Agent 5: Customer Persona).
        errors: List of error messages or fallback warnings accumulated during execution.
        agent_logs: Step-by-step agent execution logs for real-time progress and debugging.
    """

    user_input: str
    item_description: Union[str, Dict[str, Any]]
    capital_cost: Optional[float]
    market_prices: List[Dict[str, Any]]
    scout_summary: Optional[Dict[str, Any]]
    trend_analysis: str
    pricing_strategy: Dict[str, Any]
    final_strategy: str
    customer_verdict: str
    errors: Annotated[List[str], operator.add]
    agent_logs: Annotated[List[Dict[str, Any]], operator.add]
