# System Architecture

## 1. High-Level Architecture
The system follows a client-server model with a heavily AI-driven backend focusing on agent orchestration and browser automation.

### 1.1 Frontend (Client)
- **Framework:** Next.js (React) or Vue.js.
- **UI Components:** Chat interface capable of handling text, image uploads (for vision models), and streaming text responses.
- **State Management:** Manages the user's BYOK (API Keys) securely (stored locally or in encrypted session state).

### 1.2 Backend (API & Orchestration)
- **Framework:** Python (FastAPI).
- **Agent Framework:** **LangGraph** (Highly recommended for robust, cyclic, and stateful multi-agent workflows) or **CrewAI**.
- **LLM Gateway:** `LiteLLM` to standardize API calls between OpenAI and Anthropic formats.

### 1.3 Data Acquisition Layer (Agent 1 Tools)
- **Browser Automation:** Playwright with Stealth plugins.
- **Search API Fallback:** Tavily or Serper.dev in case direct browser automation is temporarily blocked by Cloudflare/Datadome on Tokopedia/Shopee.

## 2. Infrastructure & Deployment
- **Web App Hosting:** Vercel or Railway (for Next.js).
- **Backend Hosting:** Render, Railway, or AWS ECS. (Must support running headless browsers for Playwright).
- **Database:** PostgreSQL (via Supabase or Neon) to store chat history, user sessions, and historical item analyses.

## 3. Data Flow (Request Lifecycle)
1. **Input:** User sends a text/image via the Frontend chat, along with their API key.
2. **Vision Processing (if image):** The backend uses GPT-4o / Claude 3.5 to extract the item name, condition, and details from the image.
3. **Orchestration Trigger:** LangGraph state machine is initialized.
4. **Execution:**
   - *Node A:* Agent 1 runs Playwright scripts to search Tokopedia/Shopee/FB Marketplace.
   - *Node B:* Agent 2 runs web searches for trend analysis.
   - *(Nodes A & B can run in parallel)*
   - *Node C:* Agent 3 takes output from A & B, applies the 20% fee math, and calculates margins.
   - *Node D:* Agent 4 takes all previous state and writes the strategic summary.
   - *Node E:* Agent 5 reviews Agent 4's summary and outputs the final verdict.
5. **Streaming Output:** Throughout the graph execution, state updates and agent thoughts are streamed back to the Frontend via Server-Sent Events (SSE) or WebSockets.
