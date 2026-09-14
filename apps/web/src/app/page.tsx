"use client";

import React, { useState } from "react";
import { Header } from "@/components/Header";
import { SettingsModal } from "@/components/SettingsModal";
import { ItemParserInput } from "@/components/ItemParserInput";
import { ItemResultCard } from "@/components/ItemResultCard";
import {
  parseItem,
  ParseItemRequest,
  ParseItemResponse,
} from "@/lib/api";
import { useSettingsStore } from "@/store/useSettingsStore";
import {
  ArrowRight,
  Sparkles,
  AlertTriangle,
  KeyRound,
  FileSearch,
  CheckCircle2,
  Terminal,
} from "lucide-react";

export default function HomePage() {
  const [result, setResult] = useState<ParseItemResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { isConfigured, setSettingsOpen, provider } = useSettingsStore();

  const handleParse = async (payload: ParseItemRequest) => {
    setError(null);
    setIsLoading(true);

    try {
      const response = await parseItem(payload);
      setResult(response);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to parse item.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const configured = isConfigured();

  return (
    <div className="flex min-h-screen flex-col bg-[#090a0f] text-zinc-100">
      <Header />
      <SettingsModal />

      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 space-y-8">
        {/* Banner / Value Proposition */}
        <section className="relative overflow-hidden rounded-2xl border border-zinc-800/80 bg-gradient-to-b from-[#141829] to-[#0d0f18] p-6 sm:p-8">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-1.5 rounded-full border border-blue-500/30 bg-blue-950/40 px-3 py-1 text-xs font-medium text-blue-300 mb-3">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Phase 1 Vision & BYOK Ingestion</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white leading-tight">
              Extract Structured Resale Specs with Multimodal AI
            </h1>
            <p className="mt-2 text-sm text-zinc-300 leading-relaxed">
              Upload listing photos or raw item descriptions. Reseller AI uses your
              configured LLM provider to extract normalized title, condition, category,
              key features, and retail estimation in structured JSON.
            </p>
          </div>

          {/* BYOK Warning if unconfigured */}
          {!configured && (
            <div className="mt-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-amber-500/40 bg-amber-950/20 p-4 text-xs text-amber-200">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <span className="font-semibold text-amber-300">
                    BYOK Configuration Required:
                  </span>{" "}
                  You have selected <code className="bg-amber-950 px-1 py-0.5 rounded font-mono">{provider}</code> without an API key. Either provide an API key or switch to Mock Mode in Settings.
                </div>
              </div>
              <button
                type="button"
                onClick={() => setSettingsOpen(true)}
                className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/20 border border-amber-500/40 px-3 py-1.5 text-xs font-medium text-amber-200 hover:bg-amber-500/30 shrink-0 transition-colors"
              >
                <KeyRound className="h-3.5 w-3.5" />
                <span>Open Settings</span>
              </button>
            </div>
          )}
        </section>

        {/* Workflow Grid */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Column: Input */}
          <div className="lg:col-span-6 space-y-6">
            <ItemParserInput onParse={handleParse} isLoading={isLoading} />

            {/* Architecture Steps Explainer */}
            <div className="rounded-xl border border-zinc-800/60 bg-[#10121d]/60 p-4 text-xs text-zinc-400 space-y-2.5">
              <div className="flex items-center gap-1.5 font-semibold text-zinc-300 uppercase tracking-wider text-[11px]">
                <Terminal className="h-3.5 w-3.5 text-blue-400" />
                <span>Pipeline Architecture Flow</span>
              </div>
              <ul className="space-y-1.5 pl-1">
                <li className="flex items-center gap-2">
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-zinc-800 text-[10px] text-zinc-300 font-mono">1</span>
                  <span>Input converted to payload (Text / Base64 image)</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-zinc-800 text-[10px] text-zinc-300 font-mono">2</span>
                  <span>Dispatched with <code className="text-zinc-300 font-mono">X-LLM-Provider</code> & <code className="text-zinc-300 font-mono">X-API-Key</code> headers</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-zinc-800 text-[10px] text-zinc-300 font-mono">3</span>
                  <span>LiteLLM + Instructor strictly enforces <code className="text-blue-300 font-mono">ItemDescription</code> schema</span>
                </li>
                <li className="flex items-center gap-2">
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-zinc-800 text-[10px] text-zinc-300 font-mono">4</span>
                  <span>Outputs downstream seed for Phase 2 Market Scraping & Phase 3 Swarm</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Right Column: Output / Skeletons / Empty States */}
          <div className="lg:col-span-6 space-y-4">
            {/* Error Alert */}
            {error && (
              <div className="rounded-xl border border-rose-800/60 bg-rose-950/30 p-4 text-xs text-rose-200 space-y-2">
                <div className="flex items-center gap-2 font-semibold text-rose-300">
                  <AlertTriangle className="h-4 w-4 text-rose-400" />
                  <span>Parsing Error</span>
                </div>
                <p className="leading-relaxed font-mono text-[11px] bg-rose-950/60 p-2.5 rounded border border-rose-900/50">
                  {error}
                </p>
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[11px] text-zinc-400">
                    Ensure FastAPI backend is running and valid API keys are configured.
                  </span>
                  <button
                    type="button"
                    onClick={() => setSettingsOpen(true)}
                    className="underline text-blue-400 hover:text-blue-300"
                  >
                    Check BYOK Settings
                  </button>
                </div>
              </div>
            )}

            {/* Loading Skeleton */}
            {isLoading && (
              <div className="rounded-xl border border-zinc-800 bg-[#10121d] p-5 space-y-4 animate-pulse">
                <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
                  <div className="flex items-center gap-2">
                    <div className="h-6 w-6 rounded bg-zinc-800" />
                    <div className="h-4 w-36 rounded bg-zinc-800" />
                  </div>
                  <div className="h-6 w-20 rounded bg-zinc-800" />
                </div>
                <div className="space-y-2">
                  <div className="h-5 w-3/4 rounded bg-zinc-800" />
                  <div className="h-3 w-1/2 rounded bg-zinc-800" />
                </div>
                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className="h-16 rounded-lg bg-zinc-800/60" />
                  <div className="h-16 rounded-lg bg-zinc-800/60" />
                </div>
                <div className="h-20 rounded-lg bg-zinc-800/40" />
              </div>
            )}

            {/* Result display */}
            {result && !isLoading && (
              <ItemResultCard
                item={result.item}
                providerUsed={result.provider_used}
                modelUsed={result.model_used}
              />
            )}

            {/* Empty State */}
            {!result && !isLoading && !error && (
              <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-zinc-800/80 bg-[#10121d]/40 p-10 text-center text-zinc-400 min-h-[320px]">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-zinc-900 border border-zinc-800 text-zinc-400 mb-3">
                  <FileSearch className="h-6 w-6" />
                </div>
                <h3 className="text-sm font-semibold text-zinc-200">
                  No Item Metadata Extracted Yet
                </h3>
                <p className="mt-1 max-w-sm text-xs text-zinc-400">
                  Type a description or upload a photo on the left, then click &ldquo;Parse Structured Item&rdquo; to see the structured schema result.
                </p>
                <div className="mt-4 flex items-center gap-1.5 text-[11px] text-zinc-500">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  <span>Supports English & Bahasa Indonesia descriptions</span>
                </div>
              </div>
            )}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-zinc-800/80 bg-[#090a0f] py-4 text-center text-xs text-zinc-500">
        <div className="mx-auto max-w-6xl px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Reseller AI Swarm Architecture • Phase 1 Foundation</span>
          <span className="font-mono text-[11px]">FastAPI + Next.js App Router + LiteLLM</span>
        </div>
      </footer>
    </div>
  );
}
