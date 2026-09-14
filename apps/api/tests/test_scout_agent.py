"""Unit and integration tests for Market Scout Agent service and FastAPI endpoints."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app
from src.models.auth import BYOKCredentials
from src.models.item import ItemDescription
from src.models.scout import MarketScoutReport, ScoutQueryFormulation
from src.scrapers.base import ProductListing, ScrapeResult
from src.services.scout import MarketScoutService

client = TestClient(app)


# --- Market Scout Service Unit Tests ---

def test_heuristic_query_formulation():
    """Verify heuristic cleaner strips filler words, conditions, and extra spaces."""
    service = MarketScoutService()
    
    # Test 1: Indonesian listing with condition and filler words
    raw1 = "Dijual MacBook Air M1 2020 8GB 256GB kondisi mulus banget pemakaian 6 bulan"
    clean1 = service.formulate_search_query(raw_text=raw1)
    assert "mulus" not in clean1.lower()
    assert "kondisi" not in clean1.lower()
    assert "dijual" not in clean1.lower()
    assert "MacBook" in clean1
    assert "M1" in clean1

    # Test 2: ItemDescription model
    item = ItemDescription(
        name="Apple iPhone 13 Pro 128GB Sierra Blue Bekas Fullset",
        condition="Used - Good",
        key_features=["128GB Storage", "Sierra Blue"],
    )
    clean2 = service.formulate_search_query(item=item)
    assert "bekas" not in clean2.lower()
    assert "fullset" not in clean2.lower()
    assert "iPhone" in clean2
    assert "13" in clean2


def test_aggregate_market_report():
    """Verify cross-platform mathematical aggregations (min, max, mean, median, total)."""
    service = MarketScoutService()

    tokped_res = ScrapeResult(
        platform="Tokopedia",
        lowest_price=10_000_000.0,
        highest_price=12_000_000.0,
        average_price=11_000_000.0,
        median_price=11_000_000.0,
        sample_count=2,
        top_listings=[
            ProductListing(title="Item A", price=10_000_000.0, platform="Tokopedia"),
            ProductListing(title="Item B", price=12_000_000.0, platform="Tokopedia"),
        ],
    )
    shopee_res = ScrapeResult(
        platform="Shopee",
        lowest_price=9_500_000.0,
        highest_price=11_500_000.0,
        average_price=10_500_000.0,
        median_price=10_500_000.0,
        sample_count=2,
        top_listings=[
            ProductListing(title="Item C", price=9_500_000.0, platform="Shopee"),
            ProductListing(title="Item D", price=11_500_000.0, platform="Shopee"),
        ],
    )

    platform_results = {"tokopedia": tokped_res, "shopee": shopee_res}
    report = service.aggregate_market_report(
        item="MacBook Air M1",
        search_query_used="MacBook Air M1",
        platform_results=platform_results,
    )

    assert isinstance(report, MarketScoutReport)
    assert report.total_listings_found == 4
    assert report.overall_lowest_price == 9_500_000.0
    assert report.overall_highest_price == 12_000_000.0
    assert report.overall_average_price == 10_750_000.0
    assert report.overall_median_price == 10_750_000.0
    assert report.best_platform_recommendation == "Shopee"
    assert report.recommended_price_range is not None
    assert report.summary_insights is not None


def test_generate_mock_results():
    """Verify deterministic mock results generator outputs realistic data structure."""
    service = MarketScoutService()
    results = service.generate_mock_results("iPhone 13 128GB")

    assert "tokopedia" in results
    assert "shopee" in results
    assert "facebook" in results

    assert results["tokopedia"].sample_count == 3
    assert results["tokopedia"].lowest_price > 0
    assert len(results["tokopedia"].top_listings) == 3


@pytest.mark.asyncio
async def test_run_scout_in_mock_mode():
    """Verify run_scout executes smoothly in mock mode without opening browser."""
    service = MarketScoutService()
    report = await service.run_scout(
        raw_text="Sony WH-1000XM4 Noise Cancelling",
        mock=True,
    )

    assert report.total_listings_found > 0
    assert report.overall_lowest_price > 0
    assert report.overall_highest_price >= report.overall_lowest_price
    assert report.best_platform_recommendation is not None


# --- API Endpoint Tests ---

def test_scout_search_endpoint_with_direct_query():
    """Test POST /api/scout/search with direct query in mock mode."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "mock_key",
    }
    payload = {
        "query": "iPhone 13 Pro 128GB",
        "mock": True,
    }
    response = client.post("/api/scout/search", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["search_query_used"] == "iPhone 13 Pro 128GB"
    assert data["total_listings_found"] > 0
    assert data["overall_lowest_price"] > 0
    assert "tokopedia" in data["platform_results"]
    assert "shopee" in data["platform_results"]


def test_scout_search_endpoint_with_item_description():
    """Test POST /api/scout/search with ItemDescription payload."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "mock_key",
    }
    payload = {
        "item": {
            "name": "Apple MacBook Air M1 2020 8GB 256GB Space Grey",
            "condition": "Used - Good",
            "key_features": ["M1 Chip", "8GB RAM", "256GB SSD"],
        },
        "mock": True,
    }
    response = client.post("/api/scout/search", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["total_listings_found"] > 0
    assert data["overall_lowest_price"] > 0
    assert isinstance(data["item"], dict)
    assert data["item"]["name"] == "Apple MacBook Air M1 2020 8GB 256GB Space Grey"


def test_scout_search_endpoint_validation_error():
    """Test POST /api/scout/search returns 422 on empty request."""
    response = client.post("/api/scout/search", json={})
    assert response.status_code == 422


def test_analyze_endpoint_e2e_mock():
    """Test POST /api/analyze end-to-end (Vision/Text Parser -> Market Scout Agent)."""
    headers = {
        "X-LLM-Provider": "mock",
        "X-API-Key": "mock_key",
        "X-LLM-Model": "mock-model-v1",
    }
    payload = {
        "text": "WTS iPhone 13 Pro 128GB Sierra Blue mulus 99% fullset original",
        "mock": True,
    }
    response = client.post("/api/analyze", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["provider_used"] == "mock"

    # Verify Stage 1: Parsed Item
    parsed = data["parsed_item"]
    assert "iPhone 13 Pro" in parsed["name"]
    assert parsed["condition"]

    # Verify Stage 2: Market Scout Report
    report = data["scout_report"]
    assert report["total_listings_found"] > 0
    assert report["overall_lowest_price"] > 0
    assert report["overall_highest_price"] >= report["overall_lowest_price"]
    assert report["best_platform_recommendation"]
    assert report["summary_insights"]
