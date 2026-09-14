"""Agent 1: Market Scout Node.

Responsibilities:
- Inspects item_description (or raw user_input) from ResellerState.
- Invokes MarketScoutService to formulate query and scrape/aggregate listings from Tokopedia, Shopee, and FB Marketplace.
- Populates `market_prices` (list of cleaned listing dictionaries) and `scout_summary` (min, max, avg, median, count, best platform).
- Appends step log entry to `agent_logs`.
- Supports both async and sync execution with robust mock and error fallbacks.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Union

from src.graph.state import AgentLogEntry, ResellerState
from src.models.auth import BYOKCredentials
from src.models.item import ItemDescription
from src.services.scout import MarketScoutService

logger = logging.getLogger("reseller_api.agents.scout")


async def run_market_scout(
    state: ResellerState,
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
    platforms: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Execute Market Scout Agent node asynchronously.

    Args:
        state: Current ResellerState.
        credentials: Optional BYOK credentials for LLM query formulation.
        mock: Force simulated/mock scraping.
        platforms: Optional target platforms list.

    Returns:
        State update dictionary containing:
            - market_prices: List[Dict[str, Any]]
            - scout_summary: Dict[str, Any]
            - agent_logs: List[AgentLogEntry]
            - errors (if any): List[str]
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    agent_logs = list(state.get("agent_logs") or [])
    errors = list(state.get("errors") or [])

    item_desc = state.get("item_description")
    user_input = state.get("user_input")

    # Resolve target item representation
    target_item: Optional[ItemDescription] = None
    raw_text: Optional[str] = None

    if isinstance(item_desc, ItemDescription):
        target_item = item_desc
    elif isinstance(item_desc, dict):
        try:
            target_item = ItemDescription(**item_desc)
        except Exception:
            raw_text = str(item_desc.get("name") or item_desc.get("summary") or item_desc)
    elif isinstance(item_desc, str) and item_desc.strip():
        raw_text = item_desc.strip()
    elif user_input and user_input.strip():
        raw_text = user_input.strip()
    else:
        raw_text = "Trending Resale Item"

    service = MarketScoutService(credentials=credentials)

    try:
        report = await service.run_scout(
            item=target_item,
            raw_text=raw_text,
            mock=mock,
            platforms=platforms,
        )

        # Flatten listings for state
        all_listings: List[Dict[str, Any]] = []
        for platform_name, res in report.platform_results.items():
            for listing in res.top_listings:
                all_listings.append({
                    "title": listing.title,
                    "price": listing.price,
                    "platform": listing.platform or platform_name,
                    "condition": listing.condition,
                    "location": listing.location,
                    "url": listing.url,
                    "raw_price": listing.raw_price,
                })

        scout_summary = {
            "search_query_used": report.search_query_used,
            "overall_lowest_price": report.overall_lowest_price,
            "overall_highest_price": report.overall_highest_price,
            "overall_average_price": report.overall_average_price,
            "overall_median_price": report.overall_median_price,
            "total_listings_found": report.total_listings_found,
            "best_platform_recommendation": report.best_platform_recommendation,
            "summary_insights": report.summary_insights,
            "recommended_price_range": report.recommended_price_range,
        }

        log_entry: AgentLogEntry = {
            "agent": "scout",
            "status": "completed",
            "message": f"Market Scout gathered {len(all_listings)} listings across marketplaces for query '{report.search_query_used}'.",
            "timestamp": timestamp,
            "metadata": {
                "search_query": report.search_query_used,
                "total_found": report.total_listings_found,
                "median_price": report.overall_median_price,
                "best_platform": report.best_platform_recommendation,
            },
        }
        agent_logs.append(log_entry)

        return {
            "market_prices": all_listings,
            "scout_summary": scout_summary,
            "agent_logs": agent_logs,
            "errors": errors,
        }

    except Exception as e:
        logger.error("Market Scout node encountered an error: %s", str(e), exc_info=True)
        err_msg = f"Market Scout error: {str(e)}"
        errors.append(err_msg)

        # Graceful fallback data
        fallback_results = service.generate_mock_results(
            raw_text or (target_item.name if target_item else "Product"),
            platforms=platforms,
        )
        fallback_report = service.aggregate_market_report(
            item=target_item or raw_text or "Product",
            search_query_used=raw_text or (target_item.name if target_item else "Product"),
            platform_results=fallback_results,
        )

        all_listings = []
        for p_name, res in fallback_report.platform_results.items():
            for listing in res.top_listings:
                all_listings.append({
                    "title": listing.title,
                    "price": listing.price,
                    "platform": listing.platform or p_name,
                    "condition": listing.condition,
                    "location": listing.location,
                    "url": listing.url,
                    "raw_price": listing.raw_price,
                })

        scout_summary = {
            "search_query_used": fallback_report.search_query_used,
            "overall_lowest_price": fallback_report.overall_lowest_price,
            "overall_highest_price": fallback_report.overall_highest_price,
            "overall_average_price": fallback_report.overall_average_price,
            "overall_median_price": fallback_report.overall_median_price,
            "total_listings_found": fallback_report.total_listings_found,
            "best_platform_recommendation": fallback_report.best_platform_recommendation,
            "summary_insights": fallback_report.summary_insights,
            "recommended_price_range": fallback_report.recommended_price_range,
        }

        log_entry: AgentLogEntry = {
            "agent": "scout",
            "status": "completed",
            "message": f"Market Scout recovered with fallback data ({len(all_listings)} listings).",
            "timestamp": timestamp,
            "metadata": {"fallback": True, "error": str(e)},
        }
        agent_logs.append(log_entry)

        return {
            "market_prices": all_listings,
            "scout_summary": scout_summary,
            "agent_logs": agent_logs,
            "errors": errors,
        }


def market_scout_node(
    state: ResellerState,
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
    platforms: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Synchronous wrapper for market scout node."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(
                run_market_scout(state, credentials=credentials, mock=mock, platforms=platforms)
            )
        return asyncio.run(
            run_market_scout(state, credentials=credentials, mock=mock, platforms=platforms)
        )
    except RuntimeError:
        return asyncio.run(
            run_market_scout(state, credentials=credentials, mock=mock, platforms=platforms)
        )
