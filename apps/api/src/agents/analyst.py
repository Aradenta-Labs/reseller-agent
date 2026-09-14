"""Agent 2: Trend Analyst Node.

Responsibilities:
- Accepts ResellerState.
- Uses SearchTool (Tavily, Serper, or simulated fallback) and/or LLM synthesis via LiteLLM to gauge demand velocity, seasonal hype, and urgency.
- Populates `trend_analysis` (structured insights covering demand velocity, seasonality, hype signals, and buyer preferences).
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
from src.services.llm import DEFAULT_MODELS
from src.tools.search import SearchFindings, SearchTool

logger = logging.getLogger("reseller_api.agents.analyst")


async def run_trend_analyst(
    state: ResellerState,
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
    tavily_api_key: Optional[str] = None,
    serper_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute Trend Analyst Agent node asynchronously.

    Args:
        state: Current ResellerState.
        credentials: Optional BYOK credentials for LLM synthesis.
        mock: Force simulated/mock search & analysis.
        tavily_api_key: Optional override for Tavily search.
        serper_api_key: Optional override for Serper search.

    Returns:
        State update dictionary containing:
            - trend_analysis: str
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

    search_tool = SearchTool(
        tavily_api_key=tavily_api_key,
        serper_api_key=serper_api_key,
    )

    try:
        # Step 1: Query web search / trend data
        findings: SearchFindings = await search_tool.search(
            item=target_item or raw_text,
            mock=mock,
        )

        # Step 2: Synthesize trend insights (via LLM if available, else structured template)
        has_llm = (
            credentials
            and credentials.provider != "mock"
            and credentials.api_key
            and not credentials.api_key.startswith("mock-")
            and credentials.api_key != "test_key"
            and not mock
        )

        trend_text: str = ""

        if has_llm and credentials:
            trend_text = _synthesize_llm_trends(
                findings=findings,
                item=target_item or raw_text or "Product",
                credentials=credentials,
            )

        if not trend_text:
            trend_text = _format_structured_trend_analysis(findings, target_item or raw_text)

        log_entry: AgentLogEntry = {
            "agent": "analyst",
            "status": "completed",
            "message": f"Trend Analyst identified {findings.demand_velocity} demand velocity with {len(findings.trend_signals)} market signals.",
            "timestamp": timestamp,
            "metadata": {
                "velocity": findings.demand_velocity,
                "provider": findings.provider,
                "signals_count": len(findings.trend_signals),
            },
        }
        agent_logs.append(log_entry)

        return {
            "trend_analysis": trend_text,
            "agent_logs": agent_logs,
            "errors": errors,
        }

    except Exception as e:
        logger.error("Trend Analyst node encountered an error: %s", str(e), exc_info=True)
        err_msg = f"Trend Analyst error: {str(e)}"
        errors.append(err_msg)

        fallback_text = (
            "Permintaan pasar: Medium.\n"
            "- Likuiditas pasar relatif stabil dengan persaingan harga wajar.\n"
            "- Produk memiliki basis peminat e-commerce yang konsisten.\n"
            "- Kunci penjualan cepat: foto kondisi fisik transparan dan harga bersaing."
        )

        log_entry: AgentLogEntry = {
            "agent": "analyst",
            "status": "completed",
            "message": "Trend Analyst recovered with fallback analysis.",
            "timestamp": timestamp,
            "metadata": {"fallback": True, "error": str(e)},
        }
        agent_logs.append(log_entry)

        return {
            "trend_analysis": fallback_text,
            "agent_logs": agent_logs,
            "errors": errors,
        }


def _format_structured_trend_analysis(
    findings: SearchFindings,
    item: Union[ItemDescription, str],
) -> str:
    """Format structured trend analysis text when LLM is offline or mock mode is active."""
    signals_formatted = "\n".join([f"- {signal}" for signal in findings.trend_signals])
    item_name = item.name if isinstance(item, ItemDescription) else str(item)

    return (
        f"**Demand Velocity: {findings.demand_velocity}**\n\n"
        f"**Market & Trend Signals for '{item_name}':**\n"
        f"{signals_formatted}\n\n"
        f"**Executive Demand Summary:**\n"
        f"{findings.summary}"
    )


def _synthesize_llm_trends(
    findings: SearchFindings,
    item: Union[ItemDescription, str],
    credentials: BYOKCredentials,
) -> str:
    """Synthesize web search findings into actionable trend analysis using LiteLLM."""
    try:
        import litellm

        system_prompt = (
            "You are the Trend Analyst Agent for an Indonesian resale intelligence platform. "
            "Analyze the web search findings, news signals, and market demand to provide a concise, "
            "authoritative trend report for the reseller in Indonesian/English.\n"
            "Include:\n"
            "1. Demand Velocity (High / Medium / Low) with brief justification.\n"
            "2. Seasonality & Hype cycle (is it rising, peaking, or declining?).\n"
            "3. Key buyer expectations (specs, condition, warranty) that accelerate resale closing."
        )

        item_repr = item.name if isinstance(item, ItemDescription) else str(item)
        user_prompt = (
            f"Item: {item_repr}\n"
            f"Search Query: {findings.query}\n"
            f"Retrieved Findings Summary: {findings.summary}\n"
            f"Trend Signals: {', '.join(findings.trend_signals)}\n\n"
            "Provide the structured trend analysis:"
        )

        target_model = credentials.model or DEFAULT_MODELS.get(
            credentials.provider.lower(), "gpt-4o-mini"
        )
        provider = credentials.provider.lower()
        if (provider == "anthropic" or provider == "custom_anthropic") and not target_model.startswith("anthropic/"):
            target_model = f"anthropic/{target_model}"
        elif (provider == "openai" or provider == "custom_openai") and not target_model.startswith("openai/"):
            target_model = f"openai/{target_model}"

        completion_kwargs = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "api_key": credentials.api_key,
            "temperature": 0.2,
            "max_tokens": 400,
        }
        if credentials.base_url:
            completion_kwargs["api_base"] = credentials.base_url

        response = litellm.completion(**completion_kwargs)

        content = response.choices[0].message.content
        if content and content.strip():
            return content.strip()

    except Exception as e:
        logger.warning("LiteLLM trend synthesis failed (%s); using structured template.", str(e))

    return ""


def trend_analyst_node(
    state: ResellerState,
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
    tavily_api_key: Optional[str] = None,
    serper_api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Synchronous wrapper for trend analyst node."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(
                run_trend_analyst(
                    state,
                    credentials=credentials,
                    mock=mock,
                    tavily_api_key=tavily_api_key,
                    serper_api_key=serper_api_key,
                )
            )
        return asyncio.run(
            run_trend_analyst(
                state,
                credentials=credentials,
                mock=mock,
                tavily_api_key=tavily_api_key,
                serper_api_key=serper_api_key,
            )
        )
    except RuntimeError:
        return asyncio.run(
            run_trend_analyst(
                state,
                credentials=credentials,
                mock=mock,
                tavily_api_key=tavily_api_key,
                serper_api_key=serper_api_key,
            )
        )
