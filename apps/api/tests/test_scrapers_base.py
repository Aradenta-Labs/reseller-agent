"""Unit tests for BaseScraper models, IDR price parsing, and statistics calculation."""

import pytest
from src.scrapers.base import BaseScraper, ProductListing, ScrapeResult


class DummyScraper(BaseScraper):
    platform_name = "DummyPlatform"

    async def scrape(self, search_term: str, max_results: int = 10) -> ScrapeResult:
        listings = [
            ProductListing(
                title=f"{search_term} item 1",
                price=100000.0,
                url="https://example.com/1",
                platform=self.platform_name,
                condition="Baru",
                location="Jakarta",
                raw_price="Rp 100.000",
            ),
            ProductListing(
                title=f"{search_term} item 2",
                price=200000.0,
                url="https://example.com/2",
                platform=self.platform_name,
                condition="Bekas",
                location="Bandung",
                raw_price="Rp 200.000",
            ),
        ]
        return self.calculate_stats(listings[:max_results])


def test_product_listing_model():
    listing = ProductListing(
        title="Sony WH-1000XM5 Headphone",
        price=4500000.0,
        url="https://tokopedia.com/item/123",
        platform="Tokopedia",
        condition="Baru",
        location="Jakarta Barat",
        raw_price="Rp 4.500.000",
    )
    assert listing.title == "Sony WH-1000XM5 Headphone"
    assert listing.price == 4500000.0
    assert listing.url == "https://tokopedia.com/item/123"
    assert listing.platform == "Tokopedia"
    assert listing.condition == "Baru"
    assert listing.location == "Jakarta Barat"
    assert listing.raw_price == "Rp 4.500.000"


def test_product_listing_optional_fields():
    listing = ProductListing(
        title="Keyboard Mechanical",
        price=350000.0,
        platform="Shopee",
    )
    assert listing.title == "Keyboard Mechanical"
    assert listing.price == 350000.0
    assert listing.platform == "Shopee"
    assert listing.url is None
    assert listing.condition is None
    assert listing.location is None
    assert listing.raw_price is None


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Rp 1.500.000", 1500000.0),
        ("Rp. 1.500.000", 1500000.0),
        ("RP 1500000", 1500000.0),
        ("Rp1.500.000", 1500000.0),
        ("1,500,000", 1500000.0),
        ("1.5jt", 1500000.0),
        ("1,5 jt", 1500000.0),
        ("1.5 juta", 1500000.0),
        ("2jt", 2000000.0),
        ("0.5 jt", 500000.0),
        ("1500k", 1500000.0),
        ("1.500k", 1500000.0),
        ("150 rb", 150000.0),
        ("150ribu", 150000.0),
        ("Gratis", 0.0),
        ("Free", 0.0),
        ("cuma-cuma", 0.0),
        ("Rp 1.500.000 - Rp 2.000.000", 1500000.0),
        ("50.000", 50000.0),
        ("5.000", 5000.0),
        ("1.2 miliar", 1200000000.0),
        (None, None),
        ("", None),
        ("invalid text without numbers", None),
    ],
)
def test_clean_idr_price(raw, expected):
    result = BaseScraper.clean_idr_price(raw)
    assert result == expected


def test_calculate_stats_empty():
    res = BaseScraper.calculate_stats([], platform="Tokopedia")
    assert res.platform == "Tokopedia"
    assert res.sample_count == 0
    assert res.lowest_price == 0.0
    assert res.highest_price == 0.0
    assert res.average_price == 0.0
    assert res.median_price == 0.0
    assert res.top_listings == []


def test_calculate_stats_populated():
    listings = [
        ProductListing(title="Item 1", price=100000.0, platform="Tokopedia"),
        ProductListing(title="Item 2", price=200000.0, platform="Tokopedia"),
        ProductListing(title="Item 3", price=300000.0, platform="Tokopedia"),
    ]
    res = BaseScraper.calculate_stats(listings, platform="Tokopedia")
    assert res.platform == "Tokopedia"
    assert res.sample_count == 3
    assert res.lowest_price == 100000.0
    assert res.highest_price == 300000.0
    assert res.average_price == 200000.0
    assert res.median_price == 200000.0
    assert len(res.top_listings) == 3


def test_dummy_scraper_async():
    import asyncio
    scraper = DummyScraper()
    result = asyncio.run(scraper.scrape("MacBook", max_results=5))
    assert isinstance(result, ScrapeResult)
    assert result.platform == "DummyPlatform"
    assert result.sample_count == 2
    assert result.lowest_price == 100000.0
    assert result.highest_price == 200000.0
    assert result.average_price == 150000.0
    assert result.median_price == 150000.0
    assert len(result.top_listings) == 2
