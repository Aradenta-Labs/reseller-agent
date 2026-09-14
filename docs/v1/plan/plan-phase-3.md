# Phase 3 Implementation Plan: Swarm Logic & Orchestration

This document details the actionable engineering steps for Phase 3. The objective is to build the core orchestration engine that manages state and routes tasks between the 5 specialized AI agents using LangGraph and LiteLLM.

## 1. Directory Structure Additions

```text
reseller-agent/
├── apps/
│   └── api/
│       └── src/
│           ├── agents/
│           │   ├── __init__.py
│           │   ├── scout.py        # Agent 1: Market Scout
│           │   ├── analyst.py      # Agent 2: Trend Analyst
│           │   ├── strategist.py   # Agent 3: Pricing & Agent 4: Chief
│           │   └── customer.py     # Agent 5: Customer Persona
│           ├── graph/
│           │   ├── __init__.py
│           │   ├── state.py        # TypedDict for ResellerState
│           │   └── workflow.py     # LangGraph compilation
│           └── tools/
│               └── search.py       # Tavily/Serper wrapper for Agent 2
```

## 2. Step-by-Step Implementation

### Step 2.1: Define the Graph State
1. **Create `graph/state.py`:**
   - Define the `ResellerState` using Python's `TypedDict`. This object will flow through all nodes in the graph.
   ```python
   from typing import TypedDict, List, Optional

   class ResellerState(TypedDict):
       user_input: str
       item_description: str
       capital_cost: Optional[float]
       market_prices: List[dict]    # Populated by Agent 1
       trend_analysis: str          # Populated by Agent 2
       pricing_strategy: dict       # Populated by Agent 3
       final_strategy: str          # Populated by Agent 4
       customer_verdict: str        # Populated by Agent 5
   ```

### Step 2.2: Implement Agent Nodes
Each node is a Python function that takes the `ResellerState`, invokes an LLM (via LiteLLM) or a tool, and returns a dictionary to update the state.

1. **Agent 1: Market Scout (`agents/scout.py`)**
   - Receives `item_description`.
   - Calls the Playwright scrapers built in Phase 2.
   - Returns: `{"market_prices": [...]}`
2. **Agent 2: Trend Analyst (`agents/analyst.py`)**
   - Receives `item_description`.
   - Uses a web search tool (e.g., Tavily API) to gauge current hype/urgency.
   - Returns: `{"trend_analysis": "..."}`
3. **Agent 3: Pricing Strategist (`agents/strategist.py`)**
   - Receives `market_prices` and `trend_analysis`.
   - Applies the 20% platform fee calculation logic to find the optimal buying price for a 15% margin.
   - Returns: `{"pricing_strategy": {...}}`
4. **Agent 4: Chief Strategist (`agents/strategist.py`)**
   - Receives all previous state variables.
   - Uses an LLM to synthesize a step-by-step selling plan (where to list, how to photograph, pricing tiers).
   - Returns: `{"final_strategy": "..."}`
5. **Agent 5: Customer Persona (`agents/customer.py`)**
   - Receives `final_strategy`.
   - Uses an LLM prompted as a skeptical buyer to evaluate the proposed listing.
   - Returns: `{"customer_verdict": "BUY" | "PASS"}`

### Step 2.3: Build the LangGraph Workflow
1. **Create `graph/workflow.py`:**
   - Import `StateGraph` from `langgraph.graph`.
   - Initialize the graph: `workflow = StateGraph(ResellerState)`
   - Add nodes:
     ```python
     workflow.add_node("market_scout", run_market_scout)
     workflow.add_node("trend_analyst", run_trend_analyst)
     workflow.add_node("pricing_strategist", run_pricing_strategist)
     workflow.add_node("chief_strategist", run_chief_strategist)
     workflow.add_node("customer_persona", run_customer_persona)
     ```
   - Define Edges (Parallel execution for A1 and A2):
     ```python
     workflow.set_entry_point(["market_scout", "trend_analyst"])
     workflow.add_edge("market_scout", "pricing_strategist")
     workflow.add_edge("trend_analyst", "pricing_strategist")
     workflow.add_edge("pricing_strategist", "chief_strategist")
     workflow.add_edge("chief_strategist", "customer_persona")
     workflow.set_finish_point("customer_persona")
     ```
   - Compile the graph: `app = workflow.compile()`

### Step 2.4: Connect to FastAPI
1. **Create Route (`POST /api/orchestrate`):**
   - Endpoint accepts the user's BYOK credentials and the initial `item_description`.
   - Invokes `app.invoke({"item_description": description})`.
   - *Note:* In this phase, we will return the final state as a JSON response. Real-time streaming (SSE) will be implemented in Phase 4.

## 3. Definition of Done for Phase 3
- [ ] The `ResellerState` object is clearly defined and successfully passes between all nodes.
- [ ] Agents 1 and 2 execute in parallel successfully.
- [ ] Agent 3 accurately calculates margins factoring in the 20% platform fee.
- [ ] The full graph executes from start to finish via a FastAPI endpoint using the user's provided API key.
- [ ] The final JSON response contains the `customer_verdict` and `final_strategy`.

## 4. Next Steps (Proceed to Phase 4)
With the orchestration engine complete, Phase 4 will focus on connecting this graph to the Next.js frontend and implementing Server-Sent Events (SSE) so the user can watch the agents' progress in real-time.
