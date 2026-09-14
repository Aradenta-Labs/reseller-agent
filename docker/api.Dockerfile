FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PORT=8000

# Install essential system dependencies and Playwright browser libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and app directory
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /ms-playwright && \
    chown -R appuser:appuser /app /ms-playwright

WORKDIR /app

# Copy dependency specifications
COPY apps/api/requirements.txt /app/requirements.txt

# Install python dependencies
RUN pip install --upgrade pip && \
    pip install -r /app/requirements.txt

# Install Playwright chromium browser binaries and system deps
RUN playwright install --with-deps chromium

# Copy API application source code
COPY apps/api/src /app/src

# Switch to non-root user
USER appuser

EXPOSE 8000

# Run FastAPI backend with Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
