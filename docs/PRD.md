# Product Requirements Document (PRD): Reseller AI Assistant

## 1. Product Overview
The Reseller AI Assistant is a web-based chat platform designed to help resellers evaluate whether a specific item is worth buying for resale. By leveraging a swarm of 5 specialized AI agents, the platform analyzes market prices, trends, platform fees, and consumer psychology to provide a definitive "buy" or "pass" recommendation.

## 2. Target Audience
- Individual resellers, thrifters, and dropshippers.
- Small business owners looking to validate inventory purchases before committing capital.

## 3. Core Features & User Experience
### 3.1 Chat-Based Interface
- Users interact with the platform via a conversational chat interface.
- **Inputs supported:** 
  - Text descriptions (e.g., "Found a used iPhone 13 Pro 128GB for $400, should I buy it?").
  - Screenshots/Images (e.g., a photo of a thrift store find or an online listing).

### 3.2 Bring Your Own Key (BYOK)
- To manage AI inference costs and provide flexibility, users must provide their own API keys.
- Supported providers: OpenAI (GPT-4o) and Anthropic (Claude 3.5 Sonnet).

## 4. Multi-Agent Swarm (The 5 Agents)
The core value is delivered by a robust multi-agent orchestration pipeline.

### Agent 1: The Market Scout
- **Role:** Finds the current market price of the item.
- **Mechanism:** Uses Browser Automation (e.g., Playwright) to scrape live or recent pricing data from target platforms (Tokopedia, Shopee, Facebook Marketplace).
- **Goal:** Determine the realistic selling price to see if the user's capital investment makes sense.

### Agent 2: The Trend Analyst
- **Role:** Evaluates market demand.
- **Metric:** Analyzes if "people have an urge to buy this item soon" (measuring velocity, seasonal demand, or hype).
- **Mechanism:** Synthesizes web search data, social sentiment, and general knowledge regarding the item's current cultural relevance.

### Agent 3: The Pricing Strategist
- **Role:** Calculates potential profit margins and pricing tiers.
- **Mechanism:** 
  - Factors in a flat ~20% platform fee for e-commerce (Tokopedia/Shopee).
  - Calculates margins for different strategies: Fast sale (undercutting), maximum profit (waiting for the right buyer), offline vs. online sales.

### Agent 4: The Chief Strategist
- **Role:** The synthesizer.
- **Mechanism:** Reviews the data gathered by Agents 1, 2, and 3. Proposes concrete selling strategies, highlights risks, and outlines the step-by-step approach to selling the item successfully.

### Agent 5: The Customer Persona
- **Role:** The ultimate judge.
- **Mechanism:** Adopts the persona of a skeptical but interested buyer. Reviews the Chief Strategist's proposed price and strategy and gives a final judgment: "At this price and condition, I would/would not buy this." It serves as a reality check.

## 5. Non-Functional Requirements
- **Robustness:** Browser automation must include anti-bot bypass mechanisms or graceful fallbacks if platforms heavily block scraping.
- **Extensibility:** The agent graph should be modular so new platforms or agents can be added later.
- **Performance:** As 5 agents will run (partially in parallel, partially sequential), the UI must provide real-time streaming updates (e.g., "Agent 1 is scanning Tokopedia...") to keep the user engaged during processing.
