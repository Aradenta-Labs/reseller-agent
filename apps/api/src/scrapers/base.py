"""Base scraper models and interface for marketplace data acquisition."""

from abc import ABC, abstractmethod
import asyncio
import math
import os
import random
import re
import statistics
import time
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

# Global lock & timestamp tracker for rate limiting / cooldown across scrapers
_LAST_SCRAPE_TIMESTAMP: float = 0.0
_SCRAPER_RATE_LOCK = asyncio.Lock()

# Realistic fingerprint pools for session randomization
FINGERPRINT_POOL: List[Dict[str, Any]] = [
    {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "id-ID",
        "timezone_id": "Asia/Jakarta",
        "platform": "macOS",
    },
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "viewport": {"width": 1440, "height": 900},
        "locale": "id-ID",
        "timezone_id": "Asia/Jakarta",
        "platform": "Windows",
    },
    {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "viewport": {"width": 1536, "height": 864},
        "locale": "id-ID",
        "timezone_id": "Asia/Jakarta",
        "platform": "Windows",
    },
    {
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "id-ID",
        "timezone_id": "Asia/Jakarta",
        "platform": "Linux",
    },
]


def get_random_fingerprint() -> Dict[str, Any]:
    """Select a randomized browser fingerprint profile from the pool."""
    return random.choice(FINGERPRINT_POOL)


async def enforce_scraper_cooldown() -> None:
    """Enforce a configurable cooldown between scraper operations from the container."""
    global _LAST_SCRAPE_TIMESTAMP
    cooldown_seconds = float(os.getenv("SCRAPER_COOLDOWN_SECONDS", "1.5"))
    if cooldown_seconds <= 0:
        return

    async with _SCRAPER_RATE_LOCK:
        now = time.time()
        elapsed = now - _LAST_SCRAPE_TIMESTAMP
        if elapsed < cooldown_seconds:
            wait_time = cooldown_seconds - elapsed
            await asyncio.sleep(wait_time)
        _LAST_SCRAPE_TIMESTAMP = time.time()


def get_scraper_proxy_config() -> Optional[Dict[str, str]]:
    """Retrieve proxy configuration from SCRAPER_PROXY_URL env if present."""
    proxy_url = os.getenv("SCRAPER_PROXY_URL")
    if proxy_url and proxy_url.strip():
        return {"server": proxy_url.strip()}
    return None


class ProductListing(BaseModel):
    """Model representing an individual product listing scraped from a marketplace."""

    title: str = Field(..., description="Product title or listing headline")
    price: float = Field(..., description="Parsed numeric price value in IDR")
    url: Optional[str] = Field(None, description="Direct URL link to the product listing")
    platform: str = Field(..., description="Source platform name (e.g., Tokopedia, Shopee, Facebook Marketplace)")
    condition: Optional[str] = Field(
        None, description="Condition of the item if specified (e.g., Baru, Bekas, Like New)"
    )
    location: Optional[str] = Field(
        None, description="Location/city of seller or item origin"
    )
    raw_price: Optional[str] = Field(
        None, description="Original unparsed raw price string extracted from the webpage"
    )


class ScrapeResult(BaseModel):
    """Aggregated scrape summary statistics and listings extracted for a search term."""

    platform: str = Field(..., description="Source marketplace platform")
    lowest_price: float = Field(0.0, description="Minimum price among valid listings")
    highest_price: float = Field(0.0, description="Maximum price among valid listings")
    average_price: float = Field(0.0, description="Arithmetic mean price across valid listings")
    median_price: float = Field(0.0, description="Median price across valid listings")
    sample_count: int = Field(0, description="Total number of valid parsed product listings")
    top_listings: List[ProductListing] = Field(
        default_factory=list, description="List of top product listings gathered"
    )
    error: Optional[str] = Field(
        None, description="Error message if scraping or parsing encountered issues"
    )
    fallback_used: bool = Field(
        False, description="Indicates whether fallback search (Tavily/Serper) was triggered"
    )


class BaseScraper(ABC):
    """Abstract base class defining the scraping interface and price processing utilities."""

    platform_name: str = "Base"

    @abstractmethod
    async def scrape(self, search_term: str, max_results: int = 10) -> ScrapeResult:
        """Asynchronously scrape the target marketplace for a search term.

        Args:
            search_term: The query string or item title to search.
            max_results: Maximum number of listings to retrieve and return.

        Returns:
            ScrapeResult containing statistical summary and top listings.
        """
        pass

    @classmethod
    async def simulate_human_interaction(cls, page: Any) -> None:
        """Simulate realistic human behavior (random smooth scrolling and mouse jiggle)."""
        try:
            # 1. Random mouse movement
            await page.mouse.move(random.randint(100, 500), random.randint(100, 400))
            await asyncio.sleep(random.uniform(0.1, 0.3))

            # 2. Variable scrolling with small jitter
            for _ in range(random.randint(1, 3)):
                scroll_delta = random.randint(300, 700)
                await page.evaluate(f"window.scrollBy(0, {scroll_delta})")
                await asyncio.sleep(random.uniform(0.2, 0.5))

            # 3. Micro hesitation
            await page.mouse.move(random.randint(200, 700), random.randint(300, 600))
            await asyncio.sleep(random.uniform(0.1, 0.2))
        except Exception:
            pass

    @classmethod
    def clean_idr_price(cls, raw_price: Optional[str]) -> Optional[float]:
        """Robustly parse Indonesian Rupiah (IDR) price strings into numeric float values.

        Handles diverse Indonesian currency formats:
        - Standard IDR: 'Rp 1.500.000', 'Rp. 1.500.000', 'RP 1500000', 'Rp1.500.000'
        - Standard English/Comma: '1,500,000', '$1,500.00'
        - Multipliers (Juta/jt): '1.5jt', '1,5 jt', '1.5 juta', '2jt', '0.5 jt'
        - Multipliers (Ribu/k): '1500k', '1.500k', '150 rb', '150ribu'
        - Multipliers (Miliar/M): '1.2m', '1.2 miliar'
        - Free / Special keywords: 'Gratis', 'Free', 'Rp 0' -> 0.0
        - Ranges: takes the first valid price or lower bound (e.g. 'Rp 1.500.000 - Rp 2.000.000' -> 1500000.0)

        Args:
            raw_price: Raw text string representing the price.

        Returns:
            Extracted price as a float, or None if parsing fails.
        """
        if not raw_price or not isinstance(raw_price, str):
            return None

        text = raw_price.strip()
        if not text:
            return None

        # Check for free items
        lower = text.lower()
        if any(term in lower for term in ["gratis", "free", "cuma-cuma"]):
            return 0.0

        # Handle price ranges by taking the first portion
        if " - " in text or " – " in text or " — " in text:
            parts = re.split(r"\s*[-–—]\s*", text)
            if parts and parts[0].strip():
                text = parts[0].strip()
                lower = text.lower()

        # Multiplier regexes
        # 1. Juta (jt / juta / jta)
        jt_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:jt|juta|jta)\b", lower)
        if jt_match:
            val_str = jt_match.group(1).replace(",", ".")
            try:
                val = float(val_str)
                return float(round(val * 1_000_000))
            except ValueError:
                pass

        # 2. Miliar (m / milyar / miliar / milyard) - only if preceded by number and explicitly 'm' or 'miliar'
        m_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:miliar|milyar|milyard)\b", lower)
        if m_match:
            val_str = m_match.group(1).replace(",", ".")
            try:
                val = float(val_str)
                return float(round(val * 1_000_000_000))
            except ValueError:
                pass

        # 3. Ribu (k / rb / ribu)
        k_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:k|rb|ribu)\b", lower)
        if k_match:
            val_str = k_match.group(1)
            # If formatted like 1.500k or 1,500k where 3 digits follow delimiter, it is 1500k
            parts = re.split(r"[.,]", val_str)
            if len(parts) == 2 and len(parts[1]) == 3:
                val_str = parts[0] + parts[1]
            else:
                val_str = val_str.replace(",", ".")
            try:
                val = float(val_str)
                return float(round(val * 1_000))
            except ValueError:
                pass

        # Normalize currency prefixes
        clean_text = re.sub(r"(?i)\b(?:rp\.?|idr)\b", "", text).strip()
        # Extract numerical sequence with delimiters
        num_match = re.search(r"(\d[\d.,]*)", clean_text)
        if not num_match:
            return None

        num_str = num_match.group(1).strip()

        # Disambiguate Indonesian dot format (1.500.000) vs English decimal (1500.50)
        # Case A: Contains both '.' and ','
        if "." in num_str and "," in num_str:
            last_dot = num_str.rfind(".")
            last_comma = num_str.rfind(",")
            if last_comma > last_dot:
                # 1.500.000,50 (Indonesian standard with comma decimal)
                num_str = num_str.replace(".", "").replace(",", ".")
            else:
                # 1,500,000.50 (US standard with dot decimal)
                num_str = num_str.replace(",", "")
        # Case B: Multiple dots or dots with 3 trailing digits (1.500.000 or 15.000 or 1.500)
        elif "." in num_str:
            dots_count = num_str.count(".")
            parts = num_str.split(".")
            # If multiple dots, they are definitely thousand separators (1.500.000)
            if dots_count > 1:
                num_str = num_str.replace(".", "")
            elif len(parts) == 2 and len(parts[1]) == 3:
                # e.g., 50.000 or 5.000 -> thousand separator
                num_str = num_str.replace(".", "")
            elif len(parts) == 2 and len(parts[1]) == 2:
                # e.g. 50.00 -> decimal
                pass
            else:
                # Ambiguous single dot: if part[1] is 3 digits treated as thousands, else decimal
                if len(parts[1]) == 3:
                    num_str = num_str.replace(".", "")
        # Case C: Comma separated (1,500,000 or 15,000)
        elif "," in num_str:
            comma_count = num_str.count(",")
            parts = num_str.split(",")
            if comma_count > 1:
                num_str = num_str.replace(",", "")
            elif len(parts) == 2 and len(parts[1]) == 3:
                num_str = num_str.replace(",", "")
            elif len(parts) == 2 and len(parts[1]) == 2:
                # Decimal comma e.g. 50,50 -> 50.50
                num_str = num_str.replace(",", ".")
            else:
                num_str = num_str.replace(",", "")

        try:
            val = float(num_str)
            return val
        except ValueError:
            return None

    @classmethod
    def calculate_stats(
        cls,
        listings: List[ProductListing],
        platform: Optional[str] = None,
        error: Optional[str] = None,
        fallback_used: bool = False,
    ) -> ScrapeResult:
        """Calculate statistical metrics (min, max, mean, median) from a list of ProductListings.

        Args:
            listings: List of parsed ProductListing objects.
            platform: Platform name for the result.
            error: Optional error message if any step failed.
            fallback_used: Whether fallback strategy was triggered.

        Returns:
            ScrapeResult containing statistical summaries and listings.
        """
        plat = platform or cls.platform_name
        valid_prices = [item.price for item in listings if item.price is not None and not math.isnan(item.price)]

        if not valid_prices:
            return ScrapeResult(
                platform=plat,
                lowest_price=0.0,
                highest_price=0.0,
                average_price=0.0,
                median_price=0.0,
                sample_count=0,
                top_listings=listings,
                error=error,
                fallback_used=fallback_used,
            )

        lowest = float(min(valid_prices))
        highest = float(max(valid_prices))
        avg = float(round(statistics.mean(valid_prices), 2))
        med = float(round(statistics.median(valid_prices), 2))

        return ScrapeResult(
            platform=plat,
            lowest_price=lowest,
            highest_price=highest,
            average_price=avg,
            median_price=med,
            sample_count=len(valid_prices),
            top_listings=listings,
            error=error,
            fallback_used=fallback_used,
        )
