"""Market Scout Agent and multi-stage analysis API routes."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from src.models.auth import BYOKCredentials, get_byok_credentials
from src.models.scout import (
    AnalyzeRequest,
    AnalyzeResponse,
    MarketScoutReport,
    ScoutSearchRequest,
)
from src.services.llm import LLMService
from src.services.scout import MarketScoutService

logger = logging.getLogger("reseller_api.routes.scout")

router = APIRouter(prefix="/api", tags=["Market Scout"])


@router.post(
    "/scout/search",
    response_model=MarketScoutReport,
    status_code=status.HTTP_200_OK,
    summary="Search marketplace prices using the Market Scout Agent",
)
async def scout_search(
    request: ScoutSearchRequest,
    credentials: BYOKCredentials = Depends(get_byok_credentials),
):
    """Execute the Market Scout Agent to formulate search keywords, scrape Indonesian

    marketplaces (Tokopedia, Shopee, Facebook Marketplace), and calculate cross-platform statistics.
    """
    try:
        service = MarketScoutService(credentials)
        report = await service.run_scout(
            item=request.item,
            raw_text=request.text,
            query=request.query,
            mock=request.mock,
            platforms=request.platforms,
            max_results_per_platform=request.max_results_per_platform,
        )
        return report
    except Exception as e:
        logger.exception("Failed executing Market Scout search")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Market Scout search failed: {str(e)}",
        )


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Comprehensive item parsing and market research pipeline",
)
async def analyze_item(
    request: AnalyzeRequest,
    credentials: BYOKCredentials = Depends(get_byok_credentials),
):
    """Multi-stage item analysis endpoint.

    1. Parses unstructured text or base64 image into structured ItemDescription (Vision/Parser).
    2. Directly passes ItemDescription into Market Scout Agent to execute live cross-platform intelligence.
    3. Returns combined analysis response.
    """
    try:
        llm_service = LLMService(credentials)
        scout_service = MarketScoutService(credentials)

        # Stage 1: Parse Item Description
        parsed_item = llm_service.parse_item_description(
            text=request.text,
            image_base64=request.image_base64,
        )

        # Stage 2: Trigger Market Scout on parsed item
        scout_report = await scout_service.run_scout(
            item=parsed_item,
            mock=request.mock,
            platforms=request.platforms,
            max_results_per_platform=request.max_results_per_platform,
        )

        return AnalyzeResponse(
            status="success",
            parsed_item=parsed_item,
            scout_report=scout_report,
            provider_used=llm_service.provider,
            model_used=llm_service.model,
        )
    except Exception as e:
        logger.exception("Failed executing comprehensive analysis pipeline")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis pipeline failed: {str(e)}",
        )
