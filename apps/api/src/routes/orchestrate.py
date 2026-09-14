"""FastAPI routing endpoints for full multi-agent reseller swarm orchestration."""

import logging
from typing import Any, Dict, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, status

from src.graph.workflow import run_reseller_orchestration
from src.models.auth import BYOKCredentials, get_byok_credentials
from src.models.item import ItemDescription
from src.models.orchestrate import AgentLog, OrchestrateRequest, OrchestrateResponse
from src.services.llm import LLMService

logger = logging.getLogger("reseller_api.routes.orchestrate")

router = APIRouter(prefix="/api", tags=["Orchestration"])


@router.post(
    "/orchestrate",
    response_model=OrchestrateResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute full 5-agent reseller swarm orchestration",
)
async def orchestrate_reseller_swarm(
    request: OrchestrateRequest,
    credentials: BYOKCredentials = Depends(get_byok_credentials),
):
    """Run the 5-agent LangGraph swarm for complete market analysis and strategy.

    Workflow execution:
    1. Parse/resolve `item_description` if only text or image was supplied.
    2. Initialize `ResellerState`.
    3. Run parallel Market Scout and Trend Analyst nodes.
    4. Fan-in to Pricing Strategist (20% fee, 15% net margin, 3 price tiers).
    5. Run Chief Strategist (master action plan).
    6. Run Customer Persona (skeptical evaluation & BUY/PASS verdict).
    7. Return structured OrchestrateResponse.
    """
    try:
        # Determine whether mock mode is requested explicitly or implied by mock credentials
        is_mock = request.mock or (credentials.provider == "mock") or (
            credentials.api_key and (credentials.api_key.startswith("mock-") or credentials.api_key == "test_key")
        )

        # 1. Resolve / Parse Item Description if not pre-populated
        item_description: Optional[Union[ItemDescription, Dict[str, Any], str]] = request.item_description
        user_input: str = request.user_input or request.text or ""

        if not item_description:
            # Need to parse from text and/or image
            try:
                llm_service = LLMService(credentials)
                parsed_item = llm_service.parse_item_description(
                    text=request.text or request.user_input,
                    image_base64=request.image_base64,
                )
                item_description = parsed_item
                if not user_input:
                    user_input = parsed_item.name
            except Exception as pe:
                logger.warning("Item parser fallback during orchestration: %s", str(pe))
                item_description = request.text or request.user_input or "Secondhand Item"

        # If user_input still empty, derive from item_description
        if not user_input:
            if isinstance(item_description, ItemDescription):
                user_input = item_description.name
            elif isinstance(item_description, dict):
                user_input = item_description.get("name", "Secondhand Item")
            else:
                user_input = str(item_description)

        # 2. Build initial state
        initial_state = {
            "user_input": user_input,
            "item_description": (
                item_description.model_dump()
                if isinstance(item_description, ItemDescription)
                else item_description
            ),
            "capital_cost": request.capital_cost,
            "market_prices": [],
            "scout_summary": None,
            "trend_analysis": "",
            "pricing_strategy": {},
            "final_strategy": "",
            "customer_verdict": "PASS",
            "errors": [],
            "agent_logs": [],
        }

        # 3. Execute LangGraph workflow
        final_state = await run_reseller_orchestration(
            initial_state=initial_state,
            credentials=credentials,
            mock=is_mock,
            platforms=request.platforms,
        )

        # 4. Map final state to OrchestrateResponse
        logs_raw = final_state.get("agent_logs", [])
        agent_logs = []
        for log in logs_raw:
            if isinstance(log, dict):
                agent_logs.append(
                    AgentLog(
                        agent=log.get("agent", "unknown"),
                        status=log.get("status", "completed"),
                        message=log.get("message", ""),
                        timestamp=log.get("timestamp"),
                        metadata=log.get("metadata", {}),
                    )
                )

        return OrchestrateResponse(
            status="success",
            user_input=final_state.get("user_input", user_input),
            item_description=item_description,
            capital_cost=final_state.get("capital_cost", request.capital_cost),
            market_prices=final_state.get("market_prices", []),
            scout_summary=final_state.get("scout_summary"),
            trend_analysis=final_state.get("trend_analysis", ""),
            pricing_strategy=final_state.get("pricing_strategy", {}),
            final_strategy=final_state.get("final_strategy", ""),
            customer_verdict=final_state.get("customer_verdict", "PASS"),
            errors=final_state.get("errors", []),
            agent_logs=agent_logs,
            provider_used=credentials.provider if credentials else None,
            model_used=credentials.model if credentials else None,
        )

    except Exception as e:
        logger.error("Swarm orchestration failed: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Swarm orchestration failed: {str(e)}",
        )
