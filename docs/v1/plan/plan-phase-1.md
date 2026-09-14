# Phase 1 Implementation Plan: Foundation & Infrastructure

This document breaks down the Phase 1 roadmap into actionable, verifiable steps for the engineering team. The goal is to establish the monorepo structure, set up the BYOK (Bring Your Own Key) architecture, and build the foundational API and UI scaffolding.

## 1. Directory & Repository Structure

We will use a Turborepo-style monorepo structure to keep the frontend and backend closely aligned.

```text
reseller-agent/
├── apps/
│   ├── web/          # Next.js Frontend
│   └── api/          # FastAPI Backend
├── packages/
│   └── shared/       # Shared TypeScript interfaces (if applicable) or common configs
└── docs/             # Documentation
```

## 2. Step-by-Step Implementation

### Step 2.1: Backend Initialization (FastAPI)
1. **Initialize Environment:**
   - Navigate to `apps/api`.
   - Setup Python environment using `uv` or `Poetry` (Python 3.11+).
2. **Core Dependencies:**
   - Install `fastapi`, `uvicorn`, `pydantic`, `pydantic-settings`.
   - Install `litellm` (for LLM routing) and `instructor` (for structured extraction).
3. **Project Structure (`apps/api/src`):**
   - `/routes`: Define basic health check endpoint `/api/health`.
   - `/services/llm`: Initialize LiteLLM wrapper.
   - `/models`: Define Pydantic models for BYOK credentials.
4. **Validation:**
   - Run `uvicorn src.main:app --reload` and verify `/docs` loads successfully.

### Step 2.2: Frontend Initialization (Next.js)
1. **Initialize Environment:**
   - Navigate to `apps/web`.
   - Run `npx create-next-app@latest .` (App Router, TypeScript, Tailwind CSS).
2. **Core Dependencies:**
   - Install `lucide-react` (icons), `zustand` (state management), and `axios` or configure native `fetch`.
3. **Validation:**
   - Run `npm run dev` and verify the default Next.js landing page loads on `localhost:3000`.

### Step 2.3: BYOK (Bring Your Own Key) Architecture
The system must safely handle user-provided API keys without permanently storing them in a database, relying on encrypted session state or frontend state.

1. **Frontend State (Zustand):**
   - Create a store `useSettingsStore` to hold the `provider` (OpenAI or Anthropic) and the `apiKey`.
   - Create a Settings Modal UI where the user pastes their key.
2. **Backend API Contract:**
   - Ensure all LLM-dependent FastAPI endpoints accept `X-LLM-Provider` and `X-API-Key` headers.
   - *Security Note:* Ensure CORS is configured properly in FastAPI to accept these headers from the Next.js origin.
3. **LiteLLM Integration:**
   - Create a generic completion function in FastAPI that reads the headers and dynamically sets `litellm.api_key` per request.

### Step 2.4: Vision Parser (The First LLM Endpoint)
Before full orchestration, we need to convert unstructured user input (text or images) into a structured `ItemDescription`.

1. **Backend Route (`POST /api/parse-item`):**
   - Accepts a JSON payload with either `text` or `image_base64`.
   - Uses `instructor` with `litellm` to enforce a Pydantic schema:
     ```python
     class ItemDescription(BaseModel):
         name: str
         condition: str
         estimated_retail_price: Optional[float]
         key_features: List[str]
     ```
2. **Frontend Integration:**
   - Build a simple chat input bar that accepts text and image uploads.
   - Wire the submit button to call `/api/parse-item`, passing the BYOK headers.
   - Display the parsed structured JSON on the screen to verify the pipeline works.

## 3. Definition of Done for Phase 1
- [ ] Both FastAPI and Next.js servers run locally without errors.
- [ ] A user can enter an OpenAI or Anthropic API key in the UI.
- [ ] A user can upload an image of an item or type a description.
- [ ] The backend successfully uses the user's API key to extract a structured JSON description of the item and returns it to the frontend.

## 4. Next Steps (Proceed to Phase 2)
Once the Definition of Done is met, the project will move to Phase 2, which involves integrating Playwright to scrape live market data based on the extracted `ItemDescription`.
