from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class ItemDescription(BaseModel):
    """Structured description extracted from item input."""
    name: str = Field(..., description="Name or title of the item")
    condition: str = Field(..., description="Condition of the item (e.g. New, Like New, Good, Fair, Poor)")
    estimated_retail_price: Optional[float] = Field(
        None, description="Estimated retail or market price if identifiable"
    )
    key_features: List[str] = Field(
        default_factory=list, description="Key specifications, attributes, or distinguishing features"
    )
    summary: Optional[str] = Field(
        None, description="Short summary/overview of the item description"
    )
    category: Optional[str] = Field(
        None, description="Primary category of the item (e.g. Electronics, Fashion, Home)"
    )


class ItemParseRequest(BaseModel):
    """Request payload to parse an item from text and/or image."""
    text: Optional[str] = Field(None, description="Unstructured item text description")
    image_base64: Optional[str] = Field(
        None, description="Base64-encoded image string (with or without data URI prefix)"
    )

    @model_validator(mode="after")
    def check_at_least_one_input(self) -> "ItemParseRequest":
        if not (self.text and self.text.strip()) and not (self.image_base64 and self.image_base64.strip()):
            raise ValueError("Either 'text' or 'image_base64' must be provided.")
        return self


class ItemParseResponse(BaseModel):
    """Response containing parsed item description and execution metadata."""
    status: str = Field("success", description="Status of the parsing operation")
    item: ItemDescription = Field(..., description="Extracted structured item details")
    provider_used: Optional[str] = Field(None, description="LLM provider used for parsing")
    model_used: Optional[str] = Field(None, description="LLM model used for parsing")
