"use client";

import React, { useState, useEffect } from "react";
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
} from "lucide-react";

const PROVIDER_OPTIONS: {
  id: LLMProvider;
  name: string;
  description: string;
  defaultModel: string;
  requiresKey: boolean;
}[] = [
  {
    id: "openai",
    name: "OpenAI",
    description: "GPT-4o, GPT-4o-mini (Supports vision & structured JSON)",
    defaultModel: DEFAULT_MODELS.openai,
    requiresKey: true,
  },
  {
    id: "anthropic",
    name: "Anthropic",
    description: "Claude 3.5 Sonnet, Claude 3.5 Haiku",
    defaultModel: DEFAULT_MODELS.anthropic,
    requiresKey: true,
  },
  {
    id: "openrouter",
    name: "OpenRouter",
    description: "Unified gateway across 100+ open and proprietary models",
    defaultModel: DEFAULT_MODELS.openrouter,
    requiresKey: true,
  },
  {
    id: "mock",
    name: "Mock Mode (Zero Cost)",
    description: "Deterministic local synthetic responses for testing without API keys",
    defaultModel: DEFAULT_MODELS.mock,
    requiresKey: false,
  },
];

export function SettingsModal() {
  const {
    provider,
    apiKey,
    model,
    isSettingsOpen,
    setSettingsOpen,
    saveSettings,
    clearKey,
  } = useSettingsStore();

  const [selectedProvider, setSelectedProvider] = useState<LLMProvider>(provider);
  const [inputKey, setInputKey] = useState<string>(apiKey);
  const [inputModel, setInputModel] = useState<string>(model);
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  // Synchronize internal state when modal opens or store changes
  useEffect(() => {
    if (isSettingsOpen) {
      setSelectedProvider(provider);
      setInputKey(apiKey);
      setInputModel(model || DEFAULT_MODELS[provider]);
      setTestResult(null);
    }
  }, [isSettingsOpen, provider, apiKey, model]);

  if (!isSettingsOpen) return null;

  const currentProviderConfig = PROVIDER_OPTIONS.find(
    (p) => p.id === selectedProvider
  );

  const handleProviderChange = (newProvider: LLMProvider) => {
    setSelectedProvider(newProvider);
    setInputModel(DEFAULT_MODELS[newProvider]);
    setTestResult(null);
  };

  const handleSave = () => {
    saveSettings({
      provider: selectedProvider,
      apiKey: inputKey.trim(),
      model: inputModel.trim() || DEFAULT_MODELS[selectedProvider],
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
        message: `Connected to ${res.service} v${res.version} [${res.environment}]`,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to backend";
      setTestResult({
        success: false,
        message: `${msg}. Make sure the FastAPI server is running on localhost:8000.`,
      });
    } finally {
      setTestingConnection(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg rounded-xl border border-zinc-800 bg-[#0d0f18] p-6 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-zinc-700 bg-zinc-800 text-zinc-200">
              <KeyRound className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-zinc-100">
                LLM & BYOK Settings
              </h2>
              <p className="text-xs text-zinc-400">
                Bring Your Own Key — credentials remain purely in your browser memory
              </p>
            </div>
          </div>
          <button
            onClick={() => setSettingsOpen(false)}
            className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="mt-5 space-y-5">
          {/* Provider Selector */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
              Select LLM Provider
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {PROVIDER_OPTIONS.map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => handleProviderChange(opt.id)}
                  className={`flex flex-col text-left p-3 rounded-lg border transition-all ${
                    selectedProvider === opt.id
                      ? "border-blue-500/80 bg-blue-950/30 text-zinc-100 ring-1 ring-blue-500/50"
                      : "border-zinc-800 bg-zinc-900/40 text-zinc-300 hover:border-zinc-700 hover:bg-zinc-800/40"
                  }`}
                >
                  <div className="flex items-center justify-between font-medium text-xs">
                    <span>{opt.name}</span>
                    {selectedProvider === opt.id && (
                      <CheckCircle2 className="h-3.5 w-3.5 text-blue-400" />
                    )}
                  </div>
                  <span className="text-[11px] text-zinc-400 mt-1 line-clamp-2 leading-tight">
                    {opt.description}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* API Key Input (if required) */}
          {currentProviderConfig?.requiresKey ? (
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                  {currentProviderConfig.name} API Key
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
              <div className="relative">
                <input
                  type="password"
                  value={inputKey}
                  onChange={(e) => setInputKey(e.target.value)}
                  placeholder={`Enter your ${currentProviderConfig.name} API key...`}
                  className="w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3.5 py-2 text-xs font-mono text-zinc-100 placeholder-zinc-500 focus:border-blue-500 focus:outline-hidden focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-zinc-400">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                <span>
                  Never saved to backend databases. Attached only as request headers.
                </span>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-blue-900/40 bg-blue-950/20 p-3 text-xs text-blue-300 flex items-start gap-2">
              <Info className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />
              <span>
                Mock mode returns structured dummy item data instantly without invoking external LLM APIs. Useful for UI testing and local verification.
              </span>
            </div>
          )}

          {/* Model Specification */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-1.5">
              Model Identifier
            </label>
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
                Reset
              </button>
            </div>
          </div>

          {/* Test Status feedback */}
          {testResult && (
            <div
              className={`rounded-lg border p-3 text-xs flex items-start gap-2 ${
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
        <div className="mt-6 flex items-center justify-between border-t border-zinc-800 pt-4">
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={testingConnection}
            className="flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-800/80 px-3 py-2 text-xs font-medium text-zinc-300 hover:bg-zinc-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${testingConnection ? "animate-spin" : ""}`}
            />
            {testingConnection ? "Checking..." : "Test Backend API"}
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
