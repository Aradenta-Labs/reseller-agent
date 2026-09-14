"""Tokopedia marketplace scraper using Playwright with stealth settings and fallback heuristics."""

import asyncio
import json
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


class TokopediaScraper(BaseScraper):
    """Scraper implementation for Tokopedia marketplace."""

    platform_name: str = "Tokopedia"
    base_url: str = "https://www.tokopedia.com"

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
        """Construct the search URL for Tokopedia."""
        return f"{self.base_url}/search?q={quote_plus(search_term)}"

    async def scrape(self, search_term: str, max_results: int = 10) -> ScrapeResult:
        """Scrape Tokopedia for product listings using Playwright and fallback parsers.

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
                        "Sec-Ch-Ua-Mobile": "?0",
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
                    # Wait for product grid elements or fallback timeout
                    try:
                        await page.wait_for_selector(
                            '[data-testid="divSRPContentProducts"], [data-testid="spnSRPProdName"], .prd_container-card',
                            timeout=5000,
                        )
                    except Exception:
                        pass

                    # Human-like interaction: mouse movement and scroll delays
                    await self.simulate_human_interaction(page)

                    html_content = await page.content()
                    listings = self.parse_html(html_content, max_results=max_results)
                finally:
                    await context.close()
                    await browser.close()

        except Exception as e:
            logger.warning("Tokopedia direct scraping encountered an error: %s", str(e))
            error_msg = f"Playwright scraping failed: {str(e)}"

        # Step 2: Fallback Chain - Query Tavily / Serper site:tokopedia.com if blocked or 0 listings
        if not listings:
            try:
                logger.info("Attempting search fallback for Tokopedia with term: %s", search_term)
                search_tool = SearchTool()
                fallback_query = f"site:tokopedia.com {search_term} harga"
                findings = await search_tool.search(query=fallback_query, max_results=max_results)

                if findings and findings.results:
                    for item in findings.results:
                        price_match = self.clean_idr_price(item.snippet or item.title)
                        if price_match and price_match > 1000:
                            listings.append(
                                ProductListing(
                                    title=item.title.replace(" - Tokopedia", "").replace(" | Tokopedia", "").strip(),
                                    price=price_match,
                                    url=item.url if "tokopedia.com" in item.url else f"https://www.tokopedia.com/search?q={quote_plus(search_term)}",
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
                logger.warning("Search fallback for Tokopedia failed: %s", str(fe))

        if not listings:
            if not error_msg:
                error_msg = "No product listings found on Tokopedia."
            return self.calculate_stats([], error=error_msg, fallback_used=fallback_used)

        return self.calculate_stats(listings[:max_results], error=error_msg, fallback_used=fallback_used)

    def parse_html(self, html_content: str, max_results: int = 10) -> List[ProductListing]:
        """Extract product listings from raw Tokopedia HTML using multiple heuristic strategies."""
        if not html_content:
            return []

        listings: List[ProductListing] = []
        soup = BeautifulSoup(html_content, "html.parser")

        # Strategy 1: Look for data-testid product cards / container
        card_selectors = [
            'div[data-testid="divProductWrapper"]',
            'div[data-testid="master-product-card"]',
            'div[data-testid="divSRPContentProducts"] div.pcv3__container',
            'div.prd_container-card',
            'div.css-bk6tzz',
            'div.css-1asz3by',
        ]

        found_cards = soup.select(', '.join(card_selectors))
        if found_cards:
            seen_titles = set()
            for card in found_cards:
                listing = self._extract_from_card(card)
                if listing and listing.title not in seen_titles:
                    seen_titles.add(listing.title)
                    listings.append(listing)
                    if len(listings) >= max_results:
                        return listings

        # Strategy 2: Look for JSON-LD structured data (Product / ItemList)
        if not listings:
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string or "{}")
                    if isinstance(data, list):
                        items = data
                    elif isinstance(data, dict):
                        items = data.get("itemListElement", [data])
                    else:
                        items = []

                    for item in items:
                        prod = item.get("item", item) if isinstance(item, dict) else {}
                        name = prod.get("name")
                        offers = prod.get("offers", {})
                        raw_p = offers.get("price") or offers.get("lowPrice")
                        if name and raw_p:
                            price_val = self.clean_idr_price(str(raw_p))
                            if price_val:
                                listings.append(
                                    ProductListing(
                                        title=name.strip(),
                                        price=price_val,
                                        url=prod.get("url") or offers.get("url"),
                                        platform=self.platform_name,
                                        condition="Baru" if "NewCondition" in str(offers.get("itemCondition", "")) else "Bekas",
                                        raw_price=str(raw_p),
                                    )
                                )
                                if len(listings) >= max_results:
                                    return listings
                except Exception:
                    continue

        # Strategy 3: Heuristic scan for link tags wrapping title + price text
        if not listings:
            links = soup.find_all("a", href=True)
            for link in links:
                href = link.get("href", "")
                text = link.get_text(separator=" ", strip=True)
                if ("tokopedia.com/" in href or href.startswith("/")) and ("Rp" in text or "rp" in text.lower()):
                    # Attempt to extract title and price
                    lines = [ln.strip() for ln in link.stripped_strings if ln.strip()]
                    title = None
                    price_val = None
                    raw_price = None
                    loc = None

                    for line in lines:
                        if "Rp" in line or "rp" in line.lower():
                            parsed = self.clean_idr_price(line)
                            if parsed and parsed > 500:
                                price_val = parsed
                                raw_price = line
                        elif len(line) > 5 and not title and not line.startswith("Rp"):
                            title = line

                    if title and price_val:
                        full_url = href if href.startswith("http") else urljoin(self.base_url, href)
                        listings.append(
                            ProductListing(
                                title=title,
                                price=price_val,
                                url=full_url,
                                platform=self.platform_name,
                                raw_price=raw_price,
                            )
                        )
                        if len(listings) >= max_results:
                            break

        return listings

    def _extract_from_card(self, card) -> Optional[ProductListing]:
        """Extract a ProductListing from a single Tokopedia HTML card element."""
        # 1. Title
        title_el = (
            card.select_one('[data-testid="spnSRPProdName"]')
            or card.select_one('.prd_link-product-name')
            or card.select_one('div[class*="product-name"]')
            or card.select_one('span[class*="title"]')
            or card.select_one('h3')
            or card.select_one('h2')
        )
        title = title_el.get_text(strip=True) if title_el else None

        # 2. Price
        price_el = (
            card.select_one('[data-testid="spnSRPProdPrice"]')
            or card.select_one('.prd_link-product-price')
            or card.select_one('div[class*="product-price"]')
            or card.select_one('span[class*="price"]')
        )
        raw_price = price_el.get_text(strip=True) if price_el else None
        if not raw_price:
            # Look inside text for Rp
            text_match = re.search(r"Rp\s?[\d.,]+", card.get_text())
            if text_match:
                raw_price = text_match.group(0)

        price_val = self.clean_idr_price(raw_price) if raw_price else None

        if not title or price_val is None:
            return None

        # 3. URL
        link_el = card if card.name == "a" else card.select_one("a[href]")
        href = link_el.get("href") if link_el else None
        full_url = None
        if href:
            full_url = href if href.startswith("http") else urljoin(self.base_url, href)

        # 4. Location
        loc_el = (
            card.select_one('[data-testid="spnSRPProdTabShopLoc"]')
            or card.select_one('.prd_link-shop-loc')
            or card.select_one('span[class*="location"]')
            or card.select_one('span[class*="shop-location"]')
        )
        location = loc_el.get_text(strip=True) if loc_el else None

        # 5. Condition (if indicated)
        card_text = card.get_text().lower()
        condition = None
        if "bekas" in card_text or "second" in card_text or "preloved" in card_text:
            condition = "Bekas"
        elif "baru" in card_text or "new" in card_text:
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
