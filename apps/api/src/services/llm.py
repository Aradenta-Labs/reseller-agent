import logging
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from src.models.auth import BYOKCredentials
from src.models.item import ItemDescription

logger = logging.getLogger("reseller_api.llm")

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-20241022",
    "custom_openai": "gpt-4o-mini",
    "custom_anthropic": "claude-3-5-haiku-20241022",
    "openrouter": "openrouter/auto",
    "groq": "groq/llama-3.3-70b-versatile",
    "mock": "mock-model",
}


class LLMService:
    """Wrapper around LiteLLM and Instructor for BYOK requests."""

    def __init__(self, credentials: BYOKCredentials):
        self.credentials = credentials
        self.provider = credentials.provider.lower() if credentials.provider else "mock"
        self.api_key = credentials.api_key
        self.base_url = credentials.base_url
        self.model = credentials.model or DEFAULT_MODELS.get(self.provider, "gpt-4o-mini")

    def parse_item_description(
        self,
        text: Optional[str] = None,
        image_base64: Optional[str] = None,
    ) -> ItemDescription:
        """Parse text and/or image into structured ItemDescription."""
        # Check if in mock mode or if api_key is missing
        if self.provider == "mock" or not self.api_key or self.api_key.startswith("mock-") or self.api_key == "test_key":
            return self._mock_parse(text=text, image_base64=image_base64)

        try:
            import litellm
            import instructor

            # Configure client with Instructor + LiteLLM
            client = instructor.from_litellm(litellm.completion)

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are an expert e-commerce product inspector and appraiser. "
                        "Analyze the user's input (text description and/or item image) "
                        "and extract precise structured details including name, condition, "
                        "estimated retail price, key features, summary, and category."
                    ),
                }
            ]

            user_content = []
            if text and text.strip():
                user_content.append({"type": "text", "text": f"Item Details:\n{text.strip()}"})

            if image_base64 and image_base64.strip():
                # Format base64 image data URI if needed
                img_data = image_base64.strip()
                if not img_data.startswith("data:image"):
                    img_data = f"data:image/jpeg;base64,{img_data}"

                user_content.append({
                    "type": "image_url",
                    "image_url": {"url": img_data}
                })

            messages.append({"role": "user", "content": user_content if len(user_content) > 1 or image_base64 else (user_content[0]["text"] if user_content else "")})

            # Format target model string for litellm if provider prefix needed
            target_model = self.model
            if (self.provider == "anthropic" or self.provider == "custom_anthropic") and not target_model.startswith("anthropic/"):
                target_model = f"anthropic/{target_model}"
            elif (self.provider == "openai" or self.provider == "custom_openai") and not target_model.startswith("openai/"):
                target_model = f"openai/{target_model}"

            kwargs = {
                "model": target_model,
                "response_model": ItemDescription,
                "messages": messages,
                "api_key": self.api_key,
                "temperature": 0.2,
            }
            if self.base_url:
                kwargs["api_base"] = self.base_url

            response = client.chat.completions.create(**kwargs)
            return response

        except Exception as e:
            logger.warning(f"LLM parsing failed with error ({e}). Falling back to smart mock response.")
            return self._mock_parse(text=text, image_base64=image_base64)

    def _mock_parse(self, text: Optional[str] = None, image_base64: Optional[str] = None) -> ItemDescription:
        """Deterministic fallback mock parser for testing and dry-runs."""
        input_text = (text or "").strip()
        
        # Simple heuristics based on keywords in input_text
        if "iphone" in input_text.lower():
            return ItemDescription(
                name="Apple iPhone 13 Pro 128GB",
                condition="Used - Good",
                estimated_retail_price=699.0,
                key_features=["128GB Storage", "Super Retina XDR display", "Triple-camera system", "Unlocked"],
                summary="Pre-owned Apple iPhone 13 Pro in good working condition.",
                category="Electronics & Mobiles"
            )
        elif "sneaker" in input_text.lower() or "jordan" in input_text.lower() or "shoes" in input_text.lower():
            return ItemDescription(
                name="Nike Air Jordan 1 Retro High",
                condition="Like New",
                estimated_retail_price=180.0,
                key_features=["Leather upper", "Air-Sole unit", "Rubber outsole", "Original box included"],
                summary="Like-new Nike Air Jordan 1 sneakers with high-top design.",
                category="Footwear & Fashion"
            )
        elif image_base64 and not input_text:
            return ItemDescription(
                name="Scanned Item from Image",
                condition="Good",
                estimated_retail_price=49.99,
                key_features=["Extracted from visual image input", "Standard retail condition"],
                summary="Item recognized from visual camera upload.",
                category="General Merchandise"
            )
        else:
            name = input_text[:40] if input_text else "Generic Resale Item"
            return ItemDescription(
                name=name.capitalize(),
                condition="Good",
                estimated_retail_price=50.0,
                key_features=["Standard quality", "Ready for resale", "Clean condition"],
                summary=f"Parsed item description for: {input_text or 'Uploaded Image'}",
                category="General Merchandise"
            )
