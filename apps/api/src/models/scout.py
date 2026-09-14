"""Data models for Market Scout Agent and aggregated market intelligence."""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator

from src.models.item import ItemDescription
from src.scrapers.base import ScrapeResult


class ScoutQueryFormulation(BaseModel):
    """Structured LLM output for formulated e-commerce search query."""

    search_query: str = Field(..., description="Targeted keywords for marketplace search (brand, model, spec)")
    reasoning: Optional[str] = Field(None, description="Brief explanation of keyword selection")


class MarketScoutReport(BaseModel):
    """Aggregated market intelligence report from Market Scout Agent across marketplaces."""

    item: Union[ItemDescription, str] = Field(
        ..., description="ItemDescription object or item name under investigation"
    )
    search_query_used: str = Field(
        ..., description="Optimized search query string executed on marketplace scrapers"
    )
    platform_results: Dict[str, ScrapeResult] = Field(
        default_factory=dict, description="Scrape results mapped by platform identifier"
    )
    overall_lowest_price: float = Field(
        0.0, description="Minimum price found across all valid listings on all platforms in IDR"
    )
    overall_highest_price: float = Field(
        0.0, description="Maximum price found across all valid listings on all platforms in IDR"
    )
    overall_average_price: float = Field(
        0.0, description="Arithmetic mean price across all valid listings on all platforms in IDR"
    )
    overall_median_price: float = Field(
        0.0, description="Median price across all valid listings on all platforms in IDR"
    )
    total_listings_found: int = Field(
        0, description="Total count of valid listings extracted across all platforms"
    )
    best_platform_recommendation: Optional[str] = Field(
        None, description="Platform recommendation based on pricing advantage and market liquidity"
    )
    summary_insights: Optional[str] = Field(
        None, description="Natural language summary and market pricing insights"
    )
    recommended_price_range: Optional[Dict[str, float]] = Field(
        None, description="Suggested buy/sell range (e.g. {'min': float, 'max': float})"
    )


class ScoutSearchRequest(BaseModel):
    """Request payload for the Market Scout search endpoint."""

    query: Optional[str] = Field(None, description="Direct search query string")
    item: Optional[ItemDescription] = Field(None, description="Structured item description")
    text: Optional[str] = Field(None, description="Raw unstructured item description text")
    mock: bool = Field(False, description="Whether to force simulated mock data generation")
    max_results_per_platform: int = Field(10, description="Max listings to extract per platform", ge=1, le=50)
    platforms: Optional[List[str]] = Field(
        None, description="Platforms to query (e.g. ['tokopedia', 'shopee', 'facebook'])"
    )

    @model_validator(mode="after")
    def validate_has_input(self) -> "ScoutSearchRequest":
        if not self.query and not self.item and not (self.text and self.text.strip()):
            raise ValueError("At least one of 'query', 'item', or 'text' must be provided.")
        return self


class AnalyzeRequest(BaseModel):
    """Request payload for comprehensive multi-stage analysis."""

    text: Optional[str] = Field(None, description="Unstructured item text description")
    image_base64: Optional[str] = Field(None, description="Base64-encoded image string")
    mock: bool = Field(False, description="Whether to run scraping in mock/simulation mode")
    max_results_per_platform: int = Field(10, description="Max listings to extract per platform", ge=1, le=50)
    platforms: Optional[List[str]] = Field(
        None, description="Platforms to query (e.g. ['tokopedia', 'shopee', 'facebook'])"
    )

    @model_validator(mode="after")
    def validate_has_input(self) -> "AnalyzeRequest":
        if not (self.text and self.text.strip()) and not (self.image_base64 and self.image_base64.strip()):
            raise ValueError("Either 'text' or 'image_base64' must be provided.")
        return self


class AnalyzeResponse(BaseModel):
    """Response payload for comprehensive multi-stage analysis."""

    status: str = Field("success", description="Status of the analysis operation")
    parsed_item: ItemDescription = Field(..., description="Structured item description extracted by Vision/Parser")
    scout_report: MarketScoutReport = Field(..., description="Market Scout intelligence report")
    provider_used: Optional[str] = Field(None, description="LLM provider used for parsing/reasoning")
    model_used: Optional[str] = Field(None, description="LLM model used for parsing/reasoning")
