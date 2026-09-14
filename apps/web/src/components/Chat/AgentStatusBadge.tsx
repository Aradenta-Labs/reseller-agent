"use client";

import React from "react";
import {
  Compass,
  TrendingUp,
  Calculator,
  Crown,
  UserCheck,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Clock,
} from "lucide-react";

export type AgentKey =
  | "scout"
  | "analyst"
  | "pricing"
  | "chief"
  | "customer";

export type AgentStateStatus = "idle" | "active" | "completed" | "error";

export interface AgentInfo {
  key: AgentKey;
  name: string;
  role: string;
  status: AgentStateStatus;
  statusMessage?: string;
  resultSummary?: string;
}

export const SWARM_AGENTS: {
  key: AgentKey;
  name: string;
  role: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
  {
    key: "scout",
    name: "Market Scout",
    role: "Tokopedia, Shopee, FB",
    icon: Compass,
  },
  {
    key: "analyst",
    name: "Trend Analyst",
    role: "Demand & Hype",
    icon: TrendingUp,
  },
  {
    key: "pricing",
    name: "Pricing Strategist",
    role: "3-Tier & 20% Fee",
    icon: Calculator,
  },
  {
    key: "chief",
    name: "Chief Strategist",
    role: "Master Playbook",
    icon: Crown,
  },
  {
    key: "customer",
    name: "Customer Persona",
    role: "Skeptical Verdict",
    icon: UserCheck,
  },
];

interface AgentStatusBadgeProps {
  agents: Record<AgentKey, {
    status: AgentStateStatus;
    statusMessage?: string;
    resultSummary?: string;
  }>;
  compact?: boolean;
}

export function AgentStatusBadge({ agents, compact = false }: AgentStatusBadgeProps) {
  return (
    <div className="w-full rounded-xl border border-zinc-800 bg-[#0d0f17] p-3.5 space-y-3">
      <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
          <span className="text-xs font-semibold tracking-wide text-zinc-200 uppercase">
            5-Agent Swarm Orchestration
          </span>
        </div>
        <span className="text-[11px] font-mono text-zinc-400">
          LangGraph Parallel Flow
        </span>
      </div>

      {/* Grid of 5 Agents */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-2">
        {SWARM_AGENTS.map((item) => {
          const current = agents[item.key] || { status: "idle" };
          const Icon = item.icon;

          const isIdle = current.status === "idle";
          const isActive = current.status === "active";
          const isCompleted = current.status === "completed";
          const isError = current.status === "error";

          return (
            <div
              key={item.key}
              className={`relative flex flex-col justify-between rounded-lg border p-2.5 transition-all ${
                isActive
                  ? "border-blue-500/60 bg-blue-950/20 text-zinc-100 ring-1 ring-blue-500/40 shadow-xs"
                  : isCompleted
                  ? "border-emerald-800/40 bg-emerald-950/15 text-zinc-200"
                  : isError
                  ? "border-rose-800/40 bg-rose-950/20 text-rose-200"
                  : "border-zinc-800/80 bg-zinc-900/30 text-zinc-400"
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-1">
                <div className="flex items-center gap-1.5">
                  <div
                    className={`flex h-6 w-6 items-center justify-center rounded-md border text-xs ${
                      isActive
                        ? "border-blue-500/40 bg-blue-900/40 text-blue-300"
                        : isCompleted
                        ? "border-emerald-700/40 bg-emerald-900/30 text-emerald-400"
                        : isError
                        ? "border-rose-700/40 bg-rose-900/30 text-rose-400"
                        : "border-zinc-700 bg-zinc-800/60 text-zinc-400"
                    }`}
                  >
                    <Icon className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <h4 className="text-[11px] font-medium leading-tight text-zinc-200">
                      {item.name}
                    </h4>
                    <span className="text-[9px] text-zinc-400 block font-mono">
                      {item.role}
                    </span>
                  </div>
                </div>

                {/* Status icon */}
                <div className="shrink-0 mt-0.5">
                  {isActive && (
                    <Loader2 className="h-3.5 w-3.5 text-blue-400 animate-spin" />
                  )}
                  {isCompleted && (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  )}
                  {isError && (
                    <AlertCircle className="h-3.5 w-3.5 text-rose-400" />
                  )}
                  {isIdle && (
                    <Clock className="h-3.5 w-3.5 text-zinc-600" />
                  )}
                </div>
              </div>

              {/* Status or Summary details */}
              {!compact && (
                <div className="mt-2 text-[10px] line-clamp-2 leading-tight">
                  {isActive && (
                    <span className="text-blue-300 animate-pulse font-sans">
                      {current.statusMessage || "Processing..."}
                    </span>
                  )}
                  {isCompleted && (
                    <span className="text-zinc-400">
                      {current.resultSummary || "Completed task successfully"}
                    </span>
                  )}
                  {isError && (
                    <span className="text-rose-400 font-mono">
                      {current.statusMessage || "Execution failed"}
                    </span>
                  )}
                  {isIdle && (
                    <span className="text-zinc-400">Standby</span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
