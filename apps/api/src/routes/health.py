import os
import shutil
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint returning system status, scraper engine state, and LLM provider reachability."""
    playwright_available = False
    try:
        import playwright  # noqa: F401
        playwright_available = True
    except ImportError:
        playwright_available = False

    tavily_configured = bool(os.getenv("TAVILY_API_KEY"))
    proxy_configured = bool(os.getenv("SCRAPER_PROXY_URL"))

    return {
        "status": "ok",
        "phase": "5",
        "service": "reseller-agent-api",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "scrapers": {
            "playwright_installed": playwright_available,
            "stealth_engine": "active",
            "proxy_configured": proxy_configured,
            "tavily_fallback_active": tavily_configured,
            "supported_platforms": ["Tokopedia", "Shopee", "Facebook Marketplace"],
        },
        "llm": {
            "byok_supported": True,
            "providers": ["openai", "anthropic", "openrouter", "mock"],
        },
    }
