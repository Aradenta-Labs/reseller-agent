"use client";

import React, { useState } from "react";
import { ItemDescription } from "@/lib/api";
import {
  Tag,
  DollarSign,
  Layers,
  CheckCircle2,
  Copy,
  Check,
  Code2,
  Box,
  FileSpreadsheet,
} from "lucide-react";

interface ItemResultCardProps {
  item: ItemDescription;
  providerUsed?: string;
  modelUsed?: string;
}

export function ItemResultCard({
  item,
  providerUsed,
  modelUsed,
}: ItemResultCardProps) {
  const [showJson, setShowJson] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopyJson = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(item, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  const formattedPrice =
    typeof item.estimated_retail_price === "number"
      ? new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: "USD",
          maximumFractionDigits: 2,
        }).format(item.estimated_retail_price)
      : "Not specified";

  return (
    <div className="w-full rounded-xl border border-zinc-800 bg-[#10121d] p-5 shadow-lg animate-in fade-in slide-in-from-bottom-2 duration-200">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-zinc-800/80 pb-4 gap-2">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-950/50 border border-emerald-700/40 text-emerald-400">
            <CheckCircle2 className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-zinc-100">
              Parsed Item Specification
            </h3>
            {(providerUsed || modelUsed) && (
              <p className="text-[11px] text-zinc-400 font-mono">
                Extracted via {providerUsed || "llm"} • {modelUsed || "default"}
              </p>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopyJson}
            className="flex items-center gap-1.5 rounded-md border border-zinc-700 bg-zinc-800/80 px-2.5 py-1.5 text-xs text-zinc-300 hover:bg-zinc-700 transition-colors"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                <span>Copy JSON</span>
              </>
            )}
          </button>
          <button
            type="button"
            onClick={() => setShowJson(!showJson)}
            className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs transition-colors ${
              showJson
                ? "border-blue-500/80 bg-blue-950/40 text-blue-300"
                : "border-zinc-700 bg-zinc-800/80 text-zinc-300 hover:bg-zinc-700"
            }`}
          >
            <Code2 className="h-3.5 w-3.5" />
            <span>{showJson ? "Hide JSON" : "View JSON"}</span>
          </button>
        </div>
      </div>

      {/* Main Content Body */}
      {showJson ? (
        <div className="mt-4">
          <pre className="rounded-lg border border-zinc-800 bg-zinc-950 p-4 font-mono text-xs text-blue-300/90 overflow-x-auto">
            {JSON.stringify(item, null, 2)}
          </pre>
        </div>
      ) : (
        <div className="mt-4 space-y-4">
          {/* Title & Category Badge */}
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              {item.category && (
                <span className="inline-flex items-center gap-1 rounded bg-zinc-800 px-2 py-0.5 text-[11px] font-medium text-zinc-300 border border-zinc-700">
                  <Layers className="h-3 w-3 text-zinc-400" />
                  {item.category}
                </span>
              )}
              <span className="inline-flex items-center gap-1 rounded bg-blue-950/40 px-2 py-0.5 text-[11px] font-medium text-blue-300 border border-blue-800/40">
                <Tag className="h-3 w-3 text-blue-400" />
                Condition: {item.condition}
              </span>
            </div>
            <h2 className="text-base sm:text-lg font-bold text-zinc-100 leading-snug">
              {item.name}
            </h2>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Estimated Price */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
              <div className="flex items-center gap-1.5 text-xs text-zinc-400 mb-1">
                <DollarSign className="h-3.5 w-3.5 text-emerald-400" />
                <span>Estimated Retail / Target Value</span>
              </div>
              <p className="text-base font-semibold font-mono text-zinc-100">
                {formattedPrice}
              </p>
            </div>

            {/* Condition Evaluation */}
            <div className="rounded-lg border border-zinc-800 bg-zinc-950/60 p-3">
              <div className="flex items-center gap-1.5 text-xs text-zinc-400 mb-1">
                <Box className="h-3.5 w-3.5 text-blue-400" />
                <span>Item State</span>
              </div>
              <p className="text-sm font-medium text-zinc-200">
                {item.condition || "Unspecified"}
              </p>
            </div>
          </div>

          {/* Summary / Synopsis if present */}
          {item.summary && (
            <div className="rounded-lg border border-zinc-800/80 bg-zinc-950/40 p-3">
              <div className="flex items-center gap-1.5 text-xs font-medium text-zinc-300 mb-1">
                <FileSpreadsheet className="h-3.5 w-3.5 text-zinc-400" />
                <span>Summary Overview</span>
              </div>
              <p className="text-xs text-zinc-300 leading-relaxed">
                {item.summary}
              </p>
            </div>
          )}

          {/* Key Features List */}
          {item.key_features && item.key_features.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                Distinguishing Features & Specifications
              </h4>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {item.key_features.map((feat, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-2 rounded-md border border-zinc-800/70 bg-zinc-950/50 p-2.5 text-xs text-zinc-300"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-blue-400 shrink-0 mt-1.5" />
                    <span className="leading-tight">{feat}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
