import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export type LLMProvider = "openai" | "anthropic" | "openrouter" | "mock";

export interface SettingsState {
  provider: LLMProvider;
  apiKey: string;
  model: string;
  isSettingsOpen: boolean;
  
  // Actions
  setProvider: (provider: LLMProvider) => void;
  setApiKey: (apiKey: string) => void;
  setModel: (model: string) => void;
  setSettingsOpen: (open: boolean) => void;
  saveSettings: (settings: { provider: LLMProvider; apiKey: string; model: string }) => void;
  clearKey: () => void;
  
  // Helpers
  isConfigured: () => boolean;
}

export const DEFAULT_MODELS: Record<LLMProvider, string> = {
  openai: "gpt-4o-mini",
  anthropic: "claude-3-5-sonnet-20241022",
  openrouter: "anthropic/claude-3.5-sonnet",
  mock: "mock-v1",
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      provider: "mock",
      apiKey: "",
      model: DEFAULT_MODELS.mock,
      isSettingsOpen: false,

      setProvider: (provider) =>
        set((state) => ({
          provider,
          // Reset model to default for provider if current model isn't customized or provider changed
          model: DEFAULT_MODELS[provider] || state.model,
        })),

      setApiKey: (apiKey) => set({ apiKey }),

      setModel: (model) => set({ model }),

      setSettingsOpen: (isSettingsOpen) => set({ isSettingsOpen }),

      saveSettings: ({ provider, apiKey, model }) =>
        set({
          provider,
          apiKey,
          model: model || DEFAULT_MODELS[provider],
        }),

      clearKey: () =>
        set({
          apiKey: "",
        }),

      isConfigured: () => {
        const { provider, apiKey } = get();
        if (provider === "mock") return true;
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
      }),
    }
  )
);
