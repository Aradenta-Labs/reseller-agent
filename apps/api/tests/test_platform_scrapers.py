"""Comprehensive unit and mock tests for Tokopedia, Shopee, and Facebook Marketplace scrapers."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.scrapers.base import ProductListing, ScrapeResult
from src.scrapers.tokped import TokopediaScraper
from src.scrapers.shopee import ShopeeScraper
from src.scrapers.fb import FacebookMarketplaceScraper
from src.scrapers import scrape_all_platforms


# --- HTML Fixtures ---

TOKPED_HTML_FIXTURE = """
<html>
<body>
    <div data-testid="divSRPContentProducts">
        <div data-testid="divProductWrapper">
            <a href="https://www.tokopedia.com/tokoonline/macbook-air-m1-2020-8-256gb">
                <span data-testid="spnSRPProdName">Apple MacBook Air M1 2020 8GB 256GB Space Grey</span>
                <div data-testid="spnSRPProdPrice">Rp 11.500.000</div>
                <span data-testid="spnSRPProdTabShopLoc">Jakarta Pusat</span>
            </a>
            <div>Kondisi: Bekas</div>
        </div>
        <div data-testid="divProductWrapper">
            <a href="/tokoonline/macbook-pro-m2-16-512gb">
                <span data-testid="spnSRPProdName">Apple MacBook Pro M2 16GB 512GB Silver</span>
                <div data-testid="spnSRPProdPrice">Rp 18.000.000</div>
                <span data-testid="spnSRPProdTabShopLoc">Surabaya</span>
            </a>
            <div>Baru Garansi Resmi</div>
        </div>
    </div>
</body>
</html>
"""

TOKPED_JSON_LD_FIXTURE = """
<html>
<head>
    <script type="application/ld+json">
    [
        {
            "@type": "Product",
            "name": "Sony WH-1000XM5 Black",
            "url": "https://www.tokopedia.com/sony/wh-1000xm5",
            "offers": {
                "@type": "Offer",
                "price": "4500000",
                "itemCondition": "http://schema.org/NewCondition"
            }
        }
    ]
    </script>
</head>
<body></body>
</html>
"""

SHOPEE_HTML_FIXTURE = """
<html>
<body>
    <div class="shopee-search-item-result__item">
        <a href="https://shopee.co.id/Sony-PlayStation-5-PS5-Slim-Disc-Version-i.12345.67890">
            <div data-sqe="name">Sony PlayStation 5 PS5 Slim Disc Version Garansi Resmi Sony Indonesia</div>
            <div data-sqe="price">Rp 8.799.000</div>
            <div data-sqe="location">Kota Jakarta Barat</div>
        </a>
    </div>
    <div data-sqe="item">
        <a href="/Nintendo-Switch-OLED-White-i.54321.98765">
            <div data-sqe="name">Nintendo Switch OLED White Console Baru</div>
            <div data-sqe="price">Rp 4.250.000</div>
            <div data-sqe="location">Kota Bandung</div>
        </a>
    </div>
</body>
</html>
"""

FB_HTML_FIXTURE = """
<html>
<body>
    <div>
        <a href="https://www.facebook.com/marketplace/item/1029384756/?ref=search">
            <div>Rp 1.200.000</div>
            <div>Sepeda Lipat Dahon Bekas Mulus</div>
            <div>Jakarta Selatan, DKI Jakarta</div>
        </a>
        <a href="/marketplace/item/5647382910/?ref=search">
            <div>Rp 500.000</div>
            <div>Monitor LG 24 Inch IPS Bekas</div>
            <div>Tangerang, Banten</div>
        </a>
    </div>
</body>
</html>
"""


# --- Tokopedia Scraper Tests ---

def test_tokped_build_url():
    scraper = TokopediaScraper()
    url = scraper.build_search_url("MacBook Air M1")
    assert url == "https://www.tokopedia.com/search?q=MacBook+Air+M1"


def test_tokped_parse_html():
    scraper = TokopediaScraper()
    listings = scraper.parse_html(TOKPED_HTML_FIXTURE, max_results=5)
    assert len(listings) == 2

    item1 = listings[0]
    assert item1.title == "Apple MacBook Air M1 2020 8GB 256GB Space Grey"
    assert item1.price == 11500000.0
    assert item1.location == "Jakarta Pusat"
    assert item1.condition == "Bekas"
    assert item1.platform == "Tokopedia"
    assert item1.url == "https://www.tokopedia.com/tokoonline/macbook-air-m1-2020-8-256gb"

    item2 = listings[1]
    assert item2.title == "Apple MacBook Pro M2 16GB 512GB Silver"
    assert item2.price == 18000000.0
    assert item2.location == "Surabaya"
    assert item2.condition == "Baru"
    assert item2.url == "https://www.tokopedia.com/tokoonline/macbook-pro-m2-16-512gb"


def test_tokped_parse_json_ld():
    scraper = TokopediaScraper()
    listings = scraper.parse_html(TOKPED_JSON_LD_FIXTURE, max_results=5)
    assert len(listings) == 1
    item = listings[0]
    assert item.title == "Sony WH-1000XM5 Black"
    assert item.price == 4500000.0
    assert item.condition == "Baru"


def test_tokped_scrape_mocked_playwright():
    scraper = TokopediaScraper()

    mock_page = AsyncMock()
    mock_page.content.return_value = TOKPED_HTML_FIXTURE
    mock_page.goto.return_value = None
    mock_page.wait_for_selector.return_value = None
    mock_page.evaluate.return_value = None

    mock_context = AsyncMock()
    mock_context.newPage.return_value = mock_page
    mock_context.close.return_value = None

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_browser.close.return_value = None

    mock_p = AsyncMock()
    mock_p.chromium.launch.return_value = mock_browser

    mock_playwright_ctx = AsyncMock()
    mock_playwright_ctx.__aenter__.return_value = mock_p
    mock_playwright_ctx.__aexit__.return_value = None

    with patch("src.scrapers.tokped.async_playwright", return_value=mock_playwright_ctx):
        result = asyncio.run(scraper.scrape("MacBook", max_results=5))
        assert isinstance(result, ScrapeResult)
        assert result.platform == "Tokopedia"
        assert result.sample_count == 2
        assert result.lowest_price == 11500000.0
        assert result.highest_price == 18000000.0
        assert result.average_price == 14750000.0
        assert result.median_price == 14750000.0
        assert len(result.top_listings) == 2


def test_tokped_scrape_error_fallback():
    scraper = TokopediaScraper()

    with patch("src.scrapers.tokped.async_playwright", side_effect=Exception("Browser launch failed")):
        result = asyncio.run(scraper.scrape("MacBook", max_results=5))
        assert isinstance(result, ScrapeResult)
        assert result.platform == "Tokopedia"
        assert result.sample_count == 0
        assert result.error is not None
        assert "Browser launch failed" in result.error


# --- Shopee Scraper Tests ---

def test_shopee_build_url():
    scraper = ShopeeScraper()
    url = scraper.build_search_url("PlayStation 5")
    assert url == "https://shopee.co.id/search?keyword=PlayStation+5"


def test_shopee_parse_html():
    scraper = ShopeeScraper()
    listings = scraper.parse_html(SHOPEE_HTML_FIXTURE, max_results=5)
    assert len(listings) == 2

    item1 = listings[0]
    assert "PlayStation 5" in item1.title
    assert item1.price == 8799000.0
    assert item1.location == "Kota Jakarta Barat"
    assert item1.platform == "Shopee"
    assert item1.url == "https://shopee.co.id/Sony-PlayStation-5-PS5-Slim-Disc-Version-i.12345.67890"

    item2 = listings[1]
    assert "Nintendo Switch" in item2.title
    assert item2.price == 4250000.0
    assert item2.location == "Kota Bandung"
    assert item2.url == "https://shopee.co.id/Nintendo-Switch-OLED-White-i.54321.98765"


def test_shopee_scrape_mocked_playwright():
    scraper = ShopeeScraper()

    mock_page = AsyncMock()
    mock_page.content.return_value = SHOPEE_HTML_FIXTURE
    mock_page.goto.return_value = None
    mock_page.wait_for_selector.return_value = None
    mock_page.evaluate.return_value = None

    mock_context = AsyncMock()
    mock_context.newPage.return_value = mock_page
    mock_context.close.return_value = None

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_browser.close.return_value = None

    mock_p = AsyncMock()
    mock_p.chromium.launch.return_value = mock_browser

    mock_playwright_ctx = AsyncMock()
    mock_playwright_ctx.__aenter__.return_value = mock_p
    mock_playwright_ctx.__aexit__.return_value = None

    with patch("src.scrapers.shopee.async_playwright", return_value=mock_playwright_ctx):
        result = asyncio.run(scraper.scrape("PS5", max_results=5))
        assert isinstance(result, ScrapeResult)
        assert result.platform == "Shopee"
        assert result.sample_count == 2
        assert result.lowest_price == 4250000.0
        assert result.highest_price == 8799000.0
        assert len(result.top_listings) == 2


def test_shopee_scrape_error_fallback():
    scraper = ShopeeScraper()

    with patch("src.scrapers.shopee.async_playwright", side_effect=Exception("Shopee network timeout")):
        result = asyncio.run(scraper.scrape("PS5", max_results=5))
        assert isinstance(result, ScrapeResult)
        assert result.platform == "Shopee"
        assert result.sample_count == 0
        assert result.error is not None
        assert "Shopee network timeout" in result.error


# --- Facebook Marketplace Scraper Tests ---

def test_fb_build_url():
    scraper = FacebookMarketplaceScraper()
    url = scraper.build_search_url("Sepeda Lipat")
    assert url == "https://www.facebook.com/marketplace/search/?query=Sepeda+Lipat"


def test_fb_parse_html():
    scraper = FacebookMarketplaceScraper()
    listings = scraper.parse_html(FB_HTML_FIXTURE, max_results=5)
    assert len(listings) == 2

    item1 = listings[0]
    assert item1.title == "Sepeda Lipat Dahon Bekas Mulus"
    assert item1.price == 1200000.0
    assert item1.location == "Jakarta Selatan, DKI Jakarta"
    assert item1.platform == "Facebook Marketplace"
    assert item1.condition == "Bekas"
    assert item1.url == "https://www.facebook.com/marketplace/item/1029384756/"

    item2 = listings[1]
    assert item2.title == "Monitor LG 24 Inch IPS Bekas"
    assert item2.price == 500000.0
    assert item2.location == "Tangerang, Banten"
    assert item2.url == "https://www.facebook.com/marketplace/item/5647382910/"


def test_fb_scrape_mocked_playwright():
    scraper = FacebookMarketplaceScraper()

    mock_page = AsyncMock()
    mock_page.content.return_value = FB_HTML_FIXTURE
    mock_page.goto.return_value = None
    mock_page.query_selector.return_value = None
    mock_page.wait_for_selector.return_value = None
    mock_page.evaluate.return_value = None

    mock_context = AsyncMock()
    mock_context.newPage.return_value = mock_page
    mock_context.close.return_value = None

    mock_browser = AsyncMock()
    mock_browser.new_context.return_value = mock_context
    mock_browser.close.return_value = None

    mock_p = AsyncMock()
    mock_p.chromium.launch.return_value = mock_browser

    mock_playwright_ctx = AsyncMock()
    mock_playwright_ctx.__aenter__.return_value = mock_p
    mock_playwright_ctx.__aexit__.return_value = None

    with patch("src.scrapers.fb.async_playwright", return_value=mock_playwright_ctx):
        result = asyncio.run(scraper.scrape("Sepeda", max_results=5))
        assert isinstance(result, ScrapeResult)
        assert result.platform == "Facebook Marketplace"
        assert result.sample_count == 2
        assert result.lowest_price == 500000.0
        assert result.highest_price == 1200000.0
        assert len(result.top_listings) == 2


def test_fb_scrape_error_fallback():
    scraper = FacebookMarketplaceScraper()

    with patch("src.scrapers.fb.async_playwright", side_effect=Exception("FB login barrier")):
        result = asyncio.run(scraper.scrape("Sepeda", max_results=5))
        assert isinstance(result, ScrapeResult)
        assert result.platform == "Facebook Marketplace"
        assert result.sample_count == 0
        assert result.error is not None
        assert "FB login barrier" in result.error


# --- Unified scrape_all_platforms Tests ---

def test_scrape_all_platforms_mocked():
    mock_tokped_result = ScrapeResult(
        platform="Tokopedia",
        lowest_price=1000000.0,
        highest_price=2000000.0,
        average_price=1500000.0,
        median_price=1500000.0,
        sample_count=2,
        top_listings=[
            ProductListing(title="Tokped Item 1", price=1000000.0, platform="Tokopedia"),
            ProductListing(title="Tokped Item 2", price=2000000.0, platform="Tokopedia"),
        ],
    )
    mock_shopee_result = ScrapeResult(
        platform="Shopee",
        lowest_price=1200000.0,
        highest_price=1800000.0,
        average_price=1500000.0,
        median_price=1500000.0,
        sample_count=2,
        top_listings=[
            ProductListing(title="Shopee Item 1", price=1200000.0, platform="Shopee"),
            ProductListing(title="Shopee Item 2", price=1800000.0, platform="Shopee"),
        ],
    )
    mock_fb_result = ScrapeResult(
        platform="Facebook Marketplace",
        lowest_price=900000.0,
        highest_price=1400000.0,
        average_price=1150000.0,
        median_price=1150000.0,
        sample_count=2,
        top_listings=[
            ProductListing(title="FB Item 1", price=900000.0, platform="Facebook Marketplace"),
            ProductListing(title="FB Item 2", price=1400000.0, platform="Facebook Marketplace"),
        ],
    )

    with patch.object(TokopediaScraper, "scrape", AsyncMock(return_value=mock_tokped_result)), \
         patch.object(ShopeeScraper, "scrape", AsyncMock(return_value=mock_shopee_result)), \
         patch.object(FacebookMarketplaceScraper, "scrape", AsyncMock(return_value=mock_fb_result)):

        results = asyncio.run(scrape_all_platforms("Laptop Asus", platforms=None, max_results_per_platform=5))

        assert "tokopedia" in results
        assert "shopee" in results
        assert "facebook" in results

        assert results["tokopedia"].sample_count == 2
        assert results["tokopedia"].lowest_price == 1000000.0

        assert results["shopee"].sample_count == 2
        assert results["shopee"].lowest_price == 1200000.0

        assert results["facebook"].sample_count == 2
        assert results["facebook"].lowest_price == 900000.0


def test_scrape_all_platforms_subset_and_error_handling():
    with patch.object(TokopediaScraper, "scrape", AsyncMock(side_effect=RuntimeError("Scraper crash"))):
        results = asyncio.run(scrape_all_platforms("iPhone 13", platforms=["tokopedia"], fallback_on_error=True))

        assert "tokopedia" in results
        assert results["tokopedia"].sample_count == 0
        assert results["tokopedia"].error is not None
        assert "Scraper crash" in results["tokopedia"].error
