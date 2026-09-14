"""Pydantic request and response schemas for multi-agent swarm orchestration."""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, model_validator

from src.models.item import ItemDescription


class OrchestrateRequest(BaseModel):
    """Request payload to initiate full 5-agent swarm orchestration."""

    user_input: Optional[str] = Field(
        None, description="Raw query or prompt from the user"
    )
    item_description: Optional[Union[ItemDescription, Dict[str, Any], str]] = Field(
        None, description="Pre-parsed ItemDescription, dictionary, or raw description text"
    )
    text: Optional[str] = Field(
        None, description="Convenience field for unstructured item text"
    )
    image_base64: Optional[str] = Field(
        None, description="Base64-encoded item image string for vision parsing"
    )
    capital_cost: Optional[float] = Field(
        None, description="Capital acquisition cost paid/intended for the item in IDR", ge=0.0
    )
    mock: bool = Field(
        False, description="Whether to run scraping and search tools in simulated mock mode"
    )
    platforms: Optional[List[str]] = Field(
        None, description="Target marketplaces for Agent 1 (Tokopedia, Shopee, Facebook Marketplace)"
    )

    @model_validator(mode="after")
    def validate_inputs(self) -> "OrchestrateRequest":
        has_input = (
            (self.user_input and self.user_input.strip())
            or (self.text and self.text.strip())
            or self.item_description
            or (self.image_base64 and self.image_base64.strip())
        )
        if not has_input:
            raise ValueError(
                "At least one of 'user_input', 'item_description', 'text', or 'image_base64' must be provided."
            )
        return self


class AgentLog(BaseModel):
    """Execution log for an agent step."""

    agent: str = Field(..., description="Agent name identifier (e.g. 'scout', 'analyst', 'pricing', 'chief', 'customer')")
    status: str = Field("completed", description="Execution status: running, completed, failed, skipped")
    message: str = Field(..., description="Summary message or status description")
    timestamp: Optional[str] = Field(None, description="ISO timestamp")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional extra debug metadata")


class OrchestrateResponse(BaseModel):
    """Final synthesized response containing results from all 5 agents."""

    status: str = Field("success", description="Overall orchestration status")
    user_input: str = Field("", description="Original user input query")
    item_description: Union[ItemDescription, Dict[str, Any], str] = Field(
        ..., description="Resolved item description"
    )
    capital_cost: Optional[float] = Field(
        None, description="User capital acquisition cost"
    )
    market_prices: List[Dict[str, Any]] = Field(
        default_factory=list, description="Scraped marketplace listings from Agent 1 (Market Scout)"
    )
    scout_summary: Optional[Dict[str, Any]] = Field(
        None, description="Aggregated market statistics from Agent 1"
    )
    trend_analysis: str = Field(
        "", description="Trend, velocity, and seasonality insights from Agent 2 (Trend Analyst)"
    )
    pricing_strategy: Dict[str, Any] = Field(
        default_factory=dict, description="Pricing tiers and margin calculations from Agent 3 (Pricing Strategist)"
    )
    final_strategy: str = Field(
        "", description="Master resale strategy and listing recommendations from Agent 4 (Chief Strategist)"
    )
    customer_verdict: str = Field(
        "PASS", description="Skeptical customer persona verdict: 'BUY' or 'PASS'"
    )
    errors: List[str] = Field(
        default_factory=list, description="Errors or fallback warnings during orchestration"
    )
    agent_logs: List[AgentLog] = Field(
        default_factory=list, description="Step-by-step agent logs"
    )
    provider_used: Optional[str] = Field(
        None, description="LLM provider used for agent execution"
    )
    model_used: Optional[str] = Field(
        None, description="LLM model used for agent execution"
    )
