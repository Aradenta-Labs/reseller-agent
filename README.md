# Reseller AI Assistant

A web-based chat platform that helps resellers decide whether an item is worth buying for resale. You describe or photograph an item, and a swarm of 5 specialized AI agents analyzes market prices, trends, platform fees, and consumer demand to give you a concrete **BUY** or **PASS** verdict.

## How It Works

The platform uses a multi-agent pipeline built on LangGraph. Each agent handles a distinct task:

| Agent | Role |
|---|---|
| **Market Scout** | Scrapes live prices from Tokopedia, Shopee, and Facebook Marketplace using Playwright |
| **Trend Analyst** | Evaluates purchase urgency by analyzing demand signals and hype cycles |
| **Pricing Strategist** | Calculates profit margins across strategies (fast sale, patient sale, offline) factoring in the 20% platform fee |
| **Chief Strategist** | Synthesizes all data into a step-by-step action plan |
| **Customer Persona** | Acts as a skeptical buyer and delivers the final BUY / PASS judgment |

Agents 1 and 2 run in parallel. Their outputs flow into Agent 3, then sequentially through 4 and 5.

## Key Features

- **Chat interface**: Send text descriptions or screenshots of items you are considering.
- **BYOK (Bring Your Own Key)**: Use your own OpenAI or Anthropic API key. No keys are stored on the server.
- **Real-time streaming**: Watch each agent's progress live as the analysis runs.
- **Platform-aware pricing**: Supports Tokopedia, Shopee, and Facebook Marketplace as both data sources and selling channels.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), Tailwind CSS, Zustand |
| Backend | Python, FastAPI |
| Agent Orchestration | LangGraph, LiteLLM |
| Data Acquisition | Playwright (with stealth), Tavily (fallback) |
| Streaming | Server-Sent Events (SSE) |

## Project Structure

```
reseller-agent/
├── apps/
│   ├── web/          # Next.js frontend
│   └── api/          # FastAPI backend
├── docs/
│   ├── PRD.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── AGENT_WORKFLOWS.md
│   ├── ROADMAP.md
│   └── v1/plan/      # Phase-by-phase implementation plans
└── AGENTS.md         # AI agent instructions for this repo
```

## Development Phases

| Phase | Focus | Status |
|---|---|---|
| 1 | Foundation & BYOK infrastructure | Planned |
| 2 | Data acquisition (Playwright scrapers) | Planned |
| 3 | Agent swarm & LangGraph orchestration | Planned |
| 4 | Chat UI & real-time streaming | Planned |
| 5 | Testing, hardening & deployment | Planned |

See `docs/v1/plan/` for the detailed implementation plan for each phase.

## Getting Started

> Prerequisites: Python 3.11+, Node.js 20+, uv or Poetry

```bash
# Clone the repo
git clone https://github.com/Aradenta-Labs/reseller-agent.git
cd reseller-agent

# Install API dependencies
cd apps/api
pip install -r requirements.txt
playwright install chromium

# Install web dependencies
cd ../web
npm install

# Run locally
cd ../api && uvicorn src.main:app --reload   # API on :8000
cd ../web && npm run dev                      # UI on :3000
```

## AI Agent Setup (for contributors)

This repo uses [AGENTS.md](./AGENTS.md) to instruct AI coding agents. Before proposing changes, agents must:
1. Run `centmem recall` to load project context.
2. Apply `antislop` rules when generating UI code.
3. Use the appropriate domain skills for FastAPI, Next.js, Playwright, or LangGraph work.

## License

MIT
