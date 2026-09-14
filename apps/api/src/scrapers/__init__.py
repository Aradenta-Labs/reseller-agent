"""Scrapers module exposing individual scrapers and unified parallel orchestrator."""

import asyncio
import logging
from typing import Dict, List, Optional

from src.scrapers.base import BaseScraper, ProductListing, ScrapeResult
from src.scrapers.fb import FacebookMarketplaceScraper
from src.scrapers.shopee import ShopeeScraper
from src.scrapers.tokped import TokopediaScraper

logger = logging.getLogger(__name__)

PLATFORM_SCRAPER_MAP = {
    "tokopedia": TokopediaScraper,
    "shopee": ShopeeScraper,
    "facebook": FacebookMarketplaceScraper,
    "facebook_marketplace": FacebookMarketplaceScraper,
}


async def scrape_all_platforms(
    search_term: str,
    platforms: Optional[List[str]] = None,
    max_results_per_platform: int = 10,
    fallback_on_error: bool = True,
) -> Dict[str, ScrapeResult]:
    """Execute scraping concurrently across requested marketplace platforms.

    Args:
        search_term: The search query or product name.
        platforms: List of platform keys to scrape (e.g. ['tokopedia', 'shopee', 'facebook']).
                   Defaults to all three platforms if None.
        max_results_per_platform: Maximum product listings to collect per platform.
        fallback_on_error: Whether to return empty/fallback ScrapeResult on unexpected exceptions.

    Returns:
        Dict mapping platform name/key to its ScrapeResult.
    """
    if platforms is None:
        target_keys = ["tokopedia", "shopee", "facebook"]
    else:
        target_keys = [p.lower().strip() for p in platforms]

    scrapers_to_run = []
    keys_order = []

    for key in target_keys:
        scraper_cls = PLATFORM_SCRAPER_MAP.get(key)
        if scraper_cls:
            scrapers_to_run.append(scraper_cls())
            keys_order.append(key)
        else:
            logger.warning("Unknown platform requested for scraping: %s", key)

    async def _safe_scrape(key: str, scraper: BaseScraper) -> tuple[str, ScrapeResult]:
        try:
            res = await scraper.scrape(search_term=search_term, max_results=max_results_per_platform)
            return key, res
        except Exception as exc:
            logger.error("Error executing scraper for %s: %s", key, str(exc))
            if fallback_on_error:
                res = scraper.calculate_stats(
                    [], platform=scraper.platform_name, error=f"Unhandled scraping exception: {str(exc)}"
                )
                return key, res
            raise exc

    tasks = [_safe_scrape(key, scraper) for key, scraper in zip(keys_order, scrapers_to_run)]
    results = await asyncio.gather(*tasks, return_exceptions=False)

    return {key: res for key, res in results}


__all__ = [
    "BaseScraper",
    "ProductListing",
    "ScrapeResult",
    "TokopediaScraper",
    "ShopeeScraper",
    "FacebookMarketplaceScraper",
    "scrape_all_platforms",
    "PLATFORM_SCRAPER_MAP",
]
