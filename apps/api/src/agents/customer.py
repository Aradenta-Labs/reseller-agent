"""Agent 5: Customer Persona Node.

Responsibilities:
- Accepts ResellerState.
- Roleplays as a skeptical Indonesian secondhand buyer evaluating the proposed item, condition, pricing tiers, and listing strategy.
- Evaluates perceived value, price competitiveness, and likelihood of purchase.
- Concludes with a definitive `customer_verdict`: "BUY" or "PASS" along with detailed psychological reasoning and critical objections.
- Populates `customer_verdict` and appends to `agent_logs`.
- Supports both async and sync execution with structured fallback and mock handling.
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from src.graph.state import AgentLogEntry, ResellerState
from src.models.auth import BYOKCredentials
from src.models.item import ItemDescription
from src.services.llm import DEFAULT_MODELS

logger = logging.getLogger("reseller_api.agents.customer")


class CustomerEvaluationSchema(BaseModel):
    """Structured response model for Customer Persona evaluation."""

    verdict: str = Field(..., description="Definitive verdict: 'BUY' or 'PASS'")
    buyer_sentiment: str = Field(..., description="Overall buyer sentiment (e.g., 'Eager', 'Skeptical', 'Interested but price-sensitive')")
    perceived_value_score: int = Field(..., description="Perceived value rating from 1 to 10", ge=1, le=10)
    top_objections: List[str] = Field(default_factory=list, description="Top objections or questions a buyer will ask")
    deal_breakers: List[str] = Field(default_factory=list, description="Specific conditions that would make the buyer immediately walk away")
    feedback_for_seller: str = Field(..., description="Actionable advice on what would convince this buyer to commit")


async def run_customer_persona(
    state: ResellerState,
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
) -> Dict[str, Any]:
    """Execute Customer Persona Agent node asynchronously.

    Args:
        state: Current ResellerState.
        credentials: Optional BYOK credentials for LLM persona roleplay.
        mock: Force simulated/mock evaluation.

    Returns:
        State update dictionary containing:
            - customer_verdict: str ("BUY" or "PASS")
            - agent_logs: List[AgentLogEntry]
            - errors (if any): List[str]
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    agent_logs = list(state.get("agent_logs") or [])
    errors = list(state.get("errors") or [])

    item_desc = state.get("item_description")
    user_input = state.get("user_input")
    scout_summary = state.get("scout_summary") or {}
    pricing_strategy = state.get("pricing_strategy") or {}
    final_strategy = state.get("final_strategy") or ""

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
        item_name = "Resale Item"

    has_llm = (
        credentials
        and credentials.provider != "mock"
        and credentials.api_key
        and not credentials.api_key.startswith("mock-")
        and credentials.api_key != "test_key"
        and not mock
    )

    try:
        evaluation: Optional[CustomerEvaluationSchema] = None

        if has_llm and credentials:
            evaluation = _evaluate_llm_customer_persona(
                item_name=item_name,
                item_desc=item_desc,
                scout_summary=scout_summary,
                pricing_strategy=pricing_strategy,
                final_strategy=final_strategy,
                credentials=credentials,
            )

        if not evaluation:
            evaluation = _evaluate_mock_customer_persona(
                item_name=item_name,
                scout_summary=scout_summary,
                pricing_strategy=pricing_strategy,
            )

        verdict = evaluation.verdict.upper()
        if verdict not in ["BUY", "PASS"]:
            verdict = "BUY" if "BUY" in verdict else "PASS"

        log_entry: AgentLogEntry = {
            "agent": "customer",
            "status": "completed",
            "message": f"Customer Persona evaluated listing: Verdict '{verdict}' (Perceived Value: {evaluation.perceived_value_score}/10).",
            "timestamp": timestamp,
            "metadata": {
                "verdict": verdict,
                "score": evaluation.perceived_value_score,
                "sentiment": evaluation.buyer_sentiment,
                "objections": evaluation.top_objections,
                "seller_feedback": evaluation.feedback_for_seller,
            },
        }
        agent_logs.append(log_entry)

        return {
            "customer_verdict": verdict,
            "agent_logs": agent_logs,
            "errors": errors,
        }

    except Exception as e:
        logger.error("Customer Persona node encountered an error: %s", str(e), exc_info=True)
        err_msg = f"Customer Persona error: {str(e)}"
        errors.append(err_msg)

        log_entry: AgentLogEntry = {
            "agent": "customer",
            "status": "completed",
            "message": "Customer Persona defaulted to 'BUY' on fallback.",
            "timestamp": timestamp,
            "metadata": {"fallback": True, "error": str(e)},
        }
        agent_logs.append(log_entry)

        return {
            "customer_verdict": "BUY",
            "agent_logs": agent_logs,
            "errors": errors,
        }


def _evaluate_mock_customer_persona(
    item_name: str,
    scout_summary: Dict[str, Any],
    pricing_strategy: Dict[str, Any],
) -> CustomerEvaluationSchema:
    """Intelligent deterministic customer persona evaluator for offline/mock mode."""
    tiers = pricing_strategy.get("tiers") or {}
    fast = tiers.get("fast_sale") or {}
    patient = tiers.get("patient_sale") or {}

    fast_p = float(fast.get("listing_price") or 0.0)
    median_p = float(scout_summary.get("overall_median_price") or 0.0)

    # If the fast sale price is competitive relative to market median, buyer chooses BUY
    if fast_p > 0 and median_p > 0 and fast_p <= median_p:
        return CustomerEvaluationSchema(
            verdict="BUY",
            buyer_sentiment="Interested & Price-Conscious",
            perceived_value_score=8,
            top_objections=[
                "Apakah bisa nego tipis jika langsung transfer / COD hari ini?",
                "Kelengkapan boks dan charger apakah original bawaan pabrik?",
                "Apakah ada garansi personal minimal 3 hari untuk cek fungsi?",
            ],
            deal_breakers=[
                "Akun iCloud / Google lock tersangkut",
                "Ada minus fisik atau fungsional yang tidak diungkapkan di awal",
                "Menolak transaksi melalui Tokopedia Rekber atau COD di tempat umum",
            ],
            feedback_for_seller=(
                f"Harga Rp {int(fast_p):,} sangat menarik dibanding harga pasaran (Rp {int(median_p):,}). "
                "Sertakan video tes fungsi lengkap dan garansi toko/personal 3 hari agar pembeli langsung checkout tanpa ragu."
            ),
        )
    elif fast_p > 0 and median_p > 0 and fast_p > (median_p * 1.15):
        return CustomerEvaluationSchema(
            verdict="PASS",
            buyer_sentiment="Skeptical & Price-Resistant",
            perceived_value_score=4,
            top_objections=[
                f"Harga Rp {int(fast_p):,} lebih mahal dari rata-rata toko lain yang menjual barang serupa.",
                "Apa kelebihan unit ini dibanding listing lain yang harganya lebih murah?",
            ],
            deal_breakers=[
                "Harga di atas rata-rata pasar tanpa ada nilai tambah signifikan (aksesori bonus / sisa garansi panjang)",
            ],
            feedback_for_seller=(
                f"Turunkan harga listing mendekati Rp {int(median_p):,} atau tambahkan bonus menarik agar lebih kompetitif."
            ),
        )
    else:
        return CustomerEvaluationSchema(
            verdict="BUY",
            buyer_sentiment="Cautiously Optimistic",
            perceived_value_score=7,
            top_objections=[
                "Bisa minta foto serial number dan invoice pembelian asli?",
                "Berapa lama estimasi pengiriman dan proteksi packing kayu?",
            ],
            deal_breakers=[
                "Kondisi fisik ternyata tidak sesuai dengan foto",
            ],
            feedback_for_seller=(
                "Harga sudah masuk akal. Tambahkan foto high-resolution di pencahayaan terang untuk mempercepat keputusan beli."
            ),
        )


def _evaluate_llm_customer_persona(
    item_name: str,
    item_desc: Any,
    scout_summary: Dict[str, Any],
    pricing_strategy: Dict[str, Any],
    final_strategy: str,
    credentials: BYOKCredentials,
) -> Optional[CustomerEvaluationSchema]:
    """Execute LLM Instructor call for strict persona appraisal."""
    try:
        import instructor
        import litellm

        client = instructor.from_litellm(litellm.completion)

        system_prompt = (
            "You are the Customer Persona Agent—a sharp, savvy, and skeptical Indonesian secondhand marketplace buyer. "
            "You are reviewing a proposed item listing, condition, price tiers, and seller strategy.\n"
            "Evaluate:\n"
            "1. Perceived value and competitiveness against other sellers on Tokopedia/Shopee/FB Marketplace.\n"
            "2. Potential friction points, doubts, and verification questions you would ask.\n"
            "3. Conclude with a strict verdict: 'BUY' (if price is fair and value is clear) or 'PASS' (if overpriced or risky)."
        )

        user_prompt = (
            f"Item Name: {item_name}\n"
            f"Market Scout Summary: {scout_summary}\n"
            f"Pricing Strategy: {pricing_strategy}\n"
            f"Seller Action Plan: {final_strategy[:500] if final_strategy else 'Standard Listing'}\n\n"
            "Evaluate as the buyer persona:"
        )

        target_model = credentials.model or DEFAULT_MODELS.get(
            credentials.provider.lower(), "gpt-4o-mini"
        )
        provider = credentials.provider.lower()
        if provider == "anthropic" and not target_model.startswith("anthropic/"):
            target_model = f"anthropic/{target_model}"
        elif provider == "openai" and not target_model.startswith("openai/"):
            target_model = f"openai/{target_model}"

        response: CustomerEvaluationSchema = client.chat.completions.create(
            model=target_model,
            response_model=CustomerEvaluationSchema,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            api_key=credentials.api_key,
            temperature=0.3,
        )
        return response

    except Exception as e:
        logger.warning("LiteLLM Customer Persona appraisal failed (%s); using deterministic evaluation.", str(e))
        return None


def customer_persona_node(
    state: ResellerState,
    credentials: Optional[BYOKCredentials] = None,
    mock: bool = False,
) -> Dict[str, Any]:
    """Synchronous wrapper for customer persona node."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(
                run_customer_persona(state, credentials=credentials, mock=mock)
            )
        return asyncio.run(
            run_customer_persona(state, credentials=credentials, mock=mock)
        )
    except RuntimeError:
        return asyncio.run(
            run_customer_persona(state, credentials=credentials, mock=mock)
        )
