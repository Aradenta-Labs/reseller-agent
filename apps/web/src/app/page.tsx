"use client";

import React, { useState, useRef, useEffect } from "react";
import { Header } from "@/components/Header";
import { BYOKModal } from "@/components/Settings/BYOKModal";
import { ItemParserInput } from "@/components/ItemParserInput";
import { ItemResultCard } from "@/components/ItemResultCard";
import { ChatInput } from "@/components/Chat/ChatInput";
import { ChatMessage, MessageData } from "@/components/Chat/ChatMessage";
import { AgentKey, AgentStateStatus } from "@/components/Chat/AgentStatusBadge";
import {
  parseItem,
  streamOrchestration,
  ParseItemRequest,
  ParseItemResponse,
  OrchestrateStreamEvent,
} from "@/lib/api";
import { useSettingsStore } from "@/store/useSettingsStore";
import {
  Sparkles,
  MessageSquare,
  FileCode2,
  AlertTriangle,
  KeyRound,
  ArrowRight,
  RotateCcw,
} from "lucide-react";

const SUGGESTIONS = [
  {
    title: "Nike Vintage Windbreaker 90s",
    desc: "Thrift find size L in good condition. Bought for Rp 120,000",
    cost: 120000,
  },
  {
    title: "Sony WH-1000XM4 Wireless Headphones",
    desc: "Used 6 months, minor scuff on band, complete with case and cable",
    cost: 1800000,
  },
  {
    title: "Fujifilm X-T20 Mirrorless Camera Body",
    desc: "Secondhand condition 8.5/10 with shutter count under 12k",
    cost: 5500000,
  },
  {
    title: "Uniqlo U Oversized Crew Neck Tee",
    desc: "Deadstock tags on, thrift batch acquisition",
    cost: 50000,
  },
];

const INITIAL_AGENT_STATES: Record<
  AgentKey,
  {
    status: AgentStateStatus;
    statusMessage?: string;
    resultSummary?: string;
  }
> = {
  scout: { status: "idle" },
  analyst: { status: "idle" },
  pricing: { status: "idle" },
  chief: { status: "idle" },
  customer: { status: "idle" },
};

export default function HomePage() {
  const [activeTab, setActiveTab] = useState<"chat" | "parser">("chat");

  // Chat State
  const [messages, setMessages] = useState<MessageData[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Phase 1 Parser State
  const [parserResult, setParserResult] = useState<ParseItemResponse | null>(null);
  const [isParserLoading, setIsParserLoading] = useState(false);
  const [parserError, setParserError] = useState<string | null>(null);

  const { isConfigured, setSettingsOpen, provider } = useSettingsStore();

  // Message counter ref for deterministic IDs
  const msgCountRef = useRef(0);

  // Auto-scroll chat
  useEffect(() => {
    if (activeTab === "chat" && chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isStreaming, activeTab]);

  // Handle Phase 1 Item Parser
  const handleParse = async (payload: ParseItemRequest) => {
    setParserError(null);
    setIsParserLoading(true);

    try {
      const response = await parseItem(payload);
      setParserResult(response);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to parse item.";
      setParserError(msg);
    } finally {
      setIsParserLoading(false);
    }
  };

  // Handle Chat Swarm Orchestration Stream
  const handleChatSubmit = async (payload: {
    text: string;
    imageBase64?: string;
    capitalCost?: number;
  }) => {
    if (isStreaming) return;

    msgCountRef.current += 1;
    const currentCount = msgCountRef.current;
    const userMessageId = `user-msg-${currentCount}`;
    const assistantMessageId = `asst-msg-${currentCount}`;
    const timestamp = "Just now";

    const userMsg: MessageData = {
      id: userMessageId,
      role: "user",
      content: payload.text || (payload.imageBase64 ? "Analyzed attached image" : ""),
      imageBase64: payload.imageBase64,
      capitalCost: payload.capitalCost,
      timestamp,
    };

    const initialAssistantMsg: MessageData = {
      id: assistantMessageId,
      role: "assistant",
      content: "",
      timestamp,
      isStreaming: true,
      agentStates: { ...INITIAL_AGENT_STATES },
    };

    setMessages((prev) => [...prev, userMsg, initialAssistantMsg]);
    setIsStreaming(true);

    // Abort controller for cancellation
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const mapAgentToKey = (agentName?: string): AgentKey | null => {
      if (!agentName) return null;
      const lower = agentName.toLowerCase();
      if (lower.includes("scout")) return "scout";
      if (lower.includes("analyst") || lower.includes("trend")) return "analyst";
      if (lower.includes("pricing")) return "pricing";
      if (lower.includes("chief") || lower.includes("strategist")) return "chief";
      if (lower.includes("customer") || lower.includes("persona")) return "customer";
      return null;
    };

    const updateAssistantMessage = (
      updater: (prev: MessageData) => MessageData
    ) => {
      setMessages((prev) =>
        prev.map((msg) => (msg.id === assistantMessageId ? updater(msg) : msg))
      );
    };

    await streamOrchestration(
      {
        user_input: payload.text,
        image_base64: payload.imageBase64,
        capital_cost: payload.capitalCost,
      },
      (event: OrchestrateStreamEvent) => {
        const agentKey = mapAgentToKey(event.agent);

        if (event.event === "AGENT_START" && agentKey) {
          updateAssistantMessage((msg) => ({
            ...msg,
            agentStates: {
              ...(msg.agentStates || INITIAL_AGENT_STATES),
              [agentKey]: {
                status: "active",
                statusMessage: event.status || "Executing agent node...",
              },
            },
          }));
        } else if (event.event === "AGENT_COMPLETE" && agentKey) {
          updateAssistantMessage((msg) => ({
            ...msg,
            agentStates: {
              ...(msg.agentStates || INITIAL_AGENT_STATES),
              [agentKey]: {
                status: "completed",
                resultSummary: event.result || "Completed",
              },
            },
            marketPrices: event.market_prices || msg.marketPrices,
            scoutSummary: event.scout_summary || msg.scoutSummary,
            trendAnalysis: event.trend_analysis || msg.trendAnalysis,
            pricingStrategy: event.pricing_strategy || msg.pricingStrategy,
            finalStrategy: event.final_strategy || msg.finalStrategy,
            customerVerdict: event.customer_verdict || msg.customerVerdict,
          }));
        } else if (event.event === "FINAL_RESULT") {
          updateAssistantMessage((msg) => ({
            ...msg,
            isStreaming: false,
            parsedItem: event.item_description,
            marketPrices: event.market_prices,
            scoutSummary: event.scout_summary,
            trendAnalysis: event.trend_analysis,
            pricingStrategy: event.pricing_strategy,
            finalStrategy: event.final_strategy,
            customerVerdict: event.customer_verdict,
            errors: event.errors,
            agentStates: {
              scout: { status: "completed", resultSummary: "Aggregated live listings" },
              analyst: { status: "completed", resultSummary: "Trend velocity computed" },
              pricing: { status: "completed", resultSummary: "Calculated 3 tiers & 20% fee" },
              chief: { status: "completed", resultSummary: "Master playbook synthesized" },
              customer: { status: "completed", resultSummary: `Verdict: ${event.customer_verdict || "PASS"}` },
            },
          }));
        } else if (event.event === "ERROR") {
          updateAssistantMessage((msg) => ({
            ...msg,
            isStreaming: false,
            errors: [...(msg.errors || []), event.error || "Execution error encountered."],
          }));
        }
      },
      (error: Error) => {
        updateAssistantMessage((msg) => ({
          ...msg,
          isStreaming: false,
          errors: [...(msg.errors || []), error.message],
        }));
        setIsStreaming(false);
      },
      () => {
        updateAssistantMessage((msg) => ({ ...msg, isStreaming: false }));
        setIsStreaming(false);
      },
      controller.signal
    );
  };

  const handleStopStream = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
    }
  };

  const handleClearChat = () => {
    if (isStreaming) handleStopStream();
    setMessages([]);
  };

  const configured = isConfigured();

  return (
    <div className="flex min-h-screen flex-col bg-[#090a0f] text-zinc-100 font-sans antialiased">
      <Header />
      <BYOKModal />

      <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col px-4 py-6 sm:px-6">
        {/* Navigation Tabs */}
        <div className="mb-6 flex items-center justify-between border-b border-zinc-800/80 pb-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setActiveTab("chat")}
              className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-medium transition-colors ${
                activeTab === "chat"
                  ? "border border-blue-500/40 bg-blue-950/40 text-blue-200 shadow-xs"
                  : "text-zinc-400 hover:bg-zinc-900/60 hover:text-zinc-200"
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5" />
              <span>5-Agent Swarm Chat</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("parser")}
              className={`flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-medium transition-colors ${
                activeTab === "parser"
                  ? "border border-blue-500/40 bg-blue-950/40 text-blue-200 shadow-xs"
                  : "text-zinc-400 hover:bg-zinc-900/60 hover:text-zinc-200"
              }`}
            >
              <FileCode2 className="h-3.5 w-3.5" />
              <span>Item Description Parser</span>
            </button>
          </div>

          {activeTab === "chat" && messages.length > 0 && (
            <button
              type="button"
              onClick={handleClearChat}
              className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <RotateCcw className="h-3 w-3" />
              <span>Reset Chat</span>
            </button>
          )}
        </div>

        {/* BYOK Warning if unconfigured */}
        {!configured && (
          <div className="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border border-amber-500/40 bg-amber-950/20 p-4 text-xs text-amber-200">
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-amber-300">
                  BYOK Configuration Notice:
                </span>{" "}
                Currently using <code className="bg-amber-950/80 px-1 py-0.5 rounded font-mono text-amber-200">{provider}</code> without an API key. Add your key in Settings or switch to Mock Mode for zero-cost simulated testing.
              </div>
            </div>
            <button
              type="button"
              onClick={() => setSettingsOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg bg-amber-500/20 border border-amber-500/40 px-3 py-1.5 text-xs font-medium text-amber-200 hover:bg-amber-500/30 shrink-0 transition-colors"
            >
              <KeyRound className="h-3.5 w-3.5" />
              <span>Configure BYOK</span>
            </button>
          </div>
        )}

        {/* Tab 1: 5-Agent Swarm Chat UI */}
        {activeTab === "chat" && (
          <div className="flex flex-1 flex-col justify-between space-y-6">
            {/* Messages Area */}
            {messages.length === 0 ? (
              <div className="my-auto flex flex-col items-center justify-center text-center py-12">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-blue-500/30 bg-blue-950/40 text-blue-400 mb-4 shadow-sm">
                  <Sparkles className="h-6 w-6" />
                </div>
                <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                  Reseller AI Multi-Agent Swarm
                </h2>
                <p className="mt-2 max-w-md text-xs sm:text-sm text-zinc-400 leading-relaxed">
                  Provide a secondhand thrift find or item photo. 5 autonomous agents will scrape live listings (Tokopedia, Shopee, FB Marketplace), compute 3-tier margins, synthesize listing strategy, and deliver a BUY/PASS verdict.
                </p>

                {/* Suggestions Grid */}
                <div className="mt-8 grid w-full max-w-2xl grid-cols-1 sm:grid-cols-2 gap-3 text-left">
                  {SUGGESTIONS.map((item, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() =>
                        handleChatSubmit({
                          text: item.desc,
                          capitalCost: item.cost,
                        })
                      }
                      className="group rounded-xl border border-zinc-800 bg-[#0d0f17]/70 p-3.5 hover:border-blue-500/50 hover:bg-blue-950/10 transition-all text-xs"
                    >
                      <div className="flex items-center justify-between font-medium text-zinc-200 group-hover:text-blue-300">
                        <span>{item.title}</span>
                        <ArrowRight className="h-3.5 w-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                      <p className="mt-1 text-[11px] text-zinc-400 line-clamp-2">
                        {item.desc}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex-1 space-y-4 overflow-y-auto">
                {messages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))}
                <div ref={chatBottomRef} />
              </div>
            )}

            {/* Chat Input Container */}
            <div className="sticky bottom-4 z-20 pt-2">
              <ChatInput
                onSubmit={handleChatSubmit}
                isLoading={isStreaming}
                onStop={handleStopStream}
              />
            </div>
          </div>
        )}

        {/* Tab 2: Item Description Parser View (Phase 1 Baseline) */}
        {activeTab === "parser" && (
          <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            <div className="lg:col-span-6 space-y-6">
              <ItemParserInput onParse={handleParse} isLoading={isParserLoading} />
            </div>

            <div className="lg:col-span-6 space-y-4">
              {parserError && (
                <div className="rounded-xl border border-rose-800/60 bg-rose-950/30 p-4 text-xs text-rose-200 space-y-2">
                  <div className="flex items-center gap-2 font-semibold text-rose-300">
                    <AlertTriangle className="h-4 w-4 text-rose-400" />
                    <span>Parsing Error</span>
                  </div>
                  <p className="font-mono text-[11px] bg-rose-950/60 p-2.5 rounded border border-rose-900/50">
                    {parserError}
                  </p>
                </div>
              )}

              {isParserLoading && (
                <div className="rounded-xl border border-zinc-800 bg-[#10121d] p-5 space-y-4 animate-pulse">
                  <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
                    <div className="h-4 w-36 rounded bg-zinc-800" />
                    <div className="h-6 w-20 rounded bg-zinc-800" />
                  </div>
                  <div className="h-5 w-3/4 rounded bg-zinc-800" />
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="h-16 rounded-lg bg-zinc-800/60" />
                    <div className="h-16 rounded-lg bg-zinc-800/60" />
                  </div>
                </div>
              )}

              {parserResult && !isParserLoading && (
                <ItemResultCard
                  item={parserResult.item}
                  providerUsed={parserResult.provider_used}
                  modelUsed={parserResult.model_used}
                />
              )}
            </div>
          </section>
        )}
      </main>

      {/* Clean Footer */}
      <footer className="border-t border-zinc-800/80 bg-[#090a0f] py-4 text-center text-xs text-zinc-500">
        <div className="mx-auto max-w-5xl px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>Reseller AI Swarm Engine • Phase 4 Frontend Streaming</span>
          <span className="font-mono text-[11px]">Next.js 16 + FastAPI SSE + LangGraph</span>
        </div>
      </footer>
    </div>
  );
}
