"""Facebook Marketplace scraper using Playwright for public listings with stealth and fallback heuristics."""

import asyncio
import logging
import re
from typing import List, Optional
from urllib.parse import quote_plus, urljoin
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.scrapers.base import (
    BaseScraper,
    ProductListing,
    ScrapeResult,
    enforce_scraper_cooldown,
    get_random_fingerprint,
    get_scraper_proxy_config,
)
from src.tools.search import SearchTool

try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None

logger = logging.getLogger(__name__)


class FacebookMarketplaceScraper(BaseScraper):
    """Scraper implementation for public Facebook Marketplace."""

    platform_name: str = "Facebook Marketplace"
    base_url: str = "https://www.facebook.com"

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 15000,
        user_agent: Optional[str] = None,
    ):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self.user_agent = (
            user_agent
            or "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

    def build_search_url(self, search_term: str) -> str:
        """Construct public marketplace search URL."""
        return f"{self.base_url}/marketplace/search/?query={quote_plus(search_term)}"

    async def scrape(self, search_term: str, max_results: int = 10) -> ScrapeResult:
        """Scrape Facebook Marketplace for listings without requiring authentication.

        Args:
            search_term: Query keyword to search.
            max_results: Max listings to extract.

        Returns:
            ScrapeResult containing statistical summary and top listings.
        """
        search_url = self.build_search_url(search_term)
        listings: List[ProductListing] = []
        error_msg: Optional[str] = None
        fallback_used = False

        # Apply rate limiting / cooldown across scrapers
        await enforce_scraper_cooldown()

        # Step 1: Direct Playwright scrape with randomized session fingerprint & proxy
        try:
            fp = get_random_fingerprint()
            proxy_cfg = get_scraper_proxy_config()
            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                f"--window-size={fp['viewport']['width']},{fp['viewport']['height']}",
            ]

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=launch_args,
                    proxy=proxy_cfg,
                )
                context = await browser.new_context(
                    user_agent=self.user_agent or fp["user_agent"],
                    viewport=fp["viewport"],
                    locale=fp.get("locale", "id-ID"),
                    timezone_id=fp.get("timezone_id", "Asia/Jakarta"),
                    extra_http_headers={
                        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Sec-Ch-Ua": '"Chromium";v="124", "Not-A.Brand";v="99", "Google Chrome";v="124"',
                        "Sec-Ch-Ua-Platform": f'"{fp.get("platform", "macOS")}"',
                    },
                )
                page = await context.newPage()

                if stealth_async:
                    await stealth_async(page)
                else:
                    await page.add_init_script(
                        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                    )

                try:
                    await page.goto(search_url, wait_until="domcontentloaded", timeout=self.timeout_ms)

                    # Close generic login dialog / banners if present
                    try:
                        close_btn = await page.query_selector(
                            '[aria-label="Close"], [aria-label="Tutup"], div[role="dialog"] [role="button"]'
                        )
                        if close_btn:
                            await close_btn.click()
                    except Exception:
                        pass

                    # Wait for marketplace feed cards
                    try:
                        await page.wait_for_selector('a[href*="/marketplace/item/"]', timeout=5000)
                    except Exception:
                        pass

                    # Human-like interaction: mouse movements and progressive scrolling
                    await self.simulate_human_interaction(page)

                    html_content = await page.content()
                    listings = self.parse_html(html_content, max_results=max_results)
                finally:
                    await context.close()
                    await browser.close()

        except Exception as e:
            logger.warning("Facebook Marketplace direct scraping encountered an error: %s", str(e))
            error_msg = f"Playwright scraping failed: {str(e)}"

        # Step 2: Fallback Chain - Query Tavily / Serper site:facebook.com/marketplace if blocked or 0 listings
        if not listings:
            try:
                logger.info("Attempting search fallback for FB Marketplace with term: %s", search_term)
                search_tool = SearchTool()
                fallback_query = f"site:facebook.com/marketplace {search_term} harga"
                findings = await search_tool.search(query=fallback_query, max_results=max_results)

                if findings and findings.results:
                    for item in findings.results:
                        price_match = self.clean_idr_price(item.snippet or item.title)
                        if price_match and price_match > 1000:
                            listings.append(
                                ProductListing(
                                    title=item.title.replace(" | Facebook", "").replace(" - Facebook", "").strip(),
                                    price=price_match,
                                    url=item.url if "facebook.com" in item.url else f"https://www.facebook.com/marketplace/search/?query={quote_plus(search_term)}",
                                    platform=self.platform_name,
                                    condition="Bekas",
                                    raw_price=f"Rp {int(price_match):,}".replace(",", "."),
                                )
                            )
                            if len(listings) >= max_results:
                                break
                    if listings:
                        fallback_used = True
                        error_msg = None
            except Exception as fe:
                logger.warning("Search fallback for FB Marketplace failed: %s", str(fe))

        if not listings:
            if not error_msg:
                error_msg = "No product listings found on Facebook Marketplace (login wall or empty search)."
            return self.calculate_stats([], error=error_msg, fallback_used=fallback_used)

        return self.calculate_stats(listings[:max_results], error=error_msg, fallback_used=fallback_used)

    def parse_html(self, html_content: str, max_results: int = 10) -> List[ProductListing]:
        """Extract product listings from raw Facebook Marketplace HTML."""
        if not html_content:
            return []

        listings: List[ProductListing] = []
        soup = BeautifulSoup(html_content, "html.parser")

        # Find all listing links pointing to marketplace item URLs
        item_links = soup.find_all("a", href=re.compile(r"/marketplace/item/\d+"))

        seen_urls = set()
        for link in item_links:
            href = link.get("href", "")
            # Normalize url (strip query params)
            base_href = href.split("?")[0]
            if base_href in seen_urls:
                continue

            listing = self._extract_from_link(link)
            if listing:
                seen_urls.add(base_href)
                listings.append(listing)
                if len(listings) >= max_results:
                    break

        # Fallback if standard item links weren't structured
        if not listings:
            all_links = soup.find_all("a", href=True)
            for link in all_links:
                href = link.get("href", "")
                if "/marketplace/" in href and not any(skip in href for skip in ["/create", "/you", "/category"]):
                    text = link.get_text(separator=" ", strip=True)
                    if "Rp" in text or "rp" in text.lower():
                        listing = self._extract_from_link(link)
                        if listing and listing.url not in seen_urls:
                            seen_urls.add(listing.url)
                            listings.append(listing)
                            if len(listings) >= max_results:
                                break

        return listings

    def _extract_from_link(self, link) -> Optional[ProductListing]:
        """Extract a ProductListing from an individual FB Marketplace listing anchor/card."""
        href = link.get("href", "")
        if not href:
            return None

        clean_href = href.split("?")[0]
        full_url = clean_href if clean_href.startswith("http") else urljoin(self.base_url, clean_href)

        # Extract text elements within the card
        # FB Marketplace card typically has lines:
        # Line 1: Price (e.g. "Rp 1.500.000" or "Gratis")
        # Line 2: Title (e.g. "MacBook Air M1 2020 8/256")
        # Line 3: Location (e.g. "Jakarta, Indonesia")
        lines = [ln.strip() for ln in link.stripped_strings if ln.strip()]
        if not lines:
            return None

        raw_price = None
        price_val = None
        title = None
        location = None

        for idx, line in enumerate(lines):
            # Check if this line is a price
            parsed = self.clean_idr_price(line)
            if parsed is not None and price_val is None:
                # Could be Rp price or 'Gratis'
                price_val = parsed
                raw_price = line
            elif title is None and len(line) > 2 and not line.startswith("Rp"):
                title = line
            elif location is None and len(line) > 2:
                location = line

        # If title wasn't found from strings, try span or image alt text
        if not title:
            img = link.find("img", alt=True)
            if img and img.get("alt"):
                title = img.get("alt")

        if not title or price_val is None:
            return None

        # Determine condition if noted
        condition = None
        full_text = link.get_text().lower()
        if "bekas" in full_text or "second" in full_text or "preloved" in full_text:
            condition = "Bekas"
        elif "baru" in full_text or "brand new" in full_text:
            condition = "Baru"

        return ProductListing(
            title=title,
            price=price_val,
            url=full_url,
            platform=self.platform_name,
            condition=condition,
            location=location,
            raw_price=raw_price,
        )
