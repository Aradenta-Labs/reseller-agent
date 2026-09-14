from fastapi import APIRouter, Depends, HTTPException, status
from src.models.auth import BYOKCredentials, get_byok_credentials
from src.models.item import ItemParseRequest, ItemParseResponse
from src.services.llm import LLMService

router = APIRouter(prefix="/api", tags=["Parser"])


@router.post(
    "/parse-item",
    response_model=ItemParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Parse item description or image into structured item metadata",
)
async def parse_item(
    request: ItemParseRequest,
    credentials: BYOKCredentials = Depends(get_byok_credentials),
):
    """Extract structured ItemDescription from text or base64 image input using BYOK credentials."""
    try:
        service = LLMService(credentials)
        item_description = service.parse_item_description(
            text=request.text,
            image_base64=request.image_base64,
        )
        return ItemParseResponse(
            status="success",
            item=item_description,
            provider_used=service.provider,
            model_used=service.model,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse item: {str(e)}",
        )
