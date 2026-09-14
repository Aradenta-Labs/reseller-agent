"""Agents module providing individual specialized node execution functions for the Reseller Agent swarm.

Exports:
- Market Scout Node: `market_scout_node` / `run_market_scout`
- Trend Analyst Node: `trend_analyst_node` / `run_trend_analyst`
- Pricing Strategist Node: `pricing_strategist_node` / `run_pricing_strategist`
- Chief Strategist Node: `chief_strategist_node` / `run_chief_strategist`
- Customer Persona Node: `customer_persona_node` / `run_customer_persona`
"""

from src.agents.analyst import run_trend_analyst, trend_analyst_node
from src.agents.customer import customer_persona_node, run_customer_persona
from src.agents.scout import market_scout_node, run_market_scout
from src.agents.strategist import (
    chief_strategist_node,
    pricing_strategist_node,
    run_chief_strategist,
    run_pricing_strategist,
)

__all__ = [
    "market_scout_node",
    "run_market_scout",
    "trend_analyst_node",
    "run_trend_analyst",
    "pricing_strategist_node",
    "run_pricing_strategist",
    "chief_strategist_node",
    "run_chief_strategist",
    "customer_persona_node",
    "run_customer_persona",
]
