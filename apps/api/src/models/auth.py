from typing import Optional
from fastapi import Header, HTTPException, status
from pydantic import BaseModel, Field


class BYOKCredentials(BaseModel):
    """BYOK (Bring Your Own Key) authentication container."""
    provider: str = Field(..., description="LLM Provider (e.g., 'openai', 'anthropic', 'custom_openai', 'custom_anthropic', 'openrouter', 'groq', 'mock')")
    api_key: Optional[str] = Field(None, description="User's API key for the selected provider")
    model: Optional[str] = Field(None, description="Custom model name or override")
    base_url: Optional[str] = Field(None, description="Custom endpoint Base URL for OpenAI/Anthropic compatible gateways (e.g., vLLM, Ollama, LM Studio, OneAPI, LiteLLM proxy)")


def get_byok_credentials(
    x_llm_provider: Optional[str] = Header(None, alias="X-LLM-Provider"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_llm_model: Optional[str] = Header(None, alias="X-LLM-Model"),
    x_llm_base_url: Optional[str] = Header(None, alias="X-LLM-Base-URL"),
) -> BYOKCredentials:
    """Dependency to extract BYOK headers from incoming requests."""
    provider = (x_llm_provider or "").strip().lower()
    
    # If no provider is given, allow fallback/mock provider if no key, or raise error
    if not provider:
        # Default to mock or raise 400 if strictly required
        provider = "mock"
    
    return BYOKCredentials(
        provider=provider,
        api_key=x_api_key.strip() if x_api_key else None,
        model=x_llm_model.strip() if x_llm_model else None,
        base_url=x_llm_base_url.strip() if x_llm_base_url else None,
    )
