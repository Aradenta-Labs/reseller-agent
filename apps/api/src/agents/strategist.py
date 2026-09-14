"""Agent 3: Pricing Strategist & Agent 4: Chief Strategist Nodes.

Responsibilities:
1. `run_pricing_strategist(state, ...)`:
   - Applies core financial rules:
     - 20% platform fee for online marketplaces (Tokopedia/Shopee/FB Marketplace shipping).
     - Minimum 15% net profit margin requirement.
     - Generates 3 distinct price tiers:
       1) Fast Sale (Online - undercutting competitors at lowest/10th percentile price with margin check)
       2) Patient Sale (Online - max profit at average/median market price)
       3) Direct/Offline Sale (0% platform fee, local COD).
     - Calculates maximum recommended acquisition/buying price (`max_buy_price` or `target_buy_price`).
     - If user provided `capital_cost`, calculates projected profit and ROI for each tier.
   - Populates `pricing_strategy` dictionary and appends to `agent_logs`.

2. `run_chief_strategist(state, ...)`:
   - Synthesizes all gathered market data (`market_prices`, `scout_summary`), trend analysis, and pricing tiers into a structured step-by-step action plan for the reseller.
   - Covers: Go/No-Go recommendation, where to list, photography & title tips, listing price schedule, risk mitigation.
   - Uses LiteLLM or structured fallback if mock mode.
   - Populates `final_strategy` string and appends to `agent_logs`.
"""

import asyncio
from datetime import datetime, timezone
import logging
import math
from typing import Any, Dict, List, Optional, Union

from src.graph.state import AgentLogEntry, ResellerState
from src.models.auth import BYOKCredentials
from src.models.item import ItemDescription
from src.services.llm import DEFAULT_MODELS

logger = logging.getLogger("reseller_api.agents.strategist")

# Financial constants
ONLINE_PLATFORM_FEE_RATE = 0.20  # 20% marketplace transaction & handling fee
MIN_NET_MARGIN_RATE = 0.15      # 15% target minimum net profit margin


# ============================================================================
# AGENT 3: PRICING STRATEGIST
# ============================================================================

async def run_pricing_strategist(
    state: ResellerState,
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
) -> Dict[str, Any]:
    """Execute Pricing Strategist Agent node asynchronously.

    Calculates 3 pricing tiers, fee deductions, margin checks, target buying price,
    and projected ROI if capital cost is provided.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    agent_logs = list(state.get("agent_logs") or [])
    errors = list(state.get("errors") or [])

    scout_summary = state.get("scout_summary") or {}
    market_prices = state.get("market_prices") or []
    capital_cost = state.get("capital_cost")

    try:
        # Step 1: Extract baseline statistical benchmarks
        lowest_price = float(scout_summary.get("overall_lowest_price") or 0.0)
        highest_price = float(scout_summary.get("overall_highest_price") or 0.0)
        median_price = float(scout_summary.get("overall_median_price") or 0.0)
        average_price = float(scout_summary.get("overall_average_price") or 0.0)

        # If summary was empty but listings exist, compute on the fly
        if (median_price == 0.0 or lowest_price == 0.0) and market_prices:
            prices = [
                float(p["price"]) for p in market_prices if p.get("price") and float(p["price"]) > 0
            ]
            if prices:
                lowest_price = min(prices)
                highest_price = max(prices)
                average_price = sum(prices) / len(prices)
                sorted_p = sorted(prices)
                mid = len(sorted_p) // 2
                median_price = (sorted_p[mid] + sorted_p[~mid]) / 2.0

        # Fallback benchmark if no listings were available
        if median_price == 0.0:
            median_price = 1_500_000.0
            lowest_price = 1_200_000.0
            highest_price = 1_800_000.0
            average_price = 1_500_000.0

        # Baseline benchmark price (use median as steady market anchor)
        benchmark_price = median_price if median_price > 0 else average_price

        # Step 2: Determine Tier Selling Prices
        # Tier 1: Fast Sale (Online) - slightly below lowest or 5% below median for rapid turnover
        fast_sale_price = round(min(lowest_price * 0.98 if lowest_price > 0 else benchmark_price * 0.90, benchmark_price * 0.92), -3)
        if fast_sale_price <= 0:
            fast_sale_price = round(benchmark_price * 0.90, -3)

        # Tier 2: Patient Sale (Online) - target median / upper market price for max profit
        patient_sale_price = round(benchmark_price, -3)
        if patient_sale_price <= fast_sale_price:
            patient_sale_price = round(fast_sale_price * 1.10, -3)

        # Tier 3: Direct/Offline Sale (COD) - 0% platform fee, competitive local pricing
        direct_sale_price = round(benchmark_price * 0.95, -3)

        # Step 3: Financial Calculations per Tier
        tiers: Dict[str, Any] = {}

        # Helper to compute tier metrics
        def compute_tier(selling_price: float, fee_rate: float, tier_name: str, description: str) -> Dict[str, Any]:
            platform_fee = round(selling_price * fee_rate, 2)
            net_payout = round(selling_price - platform_fee, 2)
            # Max buying price to guarantee at least 15% net margin: Net Payout / (1 + 0.15)
            max_buy_for_margin = round(net_payout / (1.0 + MIN_NET_MARGIN_RATE), -3)

            tier_data: Dict[str, Any] = {
                "tier_name": tier_name,
                "description": description,
                "listing_price": selling_price,
                "platform_fee_rate": fee_rate,
                "estimated_platform_fee": platform_fee,
                "net_payout": net_payout,
                "max_recommended_buy_price": max_buy_for_margin,
            }

            if capital_cost is not None and capital_cost > 0:
                net_profit = round(net_payout - capital_cost, 2)
                roi_pct = round((net_profit / capital_cost) * 100.0, 2)
                margin_pct = round((net_profit / selling_price) * 100.0, 2)
                meets_margin = margin_pct >= (MIN_NET_MARGIN_RATE * 100.0)

                tier_data.update({
                    "capital_cost": capital_cost,
                    "projected_net_profit": net_profit,
                    "projected_roi_pct": roi_pct,
                    "profit_margin_pct": margin_pct,
                    "meets_target_margin": meets_margin,
                })
            else:
                tier_data.update({
                    "meets_target_margin": True,
                })

            return tier_data

        tiers["fast_sale"] = compute_tier(
            fast_sale_price,
            ONLINE_PLATFORM_FEE_RATE,
            "Fast Sale (Online)",
            "Undercut competitors on Tokopedia/Shopee for 1-3 day turnaround.",
        )
        tiers["patient_sale"] = compute_tier(
            patient_sale_price,
            ONLINE_PLATFORM_FEE_RATE,
            "Patient Sale (Online)",
            "Optimized for maximum profit margin on online marketplaces (7-14 days).",
        )
        tiers["direct_sale"] = compute_tier(
            direct_sale_price,
            0.0,
            "Direct / Offline Sale (COD)",
            "0% platform fees via Facebook Marketplace / local meetup (COD).",
        )

        # Target acquisition price across baseline:
        # Based on patient sale payout with 15% net margin
        patient_net = tiers["patient_sale"]["net_payout"]
        target_buy_price = round(patient_net / (1.0 + MIN_NET_MARGIN_RATE), -3)

        pricing_strategy: Dict[str, Any] = {
            "currency": "IDR",
            "benchmark_median_price": benchmark_price,
            "platform_fee_rate": ONLINE_PLATFORM_FEE_RATE,
            "target_min_margin_rate": MIN_NET_MARGIN_RATE,
            "target_buy_price": target_buy_price,
            "max_buy_price": target_buy_price,
            "tiers": tiers,
            "summary_recommendation": (
                f"Target acquisition price: max Rp {int(target_buy_price):,} to secure ≥15% net margin. "
                f"Sell at Rp {int(fast_sale_price):,} for fast liquidation or Rp {int(patient_sale_price):,} for maximum yield."
            ),
        }

        log_entry: AgentLogEntry = {
            "agent": "pricing",
            "status": "completed",
            "message": f"Pricing Strategist formulated 3 tiers. Recommended max buy price: Rp {int(target_buy_price):,}.",
            "timestamp": timestamp,
            "metadata": {
                "fast_sale": fast_sale_price,
                "patient_sale": patient_sale_price,
                "direct_sale": direct_sale_price,
                "max_buy_price": target_buy_price,
            },
        }
        agent_logs.append(log_entry)

        return {
            "pricing_strategy": pricing_strategy,
            "agent_logs": agent_logs,
            "errors": errors,
        }

    except Exception as e:
        logger.error("Pricing Strategist node encountered an error: %s", str(e), exc_info=True)
        err_msg = f"Pricing Strategist error: {str(e)}"
        errors.append(err_msg)

        fallback_pricing = {
            "currency": "IDR",
            "benchmark_median_price": 1_500_000.0,
            "platform_fee_rate": 0.20,
            "target_min_margin_rate": 0.15,
            "target_buy_price": 1_000_000.0,
            "max_buy_price": 1_000_000.0,
            "tiers": {
                "fast_sale": {"listing_price": 1_350_000.0, "net_payout": 1_080_000.0},
                "patient_sale": {"listing_price": 1_500_000.0, "net_payout": 1_200_000.0},
                "direct_sale": {"listing_price": 1_400_000.0, "net_payout": 1_400_000.0},
            },
            "summary_recommendation": "Gunakan harga jual patokan Rp 1.500.000 dengan target beli maksimal Rp 1.000.000.",
        }

        log_entry: AgentLogEntry = {
            "agent": "pricing",
            "status": "completed",
            "message": "Pricing Strategist recovered with default pricing tiers.",
            "timestamp": timestamp,
            "metadata": {"fallback": True, "error": str(e)},
        }
        agent_logs.append(log_entry)

        return {
            "pricing_strategy": fallback_pricing,
            "agent_logs": agent_logs,
            "errors": errors,
        }


def pricing_strategist_node(
    state: ResellerState,
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
) -> Dict[str, Any]:
    """Synchronous wrapper for pricing strategist node."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(
                run_pricing_strategist(state, credentials=credentials, mock=mock)
            )
        return asyncio.run(
            run_pricing_strategist(state, credentials=credentials, mock=mock)
        )
    except RuntimeError:
        return asyncio.run(
            run_pricing_strategist(state, credentials=credentials, mock=mock)
        )


# ============================================================================
# AGENT 4: CHIEF STRATEGIST
# ============================================================================

async def run_chief_strategist(
    state: ResellerState,
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
) -> Dict[str, Any]:
    """Execute Chief Strategist Agent node asynchronously.

    Synthesizes market listings, statistical summary, trend analysis, and pricing tiers
    into an end-to-end executable resale master strategy.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    agent_logs = list(state.get("agent_logs") or [])
    errors = list(state.get("errors") or [])

    item_desc = state.get("item_description")
    user_input = state.get("user_input")
    scout_summary = state.get("scout_summary") or {}
    trend_analysis = state.get("trend_analysis") or ""
    pricing_strategy = state.get("pricing_strategy") or {}
    capital_cost = state.get("capital_cost")

    item_name = ""
    if isinstance(item_desc, ItemDescription):
        item_name = item_desc.name
    elif isinstance(item_desc, dict):
        item_name = str(item_desc.get("name") or item_desc.get("summary") or "Product")
    elif isinstance(item_desc, str) and item_desc.strip():
        item_name = item_desc.strip()
    elif user_input and user_input.strip():
        item_name = user_input.strip()
    else:
        item_name = "Trending Resale Item"

    has_llm = (
        credentials
        and credentials.provider != "mock"
        and credentials.api_key
        and not credentials.api_key.startswith("mock-")
        and credentials.api_key != "test_key"
        and not mock
    )

    try:
        final_strategy_text = ""

        if has_llm and credentials:
            final_strategy_text = _synthesize_llm_chief_strategy(
                item_name=item_name,
                item_desc=item_desc,
                scout_summary=scout_summary,
                trend_analysis=trend_analysis,
                pricing_strategy=pricing_strategy,
                capital_cost=capital_cost,
                credentials=credentials,
            )

        if not final_strategy_text:
            final_strategy_text = _format_structured_chief_strategy(
                item_name=item_name,
                item_desc=item_desc,
                scout_summary=scout_summary,
                trend_analysis=trend_analysis,
                pricing_strategy=pricing_strategy,
                capital_cost=capital_cost,
            )

        log_entry: AgentLogEntry = {
            "agent": "chief",
            "status": "completed",
            "message": f"Chief Strategist formulated actionable execution plan for '{item_name}'.",
            "timestamp": timestamp,
            "metadata": {
                "item_name": item_name,
                "strategy_length": len(final_strategy_text),
            },
        }
        agent_logs.append(log_entry)

        return {
            "final_strategy": final_strategy_text,
            "agent_logs": agent_logs,
            "errors": errors,
        }

    except Exception as e:
        logger.error("Chief Strategist node encountered an error: %s", str(e), exc_info=True)
        err_msg = f"Chief Strategist error: {str(e)}"
        errors.append(err_msg)

        fallback_strategy = _format_structured_chief_strategy(
            item_name=item_name,
            item_desc=item_desc,
            scout_summary=scout_summary,
            trend_analysis=trend_analysis,
            pricing_strategy=pricing_strategy,
            capital_cost=capital_cost,
        )

        log_entry: AgentLogEntry = {
            "agent": "chief",
            "status": "completed",
            "message": "Chief Strategist recovered with template action plan.",
            "timestamp": timestamp,
            "metadata": {"fallback": True, "error": str(e)},
        }
        agent_logs.append(log_entry)

        return {
            "final_strategy": fallback_strategy,
            "agent_logs": agent_logs,
            "errors": errors,
        }


def _format_structured_chief_strategy(
    item_name: str,
    item_desc: Any,
    scout_summary: Dict[str, Any],
    trend_analysis: str,
    pricing_strategy: Dict[str, Any],
    capital_cost: Optional[float],
) -> str:
    """Deterministic, beautifully structured master strategy template."""
    tiers = pricing_strategy.get("tiers") or {}
    fast = tiers.get("fast_sale") or {}
    patient = tiers.get("patient_sale") or {}
    direct = tiers.get("direct_sale") or {}

    fast_p = int(fast.get("listing_price") or 0)
    patient_p = int(patient.get("listing_price") or 0)
    direct_p = int(direct.get("listing_price") or 0)
    target_buy = int(pricing_strategy.get("target_buy_price") or 0)
    median_p = int(scout_summary.get("overall_median_price") or 0)
    best_platform = scout_summary.get("best_platform_recommendation") or "Tokopedia & FB Marketplace"

    # Go/No-Go logic
    go_status = "🟢 GO (RECOMMENDED)"
    if capital_cost and target_buy > 0 and capital_cost > target_buy:
        go_status = "🟡 CAUTION / NEGOTIATE BUY PRICE (Capital cost exceeds target buying price)"

    lines = [
        f"### 🎯 Master Resale Plan: {item_name}",
        "",
        f"**Verdict & Status:** {go_status}",
        f"- **Target Max Acquisition Price:** Rp {target_buy:,}" if target_buy else "",
        f"- **Capital Cost:** Rp {int(capital_cost):,}" if capital_cost else "- **Capital Cost:** Not specified",
        f"- **Market Median Benchmark:** Rp {median_p:,}" if median_p else "",
        "",
        "---",
        "#### 1. Recommended Pricing Schedule",
        f"- **Fast Sale Tier (Online 1-3 Days):** Rp {fast_p:,} *(Net payout ~Rp {int(fast.get('net_payout', 0)):,} after 20% platform fee)*",
        f"- **Patient Sale Tier (Online Max Profit):** Rp {patient_p:,} *(Net payout ~Rp {int(patient.get('net_payout', 0)):,} after 20% platform fee)*",
        f"- **Direct / COD Sale (0% Fee):** Rp {direct_p:,} *(Net payout Rp {direct_p:,})*",
        "",
        "#### 2. Channel & Listing Strategy",
        f"- **Primary Channel:** {best_platform} (Highest liquidity & buyer traffic).",
        "- **Cross-Listing:** Post simultaneously on Tokopedia (for rekber/escrow peace of mind) and Facebook Marketplace (for instant cash COD).",
        "- **Listing Title Formula:** `[Brand] [Model] [Variant] - [Condition Highlight] Fullset Garansi`",
        "",
        "#### 3. Photography & Visual Presentation Tips",
        "- 📸 **Hero Image:** Clean, high-contrast natural lighting shot from a 45-degree angle with clean background.",
        "- 🔍 **Proof of Condition:** High-resolution close-ups of all edges, ports, serial number, and battery health / authenticity tag.",
        "- 📦 **Included Accessories:** Lay out the original box, charger, receipt/warranty card in one flat-lay photo.",
        "",
        "#### 4. Risk Mitigation & Closing Tactics",
        "- **Handling Lowballers:** Set firm floor price at Fast Sale tier; counter offer with direct COD meetup.",
        "- **Fraud Prevention:** Strictly use official in-app escrow for courier deliveries or safe public locations (mall/coffee shop) for COD.",
    ]

    return "\n".join([line for line in lines if line is not None])


def _synthesize_llm_chief_strategy(
    item_name: str,
    item_desc: Any,
    scout_summary: Dict[str, Any],
    trend_analysis: str,
    pricing_strategy: Dict[str, Any],
    capital_cost: Optional[float],
    credentials: BYOKCredentials,
) -> str:
    """Synthesize complete action plan via LiteLLM."""
    try:
        import litellm

        system_prompt = (
            "You are the Chief Strategist Agent for an Indonesian resale intelligence platform. "
            "Your role is to synthesize market scout data, trend signals, and pricing calculations into "
            "an actionable, executive-ready resale playbook for an entrepreneur.\n"
            "Format your output with clear markdown headings:\n"
            "1. Recommendation & Go/No-Go Decision\n"
            "2. Dynamic Pricing Schedule (Fast Sale, Patient Sale, Direct COD)\n"
            "3. Platform & Cross-Listing Strategy (Tokopedia, Shopee, FB Marketplace)\n"
            "4. Product Photography & Copywriting Tips\n"
            "5. Negotiation & Fraud Risk Mitigation"
        )

        user_prompt = (
            f"Item Name: {item_name}\n"
            f"Capital Cost: {capital_cost if capital_cost else 'N/A'}\n"
            f"Market Scout Summary: {scout_summary}\n"
            f"Trend Analysis: {trend_analysis}\n"
            f"Pricing Strategy & Tiers: {pricing_strategy}\n\n"
            "Synthesize the master resale playbook:"
        )

        target_model = credentials.model or DEFAULT_MODELS.get(
            credentials.provider.lower(), "gpt-4o-mini"
        )
        provider = credentials.provider.lower()
        if provider == "anthropic" and not target_model.startswith("anthropic/"):
            target_model = f"anthropic/{target_model}"
        elif provider == "openai" and not target_model.startswith("openai/"):
            target_model = f"openai/{target_model}"

        response = litellm.completion(
            model=target_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            api_key=credentials.api_key,
            temperature=0.25,
            max_tokens=700,
        )

        content = response.choices[0].message.content
        if content and content.strip():
            return content.strip()

    except Exception as e:
        logger.warning("LiteLLM Chief Strategist synthesis failed (%s); falling back to structured template.", str(e))

    return ""


def chief_strategist_node(
    state: ResellerState,
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
) -> Dict[str, Any]:
    """Synchronous wrapper for chief strategist node."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(
                run_chief_strategist(state, credentials=credentials, mock=mock)
            )
        return asyncio.run(
            run_chief_strategist(state, credentials=credentials, mock=mock)
        )
    except RuntimeError:
        return asyncio.run(
            run_chief_strategist(state, credentials=credentials, mock=mock)
        )
