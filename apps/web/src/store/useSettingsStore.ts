import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type LLMProvider =
  | "openai"
  | "anthropic"
  | "custom_openai"
  | "custom_anthropic"
  | "openrouter"
  | "mock";

export interface SettingsState {
  provider: LLMProvider;
  apiKey: string;
  model: string;
  baseUrl: string;
  isSettingsOpen: boolean;
  
  // Actions
  setProvider: (provider: LLMProvider) => void;
  setApiKey: (apiKey: string) => void;
  setModel: (model: string) => void;
  setBaseUrl: (baseUrl: string) => void;
  setSettingsOpen: (open: boolean) => void;
  saveSettings: (settings: { provider: LLMProvider; apiKey: string; model: string; baseUrl?: string }) => void;
  clearKey: () => void;
  
  // Helpers
  isConfigured: () => boolean;
}

export const DEFAULT_MODELS: Record<LLMProvider, string> = {
  openai: "gpt-4o-mini",
  anthropic: "claude-3-5-sonnet-20241022",
  custom_openai: "gpt-4o-mini",
  custom_anthropic: "claude-3-5-sonnet-20241022",
  openrouter: "anthropic/claude-3.5-sonnet",
  mock: "mock-v1",
};

export const DEFAULT_BASE_URLS: Record<string, string> = {
  custom_openai: "http://localhost:11434/v1",
  custom_anthropic: "http://localhost:8080",
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      provider: "mock",
      apiKey: "",
      model: DEFAULT_MODELS.mock,
      baseUrl: "",
      isSettingsOpen: false,

      setProvider: (provider) =>
        set((state) => ({
          provider,
          // Reset model to default for provider if current model isn't customized or provider changed
          model: DEFAULT_MODELS[provider] || state.model,
          baseUrl: DEFAULT_BASE_URLS[provider] || state.baseUrl,
        })),

      setApiKey: (apiKey) => set({ apiKey }),

      setModel: (model) => set({ model }),

      setBaseUrl: (baseUrl) => set({ baseUrl }),

      setSettingsOpen: (isSettingsOpen) => set({ isSettingsOpen }),

      saveSettings: ({ provider, apiKey, model, baseUrl }) =>
        set({
          provider,
          apiKey,
          model: model || DEFAULT_MODELS[provider],
          baseUrl: baseUrl !== undefined ? baseUrl : (DEFAULT_BASE_URLS[provider] || ""),
        }),

      clearKey: () =>
        set({
          apiKey: "",
        }),

      isConfigured: () => {
        const { provider, apiKey, baseUrl } = get();
        if (provider === "mock") return true;
        if (provider === "custom_openai" || provider === "custom_anthropic") {
          // Custom providers might use local endpoints without strict key or with base_url
          return Boolean(baseUrl && baseUrl.trim().length > 0);
        }
        return Boolean(apiKey && apiKey.trim().length > 0);
      },
    }),
    {
      name: "reseller-agent-settings",
      storage: createJSONStorage(() => {
        if (typeof window !== "undefined") {
          return localStorage;
        }
        // Fallback dummy storage for SSR execution
        return {
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {},
        };
      }),
      partialize: (state) => ({
        provider: state.provider,
        apiKey: state.apiKey,
        model: state.model,
        baseUrl: state.baseUrl,
      }),
    }
  )
);
