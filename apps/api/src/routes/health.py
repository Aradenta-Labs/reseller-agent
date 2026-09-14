from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint returning system status and current phase."""
    return {
        "status": "ok",
        "phase": "1",
        "service": "reseller-agent-api",
        "version": "0.1.0",
        "environment": "development",
    }
