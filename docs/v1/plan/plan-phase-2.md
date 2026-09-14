# Phase 2 Implementation Plan: Data Acquisition & The Scout

This document details the actionable engineering steps for Phase 2. The core objective is to build a robust scraping layer that can extract pricing data from target e-commerce platforms using browser automation.

## 1. Directory Structure Additions

```text
reseller-agent/
├── apps/
│   └── api/
│       └── src/
│           └── scrapers/     # Playwright scraping logic
│               ├── base.py   # Base scraper interface
│               ├── shopee.py
│               ├── tokped.py
│               └── fb.py
```

## 2. Step-by-Step Implementation

### Step 2.1: Browser Automation Environment Setup
1. **Install Dependencies:**
   - In `apps/api`, run `pip install playwright playwright-stealth`.
   - Run `playwright install chromium` to install the required browser binaries.
   - Install `bs4` (BeautifulSoup) for robust HTML parsing if needed.

### Step 2.2: The Base Scraper Interface
1. **Define `base.py`:**
   - Create an abstract class or common interface that standardizes inputs and outputs.
   - **Input:** `search_term` (string)
   - **Output:** A structured Pydantic model:
     ```python
     class ScrapeResult(BaseModel):
         platform: str
         lowest_price: float
         highest_price: float
         average_price: float
         top_listings: List[dict] # {title, price, url}
     ```

### Step 2.3: Implementing Platform Scrapers
*Note: Platform DOMs change frequently. Use robust CSS selectors or evaluate injecting JS to read state/props where possible.*

1. **Tokopedia Scraper (`tokped.py`):**
   - Initialize Playwright context with `playwright-stealth`.
   - Navigate to `https://www.tokopedia.com/search?q={term}`.
   - Implement logic to wait for product cards to load.
   - Extract titles and prices, handling dynamic scrolling if necessary to get a representative sample (e.g., top 10 results).
2. **Shopee Scraper (`shopee.py`):**
   - Navigate to `https://shopee.co.id/search?keyword={term}`.
   - *Challenge:* Shopee relies heavily on API calls under the hood and aggressive bot blocking. 
   - Ensure the scraper waits for network idle and successfully extracts pricing from the loaded DOM.
3. **Facebook Marketplace Scraper (`fb.py`):**
   - Navigate to `https://www.facebook.com/marketplace/search/?query={term}`.
   - *Challenge:* Facebook often requires login. If building a stateless bot, test if unauthenticated search yields enough data. If not, consider a fallback or requiring a dummy session cookie.

### Step 2.4: Agent 1 (Market Scout) Integration
1. **Create the Tool:**
   - Wrap the scraping logic into a function that the LLM can call as a tool.
   - Example signature: `def search_market_prices(item_name: str) -> dict`
2. **LLM Orchestration:**
   - Update the `/api/parse-item` (or create a new `/api/analyze` endpoint) to trigger Agent 1.
   - The LLM receives the `ItemDescription` (from Phase 1), formulates the best search query, and calls `search_market_prices`.

### Step 2.5: Anti-Bot & Fallback Strategies
1. **Error Handling:**
   - If Playwright times out or is blocked by Cloudflare/Datadome, return a graceful error state rather than crashing the backend.
2. **Fallback:**
   - If direct scraping fails, fall back to a generic web search tool (e.g., using `Tavily` or `Serper.dev` API if integrated later) to attempt finding price data via indexed pages.

## 3. Definition of Done for Phase 2
- [ ] Playwright is successfully integrated into the FastAPI backend.
- [ ] The `tokped.py`, `shopee.py`, and `fb.py` modules can successfully extract at least 5 prices for a given search term without immediately being blocked.
- [ ] The system calculates the Lowest, Highest, and Average price accurately from the extracted data.
- [ ] Agent 1 (The Market Scout) can be invoked by the LLM to run these scripts and return the structured `ScrapeResult`.

## 4. Next Steps (Proceed to Phase 3)
Once the data acquisition layer is stable, Phase 3 will focus on building the remaining agents (Trend Analyst, Pricing Strategist, etc.) and orchestrating them using LangGraph.
