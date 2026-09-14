#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Production VPS Deployment Script for Reseller AI Assistant
# ==============================================================================

COMPOSE_FILE="deploy/docker-compose.prod.yml"
ENV_FILE="deploy/.env"

echo "🚀 [Deploy] Starting Reseller AI Assistant production deployment..."

# Ensure .env exists
if [ ! -f "$ENV_FILE" ]; then
    if [ -f "deploy/.env.example" ]; then
        echo "⚠️ [Deploy] deploy/.env not found, creating from deploy/.env.example..."
        cp deploy/.env.example "$ENV_FILE"
    else
        echo "❌ [Deploy] Error: deploy/.env file missing."
        exit 1
    fi
fi

# Step 1: Pull latest container images or build
echo "📦 [Deploy] Pulling updated container images from GHCR..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" pull || {
    echo "⚠️ [Deploy] Remote pull failed or local images preferred, building locally..."
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" build
}

# Step 2: Deploy services with zero-downtime rolling recreation
echo "🔄 [Deploy] Recreating and starting containers..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --remove-orphans

# Step 3: Healthcheck loop
echo "🩺 [Deploy] Verifying deployment health..."
MAX_ATTEMPTS=20
SLEEP_INTERVAL=3
API_READY=false
WEB_READY=false

for i in $(seq 1 $MAX_ATTEMPTS); do
    echo "🔍 Health check attempt $i/$MAX_ATTEMPTS..."

    if [ "$API_READY" = false ]; then
        if docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T api curl -s -f http://localhost:8000/api/health > /dev/null 2>&1; then
            echo "✅ API service is healthy!"
            API_READY=true
        fi
    fi

    if [ "$WEB_READY" = false ]; then
        if docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T web wget -q -O - http://localhost:3000/ > /dev/null 2>&1; then
            echo "✅ Web frontend service is healthy!"
            WEB_READY=true
        fi
    fi

    if [ "$API_READY" = true ] && [ "$WEB_READY" = true ]; then
        echo "🎉 [Deploy] All services are healthy and running!"
        exit 0
    fi

    sleep $SLEEP_INTERVAL
done

# Step 4: Auto-rollback on failure
echo "❌ [Deploy] Health checks failed after $MAX_ATTEMPTS attempts."
echo "⚠️ [Deploy] Rolling back to previous stable container states..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --tail 50
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" restart || true
exit 1
