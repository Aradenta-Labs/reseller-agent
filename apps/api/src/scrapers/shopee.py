"""Shopee marketplace scraper using Playwright with stealth settings and fallback heuristics."""

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


class ShopeeScraper(BaseScraper):
    """Scraper implementation for Shopee Indonesia."""

    platform_name: str = "Shopee"
    base_url: str = "https://shopee.co.id"

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
            or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

    def build_search_url(self, search_term: str) -> str:
        """Construct search URL for Shopee Indonesia."""
        return f"{self.base_url}/search?keyword={quote_plus(search_term)}"

    async def scrape(self, search_term: str, max_results: int = 10) -> ScrapeResult:
        """Scrape Shopee for product listings using Playwright and fallback parsers.

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
                        "Sec-Ch-Ua-Platform": f'"{fp.get("platform", "Windows")}"',
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
                    # Check for bot challenge or captcha
                    try:
                        await page.wait_for_selector(
                            '.shopee-search-item-result__item, [data-sqe="item"], div.col-xs-2-4',
                            timeout=5000,
                        )
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
            logger.warning("Shopee direct scraping encountered an error: %s", str(e))
            error_msg = f"Playwright scraping failed: {str(e)}"

        # Step 2: Fallback Chain - Query Tavily / Serper site:shopee.co.id if blocked or 0 listings
        if not listings:
            try:
                logger.info("Attempting search fallback for Shopee with term: %s", search_term)
                search_tool = SearchTool()
                fallback_query = f"site:shopee.co.id {search_term} harga"
                findings = await search_tool.search(query=fallback_query, max_results=max_results)

                if findings and findings.results:
                    for item in findings.results:
                        price_match = self.clean_idr_price(item.snippet or item.title)
                        if price_match and price_match > 1000:
                            listings.append(
                                ProductListing(
                                    title=item.title.replace(" - Shopee Indonesia", "").replace(" | Shopee", "").strip(),
                                    price=price_match,
                                    url=item.url if "shopee.co.id" in item.url else f"https://shopee.co.id/search?keyword={quote_plus(search_term)}",
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
                logger.warning("Search fallback for Shopee failed: %s", str(fe))

        if not listings:
            if not error_msg:
                error_msg = "No product listings found on Shopee or bot check encountered."
            return self.calculate_stats([], error=error_msg, fallback_used=fallback_used)

        return self.calculate_stats(listings[:max_results], error=error_msg, fallback_used=fallback_used)

    def parse_html(self, html_content: str, max_results: int = 10) -> List[ProductListing]:
        """Extract product listings from raw Shopee HTML using multiple heuristic strategies."""
        if not html_content:
            return []

        listings: List[ProductListing] = []
        soup = BeautifulSoup(html_content, "html.parser")

        # Strategy 1: Shopee standard grid item cards
        card_selectors = [
            'div.shopee-search-item-result__item',
            'div[data-sqe="item"]',
            'li.shopee-search-item-result__item',
            'div.col-xs-2-4.shopee-search-item-result__item',
            'div.col-xs-2-4',
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

        # Strategy 2: Look for embedded script tags with window.__INITIAL_STATE__ or json-ld
        if not listings:
            json_ld_scripts = soup.find_all("script", type="application/ld+json")
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string or "{}")
                    items = data.get("itemListElement", [data]) if isinstance(data, dict) else (data if isinstance(data, list) else [])
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
                                        raw_price=str(raw_p),
                                    )
                                )
                                if len(listings) >= max_results:
                                    return listings
                except Exception:
                    continue

        # Strategy 3: Link parsing heuristic
        if not listings:
            links = soup.find_all("a", href=True)
            for link in links:
                href = link.get("href", "")
                text = link.get_text(separator=" ", strip=True)
                if ("-i." in href or "/product/" in href or "/search" not in href) and ("Rp" in text or "rp" in text.lower()):
                    lines = [ln.strip() for ln in link.stripped_strings if ln.strip()]
                    title = None
                    price_val = None
                    raw_price = None

                    for line in lines:
                        if "Rp" in line or "rp" in line.lower():
                            parsed = self.clean_idr_price(line)
                            if parsed and parsed > 500:
                                price_val = parsed
                                raw_price = line
                        elif len(line) > 5 and not title and not line.startswith("Rp") and not "terjual" in line.lower():
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
        """Extract a ProductListing from a single Shopee HTML card element."""
        # 1. Title
        title_el = (
            card.select_one('[data-sqe="name"]')
            or card.select_one('div.whitespace-normal')
            or card.select_one('div[class*="truncate"]')
            or card.select_one('div[class*="title"]')
            or card.select_one('div[class*="name"]')
            or card.select_one('span[class*="name"]')
        )
        title = title_el.get_text(strip=True) if title_el else None

        # 2. Price
        price_el = (
            card.select_one('[data-sqe="price"]')
            or card.select_one('div[class*="price"]')
            or card.select_one('span[class*="price"]')
            or card.select_one('div.text-base')
        )
        raw_price = price_el.get_text(strip=True) if price_el else None
        if not raw_price:
            match = re.search(r"Rp\s?[\d.,]+", card.get_text())
            if match:
                raw_price = match.group(0)

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
            card.select_one('[data-sqe="location"]')
            or card.select_one('div[class*="location"]')
            or card.select_one('span[class*="location"]')
            or card.select_one('div.text-xs')
        )
        location = loc_el.get_text(strip=True) if loc_el else None

        # 5. Condition
        card_text = card.get_text().lower()
        condition = None
        if "bekas" in card_text or "second" in card_text:
            condition = "Bekas"
        elif "baru" in card_text:
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
