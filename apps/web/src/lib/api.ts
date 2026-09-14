import { useSettingsStore } from "@/store/useSettingsStore";

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

export interface PriceTierDetail {
  listing_price: number;
  expected_payout?: number;
  net_profit?: number;
  net_margin_percent?: number;
  description?: string;
  platform_fee?: number;
}

export interface PricingStrategy {
  fast_sale?: PriceTierDetail;
  patient_sale?: PriceTierDetail;
  direct_sale?: PriceTierDetail;
  meets_target_margin?: boolean;
  notes?: string;
}

export interface MarketPriceItem {
  platform: string;
  title: string;
  price: number;
  condition?: string;
  location?: string;
  url?: string;
}

export interface ScoutSummary {
  min_price?: number;
  max_price?: number;
  average_price?: number;
  median_price?: number;
  total_listings_found?: number;
  best_platform_for_resale?: string;
}

export interface OrchestrateStreamEvent {
  event: "AGENT_START" | "AGENT_COMPLETE" | "FINAL_RESULT" | "ERROR";
  agent?: string;
  status?: string;
  result?: string;
  error?: string;
  item_description?: ItemDescription | Record<string, unknown> | string;
  market_prices?: MarketPriceItem[];
  scout_summary?: ScoutSummary;
  trend_analysis?: string;
  pricing_strategy?: PricingStrategy;
  final_strategy?: string;
  customer_verdict?: "BUY" | "PASS" | string;
  errors?: string[];
  provider_used?: string;
  model_used?: string;
  user_input?: string;
  capital_cost?: number;
}

export interface OrchestrateRequest {
  user_input?: string;
  text?: string;
  image_base64?: string;
  capital_cost?: number;
  mock?: boolean;
  platforms?: string[];
  item_description?: ItemDescription | Record<string, unknown> | string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Extract BYOK headers from current Zustand settings store state
 */
export function getBYOKHeaders(): Record<string, string> {
  const { provider, apiKey, model, baseUrl } = useSettingsStore.getState();
  const headers: Record<string, string> = {
    "X-LLM-Provider": provider,
    "X-API-Key": apiKey || "",
  };
  if (model) {
    headers["X-LLM-Model"] = model;
  }
  if (baseUrl && (provider === "custom_openai" || provider === "custom_anthropic" || baseUrl.trim())) {
    headers["X-LLM-Base-URL"] = baseUrl.trim();
  }
  return headers;
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

/**
 * Stream multi-agent LangGraph orchestration with SSE events
 */
export async function streamOrchestration(
  request: OrchestrateRequest,
  onEvent: (event: OrchestrateStreamEvent) => void,
  onError: (error: Error) => void,
  onComplete: () => void,
  signal?: AbortSignal
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/orchestrate/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getBYOKHeaders(),
      },
      body: JSON.stringify(request),
      signal,
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => "Unknown stream error");
      throw new Error(`Server stream failed (${response.status}): ${errorText}`);
    }

    if (!response.body) {
      throw new Error("Response body is null, SSE stream unavailable");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      // Keep last incomplete chunk in buffer
      buffer = lines.pop() || "";

      for (const block of lines) {
        const trimmed = block.trim();
        if (!trimmed) continue;

        const dataLine = trimmed
          .split("\n")
          .find((l) => l.startsWith("data: "));

        if (dataLine) {
          try {
            const jsonStr = dataLine.slice(6).trim();
            const parsed = JSON.parse(jsonStr) as OrchestrateStreamEvent;
            onEvent(parsed);
          } catch (pe) {
            console.warn("Failed to parse SSE payload line:", dataLine, pe);
          }
        }
      }
    }

    // Process remainder if any
    if (buffer.trim()) {
      const dataLine = buffer
        .trim()
        .split("\n")
        .find((l) => l.startsWith("data: "));
      if (dataLine) {
        try {
          const jsonStr = dataLine.slice(6).trim();
          const parsed = JSON.parse(jsonStr) as OrchestrateStreamEvent;
          onEvent(parsed);
        } catch {
          // ignore
        }
      }
    }

    onComplete();
  } catch (err: unknown) {
    if (signal?.aborted) {
      // User aborted stream cleanly
      onComplete();
      return;
    }
    const errorObj = err instanceof Error ? err : new Error(String(err));
    onError(errorObj);
  }
}
