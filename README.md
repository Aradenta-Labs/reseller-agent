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

## Getting Started (Local Development)

### Prerequisites

- **Python 3.11+** with `uv` or `poetry` for package management
- **Node.js 20+** with `npm` for the frontend
- **Playwright Chromium** browsers for scraping
- OpenAI or Anthropic API key (Bring Your Own Key)

### Step-by-Step Setup

#### 1. Clone the Repository

```bash
git clone https://github.com/Aradenta-Labs/reseller-agent.git
cd reseller-agent
```

#### 2. Set Up the Backend (API)

```bash
cd apps/api

# Install Python dependencies using pip
pip install -r requirements.txt

# OR using uv (recommended):
# uv sync

# Install Playwright Chromium browsers
playwright install chromium

# OPTIONAL: Set proxy for scraper resilience (not required)
export SCRAPER_PROXY_URL="http://your-proxy-url"

# Start the FastAPI server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.  
Health check endpoint: `GET http://localhost:8000/api/health`

#### 3. Set Up the Frontend (Web)

Open a new terminal in the same repository root:

```bash
cd apps/web

# Install Node.js dependencies
npm install

# Start the Next.js development server
npm run dev
```

The web interface will be available at `http://localhost:3000`.

#### 4. Configure API Keys (BYOK)

When you open the frontend at `http://localhost:3000`:
1. Click the **"Settings"** icon in the top-right corner.
2. Paste your **OpenAI** (`sk-...`) or **Anthropic** (`sk-...`) API key.
3. The key is stored only in your browser session—never persisted to disk.

#### 5. Use the Application

Once both servers are running:
1. Navigate to `http://localhost:3000`.
2. Either type an item description (e.g., *"iPhone 13 Pro 128GB secondhand"*).
3. Or upload a screenshot/photo of the item.
4. Watch as Agent 1 and Agent 2 run in parallel.
5. View real-time progress updates from Agents 3, 4, and 5.
6. Receive a final **BUY/PASS** verdict with actionable strategy.

### Local Environment Variables (Optional)

The app works without any backend env vars by default. However, for advanced usage:

| Variable | Description | Default |
|---|---|---|
| `SCRAPER_COOLDOWN_SECONDS` | Delay between scrapes to reduce blocking | `3` |
| `TAVILY_API_KEY` | Fallback search engine if Playwright fails | (none) |
| `PORT` | API server port | `8000` |
| `NEXT_PUBLIC_API_URL` | Frontend's API base URL | `http://localhost:8000` |

Create a `.env` file in `apps/api` if needed:
```bash
cat > apps/api/.env << EOF
SCRAPER_COOLDOWN_SECONDS=3
EOF
```

### Troubleshooting

| Issue | Solution |
|---|---|
| `playwright` not found | Run `playwright install chromium` after installing dependencies |
| Scrapers return empty results | Try adding `SCRAPER_PROXY_URL` or wait a few minutes before retrying |
| Browser automation blocked | Ensure latest version of `playwright-stealth` is installed |
| SSE connection timeout | Check that CORS headers are enabled (default: allows localhost:3000) |

## AI Agent Setup (for contributors)

This repo uses [AGENTS.md](./AGENTS.md) to instruct AI coding agents. Before proposing changes, agents must:
1. Run `centmem recall` to load project context.
2. Apply `antislop` rules when generating UI code.
3. Use the appropriate domain skills for FastAPI, Next.js, Playwright, or LangGraph work.

## AI Agent Setup (for contributors)

This repo uses [AGENTS.md](./AGENTS.md) to instruct AI coding agents. Before proposing changes, agents must:
1. Run `centmem recall` to load project context.
2. Apply `antislop` rules when generating UI code.
3. Use the appropriate domain skills for FastAPI, Next.js, Playwright, or LangGraph work.

## License

MIT
