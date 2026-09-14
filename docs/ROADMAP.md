# Development Roadmap: Reseller AI Assistant

This roadmap outlines the step-by-step plan to build, test, and deploy the Reseller AI Assistant. The development is divided into 5 logical phases, prioritizing core infrastructure and data acquisition before moving to complex orchestration and UI.

## Phase 1: Foundation & Infrastructure (Week 1)
**Goal:** Set up the core repositories, define the tech stack, and implement the BYOK (Bring Your Own Key) architecture.

- [ ] **Repository Setup:** Initialize the monorepo (or separate frontend/backend repos).
- [ ] **Backend Initialization:** Set up Python FastAPI with basic routing and dependency management (Poetry/Pipenv).
- [ ] **Frontend Initialization:** Set up Next.js (React) with Tailwind CSS.
- [ ] **BYOK Integration:** 
  - Create secure input fields on the frontend for OpenAI/Anthropic API keys.
  - Implement secure, temporary session storage for these keys on the backend.
  - Integrate `LiteLLM` to handle routing to either OpenAI or Anthropic seamlessly.
- [ ] **Vision Parser (Pre-requisite):** Create a simple LLM endpoint that accepts an image/text and extracts the normalized `item_description`.

## Phase 2: Data Acquisition & The Scout (Week 2)
**Goal:** Build the hardest technical component—extracting live data from e-commerce platforms.

- [ ] **Playwright Setup:** Integrate Playwright with Python and configure stealth plugins (e.g., `playwright-stealth`) to bypass basic bot detection.
- [ ] **Scraping Modules:**
  - Build Tokopedia search & price extraction.
  - Build Shopee search & price extraction.
  - Build Facebook Marketplace search & price extraction.
- [ ] **Agent 1 (Market Scout) Implementation:** Wrap the scraping modules into an LLM tool. Give Agent 1 the ability to search, filter out spam, and return structured pricing data (Lowest, Highest, Average).

## Phase 3: Swarm Logic & Orchestration (Week 3)
**Goal:** Develop the remaining agents and connect them using a state graph.

- [ ] **Agent 2 (Trend Analyst):** Integrate a web search tool (e.g., Tavily/Serper) and prompt it to evaluate purchase urgency and trends.
- [ ] **Agent 3 (Pricing Strategist):** Implement the financial logic (20% platform fee deduction, multi-strategy margin calculation).
- [ ] **Agent 4 (Chief Strategist):** Prompt engineering to synthesize outputs from Agents 1, 2, and 3 into an actionable plan.
- [ ] **Agent 5 (Customer Persona):** Prompt engineering to provide the final "Buy/Pass" judgment based on Agent 4's plan.
- [ ] **LangGraph Orchestration:** 
  - Define the `ResellerState` object.
  - Build the graph: `Input -> (Agent 1 & Agent 2) -> Agent 3 -> Agent 4 -> Agent 5`.
  - Ensure state passes correctly between nodes.

## Phase 4: Frontend Chat & Real-time Streaming (Week 4)
**Goal:** Build a smooth, engaging user experience that masks the latency of multi-agent processing.

- [ ] **Chat UI:** Build a conversational interface supporting text inputs and image uploads.
- [ ] **Streaming Infrastructure (SSE/WebSockets):** Implement Server-Sent Events in FastAPI to stream updates to the frontend.
- [ ] **Agent Status Indicators:** Update the UI to show real-time progress (e.g., *“🔎 Agent 1 is scraping Tokopedia...”* -> *“📈 Agent 2 is checking trends...”*).
- [ ] **Result Rendering:** Format the final output cleanly with Markdown, highlighting the pricing strategy and the final Buy/Pass verdict.

## Phase 5: Testing, Hardening & Deployment (Week 5)
**Goal:** Ensure the system is robust against edge cases and deploy it to the cloud.

- [ ] **Anti-Bot Hardening:** Test the Playwright scrapers heavily. Implement fallbacks (e.g., using Google Search `site:tokopedia.com` if direct scraping fails).
- [ ] **Prompt Tuning:** Refine agent prompts to prevent hallucinations and ensure math (Agent 3) is consistently accurate.
- [ ] **Deployment:**
  - Deploy Frontend to Vercel.
  - Deploy Backend to Render, Railway, or an AWS EC2/ECS instance (must use an environment/Docker container that supports headless browsers and Playwright dependencies).
- [ ] **End-to-End Testing:** Conduct real-world tests with actual thrift store items to validate the accuracy of the advice.
