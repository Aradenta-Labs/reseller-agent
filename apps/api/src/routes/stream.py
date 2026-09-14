"""Server-Sent Events (SSE) streaming routes for real-time multi-agent swarm orchestration."""

import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional, Union

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from src.graph.workflow import stream_reseller_orchestration
from src.models.auth import BYOKCredentials, get_byok_credentials
from src.models.item import ItemDescription
from src.models.orchestrate import OrchestrateRequest
from src.services.llm import LLMService

logger = logging.getLogger("reseller_api.routes.stream")

router = APIRouter(prefix="/api", tags=["Streaming Orchestration"])


async def sse_event_generator(
    request: OrchestrateRequest,
    credentials: BYOKCredentials,
) -> AsyncGenerator[str, None]:
    """Generate Server-Sent Events (SSE) from the multi-agent workflow stream."""
    try:
        is_mock = request.mock or (credentials.provider == "mock") or (
            credentials.api_key and (credentials.api_key.startswith("mock-") or credentials.api_key == "test_key")
        )

        # 1. Resolve / Parse Item Description if not pre-populated
        item_description: Optional[Union[ItemDescription, Dict[str, Any], str]] = request.item_description
        user_input: str = request.user_input or request.text or ""

        if not item_description:
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
                logger.warning("Item parser fallback during stream orchestration: %s", str(pe))
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

        # 3. Stream from LangGraph workflow
        async for event in stream_reseller_orchestration(
            initial_state=initial_state,
            credentials=credentials,
            mock=is_mock,
            platforms=request.platforms,
        ):
            event_json = json.dumps(event, default=str)
            yield f"data: {event_json}\n\n"

    except Exception as e:
        logger.error("SSE stream generator encountered fatal error: %s", str(e), exc_info=True)
        error_payload = {
            "type": "ERROR",
            "error": str(e),
            "message": f"Fatal stream error: {str(e)}",
        }
        yield f"data: {json.dumps(error_payload)}\n\n"


@router.post(
    "/orchestrate/stream",
    status_code=status.HTTP_200_OK,
    summary="Execute multi-agent swarm orchestration and stream real-time SSE events",
)
async def stream_orchestrate_reseller_swarm(
    request: OrchestrateRequest,
    credentials: BYOKCredentials = Depends(get_byok_credentials),
) -> StreamingResponse:
    """Stream real-time agent progression events via Server-Sent Events (SSE).

    Event Sequence:
    1. `AGENT_START` -> emitted before each agent starts.
    2. `AGENT_COMPLETE` -> emitted with output when each agent finishes.
    3. `FINAL_RESULT` -> emitted with full aggregated state upon completion.
    4. `ERROR` -> emitted if an unrecoverable exception occurs.
    """
    return StreamingResponse(
        sse_event_generator(request=request, credentials=credentials),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
