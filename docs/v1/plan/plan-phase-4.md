# Phase 4 Implementation Plan: Frontend Chat & Real-time Streaming

This document outlines the actionable engineering steps for Phase 4. The objective is to build a responsive, engaging chat interface that masks the inherent latency of multi-agent workflows by streaming real-time status updates and agent thoughts back to the user.

## 1. Directory Structure Additions

```text
reseller-agent/
├── apps/
│   ├── api/
│   │   └── src/
│   │       └── routes/
│   │           └── stream.py       # FastAPI SSE endpoints
│   └── web/
│       ├── components/
│       │   ├── Chat/
│       │   │   ├── ChatMessage.tsx
│       │   │   ├── ChatInput.tsx
│       │   │   └── AgentStatusBadge.tsx
│       │   └── Settings/
│       │       └── BYOKModal.tsx
│       └── app/
│           └── page.tsx            # Main chat interface
```

## 2. Step-by-Step Implementation

### Step 2.1: Backend Streaming Implementation (FastAPI)
1. **Server-Sent Events (SSE):**
   - In `apps/api/src/routes/stream.py`, create a new endpoint `POST /api/orchestrate/stream`.
   - Use FastAPI's `StreamingResponse` to push JSON events as the LangGraph executes.
2. **Modify LangGraph Execution:**
   - Update the workflow invocation from Phase 3 to use `.astream_events()` or yield state updates at each node boundary.
   - **Event Types to emit:**
     - `AGENT_START`: e.g., `{"agent": "Market Scout", "status": "Searching Tokopedia..."}`
     - `AGENT_COMPLETE`: e.g., `{"agent": "Market Scout", "result": "Found 12 listings."}`
     - `FINAL_RESULT`: e.g., `{"verdict": "BUY", "strategy": "..."}`

### Step 2.2: Frontend UI Components (Next.js)
*Note: Follow the principles of `antislop`—ensure the UI has a distinct identity, uses whitespace effectively, and avoids generic AI slop patterns like unnecessary glows or pill-shaped everything.*

1. **BYOK Modal (`BYOKModal.tsx`):**
   - Create a clean, accessible modal for users to input their OpenAI/Anthropic keys.
   - Store these securely in memory (e.g., using Zustand). Do not persist raw keys to `localStorage` unless explicitly requested and warned.
2. **Chat Input (`ChatInput.tsx`):**
   - Implement a text area that auto-expands.
   - Include a file upload button for images (thrift store finds).
   - Ensure keyboard accessibility (Enter to submit, Shift+Enter for newline).
3. **Chat Message (`ChatMessage.tsx`):**
   - Differentiate user messages from AI messages visually (e.g., subtle background shade difference, not heavy shadows).
   - Render Markdown for the final Chief Strategist output.

### Step 2.3: Frontend Streaming Consumption
1. **Fetch API for SSE:**
   - In the main chat container, write a function to call `/api/orchestrate/stream`.
   - Use the native browser API (`fetch` or `EventSource`) to consume the readable stream.
   - *Crucial:* Pass the BYOK headers (`X-API-Key`, `X-LLM-Provider`) in the initial request.
2. **State Updates:**
   - As `AGENT_START` events arrive, display a pulsing `AgentStatusBadge` (e.g., "Market Scout is active...").
   - As `AGENT_COMPLETE` events arrive, turn the badge green and append a brief summary to the chat log.
   - When `FINAL_RESULT` arrives, render the full Markdown strategy and the final "BUY/PASS" verdict prominently.

### Step 2.4: UX & Resilience
1. **Loading & Error States:**
   - Implement graceful error handling if an agent fails (e.g., Playwright timeout). The stream should emit an `ERROR` event, and the UI should display it cleanly, offering a "Retry" button.
2. **Mobile Responsiveness:**
   - Ensure the chat interface is fully responsive. The input bar must not be obscured by the mobile keyboard, and status badges must wrap correctly on small screens.

## 3. Definition of Done for Phase 4
- [ ] FastAPI endpoint `/api/orchestrate/stream` successfully emits SSE events as graph nodes execute.
- [ ] Next.js frontend connects to the stream and correctly passes BYOK headers.
- [ ] The UI displays real-time agent status indicators (e.g., "Agent 2 is analyzing trends") that update sequentially.
- [ ] The final Markdown response and "Buy/Pass" verdict render correctly.
- [ ] The UI meets `antislop` standards: clear typography, no unnecessary glassmorphism, fully responsive, and accessible by keyboard.

## 4. Next Steps (Proceed to Phase 5)
With the application fully functional end-to-end, Phase 5 will focus on hardening the scrapers, tuning the prompts for accuracy, and deploying the application to production environments.
