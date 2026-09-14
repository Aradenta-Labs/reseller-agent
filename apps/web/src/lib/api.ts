import { useSettingsStore, LLMProvider } from "@/store/useSettingsStore";

export interface ItemDescription {
  name: string;
  condition: string;
  estimated_retail_price?: number | null;
  key_features: string[];
  summary?: string | null;
  category?: string | null;
}

export interface ParseItemRequest {
  text?: string;
  image_base64?: string;
}

export interface ParseItemResponse {
  status: string;
  item: ItemDescription;
  provider_used?: string;
  model_used?: string;
  detail?: string;
}

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
  environment: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Extract BYOK headers from current Zustand settings store state
 */
export function getBYOKHeaders() {
  const { provider, apiKey, model } = useSettingsStore.getState();
  return {
    "X-LLM-Provider": provider,
    "X-API-Key": apiKey || "",
    "X-LLM-Model": model || "",
  };
}

/**
 * Health check endpoint call
 */
export async function checkBackendHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/health`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...getBYOKHeaders(),
    },
  });

  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Call FastAPI parse-item endpoint with text/image_base64 and BYOK credentials
 */
export async function parseItem(payload: ParseItemRequest): Promise<ParseItemResponse> {
  const response = await fetch(`${API_BASE_URL}/api/parse-item`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getBYOKHeaders(),
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const errorMessage =
      data?.detail ||
      (typeof data === "string" ? data : `API Error ${response.status}: ${response.statusText}`);
    throw new Error(errorMessage);
  }

  return data as ParseItemResponse;
}
