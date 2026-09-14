"use client";

import React, { useState } from "react";
import {
  useSettingsStore,
  LLMProvider,
  DEFAULT_MODELS,
} from "@/store/useSettingsStore";
import { checkBackendHealth } from "@/lib/api";
import {
  X,
  KeyRound,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Trash2,
  RefreshCw,
  Cpu,
  Info,
  SlidersHorizontal,
  Globe,
} from "lucide-react";

interface ProviderConfig {
  id: LLMProvider;
  name: string;
  tagline: string;
  defaultModel: string;
  requiresKey: boolean;
  requiresBaseUrl?: boolean;
  popularModels: string[];
}

const PROVIDERS: ProviderConfig[] = [
  {
    id: "openai",
    name: "OpenAI",
    tagline: "Official OpenAI (GPT-4o & GPT-4o-mini)",
    defaultModel: DEFAULT_MODELS.openai,
    requiresKey: true,
    requiresBaseUrl: false,
    popularModels: ["gpt-4o-mini", "gpt-4o", "o3-mini"],
  },
  {
    id: "anthropic",
    name: "Anthropic",
    tagline: "Official Anthropic Claude 3.5 Sonnet & Haiku",
    defaultModel: DEFAULT_MODELS.anthropic,
    requiresKey: true,
    requiresBaseUrl: false,
    popularModels: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
  },
  {
    id: "custom_openai",
    name: "Custom OpenAI-Compatible",
    tagline: "Ollama, vLLM, LM Studio, OneAPI, LiteLLM Proxy, DeepSeek, Groq",
    defaultModel: DEFAULT_MODELS.custom_openai,
    requiresKey: false,
    requiresBaseUrl: true,
    popularModels: [
      "gpt-4o-mini",
      "deepseek-chat",
      "llama-3.3-70b-versatile",
      "qwen2.5-coder-32b",
    ],
  },
  {
    id: "custom_anthropic",
    name: "Custom Anthropic-Compatible",
    tagline: "Self-hosted Claude proxy, Bedrock gateway, or enterprise endpoint",
    defaultModel: DEFAULT_MODELS.custom_anthropic,
    requiresKey: false,
    requiresBaseUrl: true,
    popularModels: [
      "claude-3-5-sonnet-20241022",
      "claude-3-5-haiku-20241022",
    ],
  },
  {
    id: "openrouter",
    name: "OpenRouter",
    tagline: "Multi-model gateway across open-source & proprietary models",
    defaultModel: DEFAULT_MODELS.openrouter,
    requiresKey: true,
    requiresBaseUrl: false,
    popularModels: [
      "anthropic/claude-3.5-sonnet",
      "openai/gpt-4o-mini",
      "deepseek/deepseek-chat",
      "meta-llama/llama-3.3-70b-instruct",
    ],
  },
  {
    id: "mock",
    name: "Mock Mode (Zero Cost)",
    tagline: "Local simulated agent swarm for testing without spending tokens",
    defaultModel: DEFAULT_MODELS.mock,
    requiresKey: false,
    requiresBaseUrl: false,
    popularModels: ["mock-v1"],
  },
];

export function BYOKModal() {
  const {
    provider,
    apiKey,
    model,
    baseUrl,
    isSettingsOpen,
    setSettingsOpen,
    saveSettings,
    clearKey,
  } = useSettingsStore();

  const [selectedProvider, setSelectedProvider] = useState<LLMProvider>(provider);
  const [inputKey, setInputKey] = useState<string>(apiKey);
  const [inputModel, setInputModel] = useState<string>(model);
  const [inputBaseUrl, setInputBaseUrl] = useState<string>(baseUrl || "");
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  if (!isSettingsOpen) return null;

  const currentProviderConfig = PROVIDERS.find((p) => p.id === selectedProvider);

  const handleProviderChange = (newProvider: LLMProvider) => {
    setSelectedProvider(newProvider);
    setInputModel(DEFAULT_MODELS[newProvider]);
    if (newProvider === "custom_openai" && !inputBaseUrl) {
      setInputBaseUrl("http://localhost:11434/v1");
    } else if (newProvider === "custom_anthropic" && !inputBaseUrl) {
      setInputBaseUrl("http://localhost:8080");
    }
    setTestResult(null);
  };

  const handleSave = () => {
    saveSettings({
      provider: selectedProvider,
      apiKey: inputKey.trim(),
      model: inputModel.trim() || DEFAULT_MODELS[selectedProvider],
      baseUrl: inputBaseUrl.trim(),
    });
    setSettingsOpen(false);
  };

  const handleClearKey = () => {
    setInputKey("");
    clearKey();
    setTestResult(null);
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    setTestResult(null);
    try {
      const res = await checkBackendHealth();
      setTestResult({
        success: true,
        message: `Connected to API: ${res.service} v${res.version} [${res.environment}]`,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Connection failed";
      setTestResult({
        success: false,
        message: `${msg}. Ensure the FastAPI server is running on port 8000.`,
      });
    } finally {
      setTestingConnection(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="byok-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs animate-in fade-in duration-150"
    >
      <div className="relative w-full max-w-xl rounded-xl border border-zinc-800 bg-[#0d0f17] p-6 shadow-2xl space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-zinc-800/80 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-800/70 text-zinc-200">
              <KeyRound className="h-4 w-4" />
            </div>
            <div>
              <h2 id="byok-modal-title" className="text-base font-semibold text-zinc-100">
                LLM & BYOK Configuration
              </h2>
              <p className="text-xs text-zinc-400">
                Bring Your Own Key — keys reside exclusively in browser memory and are sent via request headers.
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setSettingsOpen(false)}
            aria-label="Close settings"
            className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="space-y-5">
          {/* Provider Selection */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                LLM Provider
              </label>
              <span className="text-[11px] text-zinc-500">Select inference backend</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {PROVIDERS.map((opt) => {
                const isSelected = selectedProvider === opt.id;
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => handleProviderChange(opt.id)}
                    className={`flex flex-col text-left p-3 rounded-lg border transition-all ${
                      isSelected
                        ? "border-blue-500/70 bg-blue-950/30 text-zinc-100 ring-1 ring-blue-500/30"
                        : "border-zinc-800/90 bg-zinc-900/40 text-zinc-300 hover:border-zinc-700 hover:bg-zinc-800/30"
                    }`}
                  >
                    <div className="flex items-center justify-between font-medium text-xs">
                      <span>{opt.name}</span>
                      {isSelected && (
                        <CheckCircle2 className="h-3.5 w-3.5 text-blue-400 shrink-0" />
                      )}
                    </div>
                    <span className="text-[11px] text-zinc-400 mt-1 line-clamp-2 leading-relaxed">
                      {opt.tagline}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Base URL Section for Custom Providers */}
          {currentProviderConfig?.requiresBaseUrl && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  Custom Endpoint Base URL
                </label>
                <span className="text-[11px] text-zinc-400">
                  {selectedProvider === "custom_openai" ? "e.g. /v1 appended" : "Gateway URL"}
                </span>
              </div>
              <div className="relative">
                <Globe className="absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-500" />
                <input
                  type="text"
                  value={inputBaseUrl}
                  onChange={(e) => setInputBaseUrl(e.target.value)}
                  placeholder={
                    selectedProvider === "custom_openai"
                      ? "http://localhost:11434/v1 or https://api.deepseek.com/v1"
                      : "http://localhost:8080 or your custom Anthropic gateway"
                  }
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-900 pl-9 pr-3.5 py-2 text-xs font-mono text-zinc-100 placeholder-zinc-500 focus:border-blue-500 focus:outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <p className="text-[11px] text-zinc-400">
                Compatible with any OpenAI/Anthropic API specification standard (Ollama, vLLM, LM Studio, OneAPI, LiteLLM Proxy).
              </p>
            </div>
          )}

          {/* Key Input Section */}
          {currentProviderConfig?.requiresKey || currentProviderConfig?.requiresBaseUrl ? (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  {currentProviderConfig.name} API Key
                  {currentProviderConfig.requiresBaseUrl && (
                    <span className="ml-1.5 lowercase font-normal text-zinc-400">(optional for local models)</span>
                  )}
                </label>
                {inputKey && (
                  <button
                    type="button"
                    onClick={handleClearKey}
                    className="flex items-center gap-1 text-[11px] text-rose-400 hover:text-rose-300 transition-colors"
                  >
                    <Trash2 className="h-3 w-3" />
                    Clear Key
                  </button>
                )}
              </div>
              <input
                type="password"
                value={inputKey}
                onChange={(e) => setInputKey(e.target.value)}
                placeholder={
                  currentProviderConfig.requiresBaseUrl
                    ? "sk-... or leave empty for unauthenticated local endpoints"
                    : `sk-... or your ${currentProviderConfig.name} API key`
                }
                className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3.5 py-2 text-xs font-mono text-zinc-100 placeholder-zinc-500 focus:border-blue-500 focus:outline-hidden focus:ring-1 focus:ring-blue-500"
              />
              <div className="flex items-center gap-1.5 text-[11px] text-zinc-400">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                <span>Encrypted in memory only. Never logged or persisted on backend.</span>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-blue-900/40 bg-blue-950/20 p-3 text-xs text-blue-300 flex items-start gap-2.5">
              <Info className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />
              <span>
                Mock mode runs simulated agents with realistic Indonesian marketplace figures without consuming external API credits.
              </span>
            </div>
          )}

          {/* Model Specification & Presets */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Model Identifier
              </label>
              <div className="flex items-center gap-1.5 text-[11px] text-zinc-400">
                <SlidersHorizontal className="h-3 w-3" />
                <span>Presets available</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <Cpu className="absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-500" />
                <input
                  type="text"
                  value={inputModel}
                  onChange={(e) => setInputModel(e.target.value)}
                  placeholder="e.g. gpt-4o-mini"
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-900 pl-9 pr-3.5 py-2 text-xs font-mono text-zinc-100 placeholder-zinc-500 focus:border-blue-500 focus:outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <button
                type="button"
                onClick={() => setInputModel(DEFAULT_MODELS[selectedProvider])}
                className="rounded-lg border border-zinc-700 bg-zinc-800/80 px-2.5 py-2 text-xs text-zinc-300 hover:bg-zinc-700 transition-colors"
                title="Reset to default model"
              >
                Default
              </button>
            </div>

            {/* Quick model pills */}
            {currentProviderConfig && currentProviderConfig.popularModels.length > 1 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {currentProviderConfig.popularModels.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setInputModel(m)}
                    className={`rounded-md border px-2 py-0.5 text-[11px] font-mono transition-colors ${
                      inputModel === m
                        ? "border-blue-500/60 bg-blue-950/40 text-blue-300"
                        : "border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:text-zinc-200 hover:border-zinc-700"
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Test Status feedback */}
          {testResult && (
            <div
              className={`rounded-lg border p-3 text-xs flex items-start gap-2.5 ${
                testResult.success
                  ? "border-emerald-800/50 bg-emerald-950/30 text-emerald-300"
                  : "border-rose-800/50 bg-rose-950/30 text-rose-300"
              }`}
            >
              {testResult.success ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
              )}
              <span className="leading-relaxed">{testResult.message}</span>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between border-t border-zinc-800/80 pt-4">
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={testingConnection}
            className="flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800/80 px-3 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${testingConnection ? "animate-spin" : ""}`}
            />
            {testingConnection ? "Testing..." : "Test Health"}
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setSettingsOpen(false)}
              className="rounded-lg border border-zinc-700 bg-transparent px-3 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-500 shadow-sm transition-colors"
            >
              Save Configuration
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
