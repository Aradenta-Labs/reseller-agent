"use client";

import React, { useState, useEffect } from "react";
import { useSettingsStore } from "@/store/useSettingsStore";
import { checkBackendHealth } from "@/lib/api";
import {
  KeyRound,
  Activity,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Cpu,
} from "lucide-react";

export function Header() {
  const { provider, model, isConfigured, setSettingsOpen } = useSettingsStore();
  const [mounted, setMounted] = useState(false);
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);

  useEffect(() => {
    // Subscription pattern avoids synchronous setState cascade warning
    let isSubscribed = true;

    async function verifyHealth() {
      try {
        await checkBackendHealth();
        if (isSubscribed) setApiConnected(true);
      } catch {
        if (isSubscribed) setApiConnected(false);
      }
    }

    verifyHealth();
    const interval = setInterval(verifyHealth, 30000);
    return () => {
      isSubscribed = false;
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setMounted(true);
    }, 0);
    return () => clearTimeout(timer);
  }, []);

  const configured = mounted ? isConfigured() : false;

  return (
    <header className="sticky top-0 z-30 w-full border-b border-zinc-800 bg-[#090a0f]/90 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
        {/* Left Branding */}
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-blue-500/30 bg-blue-950/40 text-blue-400 shadow-sm">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-base font-semibold tracking-tight text-zinc-100">
                Reseller AI
              </span>
              <span className="rounded border border-blue-500/40 bg-blue-950/60 px-1.5 py-0.5 text-[10px] font-medium tracking-wide uppercase text-blue-300">
                Swarm v1.0
              </span>
            </div>
            <p className="text-xs text-zinc-400 hidden sm:block">
              Intelligent multi-platform arbitrage & resale assistant
            </p>
          </div>
        </div>

        {/* Right Status & Controls */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Backend Status Indicator */}
          <div className="flex items-center gap-1.5 rounded-md border border-zinc-800 bg-zinc-900/70 px-2.5 py-1 text-xs text-zinc-300">
            <Activity className="h-3.5 w-3.5 text-zinc-400" />
            <span className="hidden md:inline text-zinc-400">API:</span>
            {apiConnected === null ? (
              <span className="flex items-center gap-1 text-zinc-400">
                <span className="h-1.5 w-1.5 rounded-full bg-zinc-400 animate-pulse" />
                Checking
              </span>
            ) : apiConnected ? (
              <span className="flex items-center gap-1 text-emerald-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                Online
              </span>
            ) : (
              <span className="flex items-center gap-1 text-rose-400">
                <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
                Offline
              </span>
            )}
          </div>

          {/* Active Model Indicator */}
          {mounted && (
            <div className="hidden lg:flex items-center gap-1.5 rounded-md border border-zinc-800 bg-zinc-900/70 px-2.5 py-1 text-xs text-zinc-300">
              <Cpu className="h-3.5 w-3.5 text-zinc-400" />
              <span className="text-zinc-400 uppercase font-mono text-[11px]">
                {provider}:
              </span>
              <span className="max-w-[120px] truncate font-mono text-[11px] text-zinc-200">
                {model}
              </span>
            </div>
          )}

          {/* Settings / BYOK Status Trigger */}
          <button
            onClick={() => setSettingsOpen(true)}
            className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors ${
              configured
                ? "border-zinc-700 bg-zinc-800/80 text-zinc-200 hover:border-zinc-600 hover:bg-zinc-700/80"
                : "border-amber-500/40 bg-amber-950/30 text-amber-200 hover:bg-amber-900/40 hover:border-amber-500/60"
            }`}
            title="Configure BYOK LLM credentials"
          >
            <KeyRound className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">
              {configured ? "LLM Settings" : "Configure Key"}
            </span>
            {configured ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
