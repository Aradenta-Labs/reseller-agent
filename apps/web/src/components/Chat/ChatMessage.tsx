"use client";

import React, { useState } from "react";
import {
  AgentStatusBadge,
  AgentKey,
  AgentStateStatus,
} from "./AgentStatusBadge";
import {
  PricingStrategy,
  MarketPriceItem,
  ScoutSummary,
  ItemDescription,
} from "@/lib/api";
import {
  Bot,
  User,
  CheckCircle,
  XCircle,
  Coins,
  DollarSign,
  Store,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  ShieldAlert,
} from "lucide-react";

export interface MessageData {
  id: string;
  role: "user" | "assistant";
  content: string;
  imageBase64?: string;
  capitalCost?: number;
  timestamp: string;
  isStreaming?: boolean;
  agentStates?: Record<
    AgentKey,
    {
      status: AgentStateStatus;
      statusMessage?: string;
      resultSummary?: string;
    }
  >;
  parsedItem?: ItemDescription | Record<string, unknown> | string;
  marketPrices?: MarketPriceItem[];
  scoutSummary?: ScoutSummary;
  trendAnalysis?: string;
  pricingStrategy?: PricingStrategy;
  finalStrategy?: string;
  customerVerdict?: "BUY" | "PASS" | string;
  errors?: string[];
}

interface ChatMessageProps {
  message: MessageData;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const [showMarketDetails, setShowMarketDetails] = useState(false);

  // Simple Markdown renderer for sections and bolding
  const renderMarkdown = (text: string) => {
    if (!text) return null;
    const lines = text.split("\n");

    return (
      <div className="space-y-2 text-xs sm:text-sm text-zinc-200 leading-relaxed font-sans">
        {lines.map((line, idx) => {
          const trimmed = line.trim();
          if (!trimmed) return <div key={idx} className="h-1.5" />;

          // Heading 3
          if (trimmed.startsWith("### ")) {
            return (
              <h4 key={idx} className="text-sm font-bold text-zinc-100 mt-3 mb-1">
                {trimmed.replace("### ", "")}
              </h4>
            );
          }
          // Heading 2
          if (trimmed.startsWith("## ")) {
            return (
              <h3 key={idx} className="text-base font-bold text-white mt-4 mb-1.5 border-b border-zinc-800 pb-1">
                {trimmed.replace("## ", "")}
              </h3>
            );
          }
          // Bullet point
          if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
            const content = trimmed.substring(2);
            return (
              <li key={idx} className="ml-4 list-disc text-zinc-300">
                {renderFormattedSpan(content)}
              </li>
            );
          }
          // Numbered list
          if (/^\d+\.\s/.test(trimmed)) {
            return (
              <p key={idx} className="ml-2 text-zinc-300 font-medium">
                {renderFormattedSpan(trimmed)}
              </p>
            );
          }

          return <p key={idx}>{renderFormattedSpan(trimmed)}</p>;
        })}
      </div>
    );
  };

  const renderFormattedSpan = (text: string) => {
    // Replace **bold** with strong elements
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={i} className="font-semibold text-zinc-100">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  if (isUser) {
    return (
      <div className="flex w-full justify-end gap-3 px-2 py-3">
        <div className="flex max-w-2xl flex-col items-end gap-2">
          {/* User Bubble */}
          <div className="rounded-2xl rounded-tr-xs border border-zinc-700 bg-zinc-800/80 px-4 py-3 text-xs sm:text-sm text-zinc-100 shadow-sm">
            {/* Optional Thumbnail */}
            {message.imageBase64 && (
              <div className="mb-2.5 overflow-hidden rounded-lg border border-zinc-600 bg-black">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`data:image/jpeg;base64,${message.imageBase64}`}
                  alt="Thrift item uploaded"
                  className="max-h-48 w-full object-cover"
                />
              </div>
            )}
            <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
          </div>

          {/* User Metadata badges */}
          <div className="flex items-center gap-2 text-[11px] text-zinc-500">
            {message.capitalCost !== undefined && message.capitalCost !== null && (
              <span className="inline-flex items-center gap-1 rounded-md border border-amber-900/50 bg-amber-950/40 px-2 py-0.5 text-amber-300 font-mono">
                <Coins className="h-3 w-3 text-amber-400" />
                Capital: Rp {message.capitalCost.toLocaleString("id-ID")}
              </span>
            )}
            <span>{message.timestamp}</span>
          </div>
        </div>

        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-zinc-700 bg-zinc-800 text-zinc-300">
          <User className="h-4 w-4" />
        </div>
      </div>
    );
  }

  // Assistant / AI Message View
  const verdict = message.customerVerdict;
  const isBuy = verdict === "BUY";
  const pricing = message.pricingStrategy;
  const scout = message.scoutSummary;
  const listings = message.marketPrices || [];

  return (
    <div className="flex w-full justify-start gap-3 px-2 py-4">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-blue-500/40 bg-blue-950/60 text-blue-400">
        <Bot className="h-4 w-4" />
      </div>

      <div className="flex w-full max-w-3xl flex-col gap-4">
        {/* Swarm Live Agent Tracker Status Bar */}
        {message.agentStates && (
          <AgentStatusBadge
            agents={message.agentStates}
            compact={!message.isStreaming && Boolean(message.finalStrategy)}
          />
        )}

        {/* Verdict Badge Banner if completed */}
        {verdict && (
          <div
            className={`flex items-center justify-between rounded-xl border p-4 shadow-sm ${
              isBuy
                ? "border-emerald-500/50 bg-emerald-950/25 text-emerald-200"
                : "border-rose-500/50 bg-rose-950/25 text-rose-200"
            }`}
          >
            <div className="flex items-center gap-3">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-lg border ${
                  isBuy
                    ? "border-emerald-600 bg-emerald-900/50 text-emerald-300"
                    : "border-rose-600 bg-rose-900/50 text-rose-300"
                }`}
              >
                {isBuy ? (
                  <CheckCircle className="h-6 w-6" />
                ) : (
                  <XCircle className="h-6 w-6" />
                )}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                    Customer Persona Verdict
                  </span>
                  <span
                    className={`rounded px-2 py-0.5 text-xs font-bold font-mono tracking-wider ${
                      isBuy
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                        : "bg-rose-500/20 text-rose-300 border border-rose-500/40"
                    }`}
                  >
                    {verdict}
                  </span>
                </div>
                <p className="text-xs text-zinc-300 mt-0.5">
                  {isBuy
                    ? "Recommended for immediate acquisition — solid spread and healthy buyer demand."
                    : "Proceed with caution or pass — tight margin buffer, slow liquidation speed, or high risk."}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* 3-Tier Dynamic Pricing Table Card */}
        {pricing && (pricing.fast_sale || pricing.patient_sale || pricing.direct_sale) && (
          <div className="rounded-xl border border-zinc-800 bg-[#0d0f17] p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-2">
              <div className="flex items-center gap-2">
                <DollarSign className="h-4 w-4 text-emerald-400" />
                <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-200">
                  Resale Pricing Tiers (20% Platform Fee &amp; Margin Simulation)
                </h4>
              </div>
              {pricing.meets_target_margin !== undefined && (
                <span
                  className={`text-[11px] font-mono px-2 py-0.5 rounded border ${
                    pricing.meets_target_margin
                      ? "border-emerald-800 bg-emerald-950/40 text-emerald-300"
                      : "border-amber-800 bg-amber-950/40 text-amber-300"
                  }`}
                >
                  {pricing.meets_target_margin ? ">=15% Net Target Met" : "<15% Margin Alert"}
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              {/* Fast Sale */}
              {pricing.fast_sale && (
                <div className="flex flex-col justify-between rounded-lg border border-zinc-800 bg-zinc-900/40 p-3 text-xs">
                  <div>
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-amber-400">
                      Fast Liquidation (1-3d)
                    </span>
                    <div className="mt-1 text-base font-bold font-mono text-zinc-100">
                      Rp {pricing.fast_sale.listing_price.toLocaleString("id-ID")}
                    </div>
                  </div>
                  <div className="mt-2 space-y-1 border-t border-zinc-800/80 pt-2 text-[11px] text-zinc-400">
                    <div className="flex justify-between">
                      <span>Net Profit:</span>
                      <span className="font-mono text-emerald-400">
                        Rp {(pricing.fast_sale.net_profit || 0).toLocaleString("id-ID")}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Margin:</span>
                      <span className="font-mono font-medium text-zinc-200">
                        {pricing.fast_sale.net_margin_percent}%
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Patient Sale */}
              {pricing.patient_sale && (
                <div className="flex flex-col justify-between rounded-lg border border-blue-900/50 bg-blue-950/20 p-3 text-xs">
                  <div>
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-blue-400">
                      Patient Market (1-2w)
                    </span>
                    <div className="mt-1 text-base font-bold font-mono text-zinc-100">
                      Rp {pricing.patient_sale.listing_price.toLocaleString("id-ID")}
                    </div>
                  </div>
                  <div className="mt-2 space-y-1 border-t border-zinc-800/80 pt-2 text-[11px] text-zinc-400">
                    <div className="flex justify-between">
                      <span>Net Profit:</span>
                      <span className="font-mono text-emerald-400">
                        Rp {(pricing.patient_sale.net_profit || 0).toLocaleString("id-ID")}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Margin:</span>
                      <span className="font-mono font-medium text-zinc-200">
                        {pricing.patient_sale.net_margin_percent}%
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Direct Sale */}
              {pricing.direct_sale && (
                <div className="flex flex-col justify-between rounded-lg border border-emerald-900/50 bg-emerald-950/20 p-3 text-xs">
                  <div>
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-400">
                      Direct / COD (0% Fee)
                    </span>
                    <div className="mt-1 text-base font-bold font-mono text-zinc-100">
                      Rp {pricing.direct_sale.listing_price.toLocaleString("id-ID")}
                    </div>
                  </div>
                  <div className="mt-2 space-y-1 border-t border-zinc-800/80 pt-2 text-[11px] text-zinc-400">
                    <div className="flex justify-between">
                      <span>Net Profit:</span>
                      <span className="font-mono text-emerald-400">
                        Rp {(pricing.direct_sale.net_profit || 0).toLocaleString("id-ID")}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span>Margin:</span>
                      <span className="font-mono font-medium text-zinc-200">
                        {pricing.direct_sale.net_margin_percent}%
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Market Scout Collapsible Details */}
        {scout && listings.length > 0 && (
          <div className="rounded-xl border border-zinc-800 bg-[#0d0f17] p-3 text-xs">
            <button
              type="button"
              onClick={() => setShowMarketDetails(!showMarketDetails)}
              className="flex w-full items-center justify-between text-left text-zinc-300 hover:text-white"
            >
              <div className="flex items-center gap-2 font-medium">
                <Store className="h-3.5 w-3.5 text-blue-400" />
                <span>
                  Scouted {listings.length} live listings (Avg: Rp{" "}
                  {(scout.average_price || 0).toLocaleString("id-ID")})
                </span>
              </div>
              {showMarketDetails ? (
                <ChevronUp className="h-3.5 w-3.5" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5" />
              )}
            </button>

            {showMarketDetails && (
              <div className="mt-3 space-y-2 border-t border-zinc-800/80 pt-3">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] font-mono text-zinc-400 mb-2">
                  <div>Min: Rp {(scout.min_price || 0).toLocaleString("id-ID")}</div>
                  <div>Median: Rp {(scout.median_price || 0).toLocaleString("id-ID")}</div>
                  <div>Max: Rp {(scout.max_price || 0).toLocaleString("id-ID")}</div>
                  <div>Best: {scout.best_platform_for_resale || "Tokopedia"}</div>
                </div>

                <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
                  {listings.map((item, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between rounded border border-zinc-800 bg-zinc-900/40 p-2 text-[11px]"
                    >
                      <div className="flex items-center gap-2 truncate">
                        <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-300 uppercase">
                          {item.platform}
                        </span>
                        <span className="truncate text-zinc-200">{item.title}</span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0 font-mono text-zinc-300">
                        <span>Rp {item.price.toLocaleString("id-ID")}</span>
                        {item.url && (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noreferrer"
                            className="text-zinc-500 hover:text-blue-400"
                          >
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Master Strategy / Playbook Output */}
        {message.finalStrategy ? (
          <div className="rounded-xl border border-zinc-800/90 bg-[#10121d] p-5 shadow-sm space-y-3">
            <div className="flex items-center gap-2 border-b border-zinc-800/80 pb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
                Chief Strategist Master Playbook
              </span>
            </div>
            {renderMarkdown(message.finalStrategy)}
          </div>
        ) : message.content ? (
          <div className="rounded-xl border border-zinc-800 bg-[#10121d] p-4 text-xs sm:text-sm text-zinc-300">
            <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
          </div>
        ) : null}

        {/* Errors / Warnings if any */}
        {message.errors && message.errors.length > 0 && (
          <div className="rounded-lg border border-amber-900/40 bg-amber-950/20 p-3 text-xs text-amber-300 space-y-1">
            <div className="flex items-center gap-1.5 font-semibold">
              <ShieldAlert className="h-3.5 w-3.5 text-amber-400" />
              <span>Warnings during swarm execution:</span>
            </div>
            <ul className="list-disc pl-4 space-y-0.5 font-mono text-[11px] text-amber-400">
              {message.errors.map((e, idx) => (
                <li key={idx}>{e}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
