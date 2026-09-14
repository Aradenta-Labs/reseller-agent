# Phase 5 Implementation Plan: Testing, Hardening & VPS Deployment (Docker)

This document details the actionable engineering steps for Phase 5. The objective is to harden the scrapers against bot detection, tune prompts for accuracy, containerize the full stack with Docker, and deploy to a self-managed VPS (no Vercel, no Render).

## 1. Directory Structure Additions

```text
reseller-agent/
├── docker/
│   ├── api.Dockerfile
│   └── web.Dockerfile
├── deploy/
│   ├── docker-compose.prod.yml
│   ├── Caddyfile
│   ├── .env.example
│   └── deploy.sh
├── apps/
│   ├── api/
│   │   └── .dockerignore
│   └── web/
│       ├── Dockerfile (optional if using docker/api.Dockerfile pattern)
│       └── .dockerignore
└── .github/
    └── workflows/
        └── docker-build.yml
```

## 2. Step-by-Step Implementation

### Step 2.1: Anti-Bot Hardening (Playwright)
1. **Proxy Rotation:**
   - Add optional HTTP/SOCKS proxy support to `apps/api/src/scrapers/base.py` via environment variables (`SCRAPER_PROXY_URL`).
   - If no proxy is available, at minimum randomize browser fingerprints per session.
2. **Session Randomization:**
   - Randomize `user_agent`, `viewport`, `timezone_id`, and `locale` per browser context using `playwright-stealth` and a small built-in pool.
3. **Human-like Behavior:**
   - Add randomized scroll delays and mouse movement simulation before extracting prices.
4. **Fallback Chain (Priority Order):**
   1. Direct Playwright scrape.
   2. If blocked or empty: `Tavily`/`Serper.dev` search for `site:tokopedia.com {term}` results.
   3. If both fail: return a clean `ScrapeError` with a retry-able message, never crash the graph.
5. **Rate Limiting:**
   - Add a configurable cooldown (`SCRAPER_COOLDOWN_SECONDS`, default 3) between searches from the same container to reduce blocking probability.

### Step 2.2: Prompt Tuning & Math Validation
1. **Agent 3 Financial Accuracy:**
   - Add a deterministic Python helper `calculate_pricing()` that the Pricing Strategist MUST call (via tool) instead of doing arithmetic inside the LLM prompt.
   - Unit tests must assert: given market price X, the Fast Sale price includes the 20% fee and still yields >= 15% net margin.
2. **Agent 5 Verdict Consistency:**
   - Enforce structured output (`BUY` | `PASS` | `CONDITIONAL`) using `instructor` + Pydantic.
3. **End-to-End Test Scenarios:**
   - Run 5 real-world item analyses (e.g., secondhand iPhone, Nike shoes, blender, gaming chair, thrift jacket) and manually review outputs for hallucinated prices.
   - Any price quoted without a scraped source URL is treated as a test failure.

### Step 2.3: Dockerizing the Stack
1. **API Image (`docker/api.Dockerfile`):**
   - Base: `python:3.11-slim`.
   - Install system deps required by Playwright (`libnss3`, `libatk-bridge2.0-0`, `libxkbcommon0`, `fonts-liberation`, etc.).
   - Install Python deps from `apps/api/requirements.txt` (or `uv sync` from `pyproject.toml`).
   - Run `playwright install --with-deps chromium`.
   - Non-root user for runtime security.
   - `CMD: uvicorn src.main:app --host 0.0.0.0 --port 8000`
2. **Web Image (`docker/web.Dockerfile`):**
   - Multi-stage build with `node:20-alpine`.
   - Stage 1: `npm ci && npm run build` (Next.js standalone output).
   - Stage 2: `node:20-alpine`, copy `.next/standalone` and `.next/static`.
   - `CMD: node server.js`
   - Set `NEXT_PUBLIC_API_URL` as a build arg so the frontend knows the API base URL.
3. **.dockerignore files:**
   - Exclude `node_modules`, `.next`, `__pycache__`, `.venv`, `tests` (keep tests out of prod images), and `.git`.

### Step 2.4: Production Compose & Reverse Proxy
1. **`deploy/docker-compose.prod.yml`:**
   - Services: `web` (Next.js standalone, port 3000 internal), `api` (Uvicorn, port 8000 internal), `caddy` (public, ports 80/443).
   - `restart: unless-stopped` for all services.
   - Resource limits for the API container (Playwright is memory-hungry): `mem_limit: 2g` minimum.
   - Shared Docker volume for Playwright browser cache (`/ms-playwright`) to speed up restarts.
2. **Caddy Reverse Proxy (`deploy/Caddyfile`):**
   - Automatic HTTPS via Let's Encrypt.
   - Route `/api/*` to the `api` service, everything else to `web`.
   - Enforce HTTP/2 for SSE streaming.
3. **Environment Variables (`.env.example`):**
   - `DOMAIN`, `SCRAPER_PROXY_URL` (optional), `SCRAPER_COOLDOWN_SECONDS`, `TAVILY_API_KEY` (optional fallback), `API_ORIGIN`.
   - Never commit real secrets; Caddy handles TLS automatically.

### Step 2.5: VPS Provisioning & Deployment Script
1. **Server Setup (assume Ubuntu 22.04+ VPS):**
   - Install Docker Engine + Compose plugin, `ufw` allow 22/80/443.
   - Create deploy user, disable password SSH auth (recommended).
2. **`deploy/deploy.sh`:**
   - `git pull` on the VPS (or copy repo via rsync).
   - Build images: `docker compose -f deploy/docker-compose.prod.yml build`.
   - Zero-downtime restart: `docker compose up -d` (Caddy re-validates TLS automatically).
   - Health check loop: curl `/api/health` and `/` until both return 200.
   - Auto-rollback: if health checks fail, `docker compose up -d --force-recreate` previous image tag or `git checkout` previous commit.
3. **CI Build Pipeline (`.github/workflows/docker-build.yml`):**
   - On push to `main`: build both images, run `pytest` inside the API image, push to GitHub Container Registry (ghcr.io).
   - On the VPS, `deploy.sh` pulls from ghcr.io instead of building locally (faster, keeps VPS resources for runtime).

### Step 2.6: Observability & Maintenance
1. **Logs:** `docker compose logs -f` with JSON logging driver and log rotation (`max-size: 10m`).
2. **Health endpoints:** `/api/health` must report scraper status and LLM provider reachability.
3. **Backup:** Nightly cron on the VPS to snapshot the Playwright cache volume and any persisted data.
4. **Watchdog:** Optional systemd timer that runs `docker compose ps` and restarts unhealthy services.

## 3. Definition of Done for Phase 5
- [ ] Scrapers survive basic bot detection on all 3 platforms with fallback chain active.
- [ ] Agent 3 uses deterministic Python math (no LLM arithmetic) and passes margin tests.
- [ ] Both Docker images build cleanly and run locally via `docker compose up`.
- [ ] The app is live on the VPS at `https://<domain>` with valid HTTPS via Caddy.
- [ ] Deploy script performs health checks and rollback on failure.
- [ ] CI builds and pushes images to ghcr.io on every push to `main`.
- [ ] 5 real-world item analyses produce sourced prices and sensible verdicts.

## 4. Post-Deployment
Phase 5 completes the v1 roadmap. Post-launch work:
- Monitor scraper block rates weekly and adjust stealth config.
- Collect user feedback on verdict quality and iterate on agent prompts.
- Evaluate adding more platforms (e.g., OLX, Carousell) using the modular scraper interface.
