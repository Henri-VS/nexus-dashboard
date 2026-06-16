#!/usr/bin/env bash
# Nexus Dashboard — startup script (Linux / macOS)
# Detects your local network IP automatically and starts Nexus.
# Usage: ./start.sh
set -e

# ── Detect local IP ────────────────────────────────────────────
HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}')

# macOS fallback (hostname -I not available)
if [ -z "$HOST_IP" ]; then
  HOST_IP=$(ipconfig getifaddr en0 2>/dev/null)
fi

# Last resort
if [ -z "$HOST_IP" ]; then
  HOST_IP="localhost"
  echo "Warning: could not detect local IP, falling back to localhost"
  echo "Other devices on your network won't be able to reach the dashboard."
  echo "Set HOST_IP manually in your .env file if needed."
  echo ""
fi

export HOST_IP

# ── Check .env exists ──────────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "No .env file found."
  echo "Run: cp .env.example .env"
  echo "Then edit .env and set NEXUS_SECRET_KEY."
  exit 1
fi

# ── Validate OBSIDIAN_VAULT_PATH if set ────────────────────────
VAULT_PATH=$(grep -E '^OBSIDIAN_VAULT_PATH=' .env 2>/dev/null | cut -d= -f2-)
if [ -n "$VAULT_PATH" ] && [ ! -d "$VAULT_PATH" ]; then
  echo ""
  echo "Warning: OBSIDIAN_VAULT_PATH is set to '$VAULT_PATH' but that directory"
  echo "does not exist. The vault mount will be empty. Check your .env."
  echo ""
fi

# ── Start ──────────────────────────────────────────────────────
echo "Starting Nexus Dashboard..."
echo ""
docker compose -f docker-compose-hub.yml up -d

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Nexus is running"
echo ""
echo " Dashboard  →  http://${HOST_IP}:3000"
echo " API        →  http://${HOST_IP}:8088"
echo " Excalidraw →  http://${HOST_IP}:3002"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To stop:  docker compose -f docker-compose-hub.yml down"
echo "To update: docker compose -f docker-compose-hub.yml pull && ./start.sh"
