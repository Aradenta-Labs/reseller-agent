# Reseller AI Assistant: Agent Instructions

Welcome to the Reseller AI Assistant project. When working on this repository, you **MUST** adhere to the following rules and utilize the specified skills to ensure consistency, quality, and architectural integrity.

## Core Mandates

1. **Memory First (`centmem`)**
   - **Before responding or starting a task**, ALWAYS use the `centmem` skill to recall previous decisions, architectural notes, and project context.
   - Run `centmem recall "your task context"` to load context.
   - When you make a structural decision, discover a fact, or reach a milestone, ALWAYS save it using `centmem put` or `centmem set`.

2. **Design Quality (`antislop`)**
   - **Before generating any UI code** for the Next.js frontend, you MUST apply the `antislop` filter rules.
   - The UI must look crafted, deliberate, and free of generic AI styling (no unnecessary glows, pill shapes, or arbitrary gradients).
   - Ensure the UI states (loading, empty, error) are always handled.

## Context-Specific Skills

Invoke the following skills automatically when working on their respective domains:

- **FastAPI / Backend Work:**
  - Invoke `python-fastapi-development`.
  - Enforce clean routing, async execution, and strict Pydantic models for the BYOK integration and orchestration endpoints.

- **Frontend / Chat UI Work:**
  - Invoke `react-nextjs-development`.
  - Use Next.js 14+ App Router, Tailwind CSS, and Server-Sent Events (SSE) for the chat streaming interface.

- **Data Acquisition / Scraping (Phase 2):**
  - Invoke `playwright-skill`.
  - Use Playwright with stealth configurations to robustly scrape Tokopedia, Shopee, and Facebook Marketplace. Implement graceful fallbacks for bot detection.

- **Agent Orchestration (Phase 3):**
  - Invoke `llm-application-dev-langchain-agent`.
  - Follow production-grade LangGraph patterns for managing the 5-agent swarm (`ResellerState`, parallel nodes, and edge transitions).

## Development Phases Reminder
Always check the `/docs/v1/plan/` directory to see which phase is currently active before proposing broad architectural changes.

---
*Failure to use `centmem` to check project state or `antislop` when building UI will result in rejected pull requests and failed tests.*