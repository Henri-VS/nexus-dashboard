#!/usr/bin/env bash
# Nexus Dashboard — one-line installer
# Usage: curl -fsSL https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/install.sh | bash
set -e

BASE="https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main"
DIR="nexus"

# ── Colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; RESET='\033[0m'
info()  { echo -e "${CYAN}▸ $*${RESET}"; }
ok()    { echo -e "${GREEN}✓ $*${RESET}"; }
fail()  { echo -e "${RED}✗ $*${RESET}"; exit 1; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Nexus Dashboard — installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Check Docker ───────────────────────────────────────────────────────────
info "Checking Docker..."
if ! command -v docker &>/dev/null; then
  fail "Docker not found. Install it first: https://docs.docker.com/engine/install/"
fi
ok "Docker found: $(docker --version)"

# ── Check Docker daemon is running and accessible ──────────────────────────
DOCKER_INFO=$(docker info 2>&1)
if echo "$DOCKER_INFO" | grep -q "permission denied"; then
  echo ""
  echo -e "${RED}✗ Permission denied — your user can't access the Docker socket.${RESET}"
  echo ""
  echo "  Fix: add your user to the docker group, then re-run this script."
  echo ""
  echo "    sudo usermod -aG docker \$USER"
  echo "    newgrp docker"
  echo ""
  exit 1
elif echo "$DOCKER_INFO" | grep -q "Cannot connect\|no such file\|Is the docker daemon running"; then
  echo ""
  echo -e "${RED}✗ Docker daemon is not running.${RESET}"
  echo ""
  echo "    sudo systemctl start docker"
  echo "    sudo systemctl enable docker   # auto-start on boot"
  echo ""
  exit 1
fi
ok "Docker daemon is running"

# ── Check Docker Compose v2 ────────────────────────────────────────────────
if ! docker compose version &>/dev/null 2>&1; then
  fail "Docker Compose v2 not found. Install: https://docs.docker.com/compose/install/"
fi
ok "Docker Compose found: $(docker compose version --short 2>/dev/null || docker compose version | head -1)"

# ── Create install directory ───────────────────────────────────────────────
info "Creating ./${DIR}/ directory..."
mkdir -p "$DIR/data"
cd "$DIR"
ok "Working in $(pwd)"

# ── Download files ─────────────────────────────────────────────────────────
info "Downloading docker-compose-hub.yml..."
curl -fsSL "$BASE/docker-compose-hub.yml" -o docker-compose-hub.yml

info "Downloading .env.example..."
curl -fsSL "$BASE/backend/.env.example" -o .env.example

info "Downloading start.sh..."
curl -fsSL "$BASE/start.sh" -o start.sh
chmod +x start.sh

ok "Files downloaded"

# ── Create .env ────────────────────────────────────────────────────────────
if [ ! -f ".env" ]; then
  cp .env.example .env

  # Generate a random 32-char key
  if KEY=$(tr -dc 'a-zA-Z0-9' </dev/urandom 2>/dev/null | head -c 32) && [ -n "$KEY" ]; then
    :
  elif KEY=$(date +%s%N 2>/dev/null | sha256sum | head -c 32) && [ -n "$KEY" ]; then
    :
  else
    KEY="please-change-this-key-$(date +%s)"
  fi

  # Write key into .env (replace the empty NEXUS_SECRET_KEY= line)
  if sed --version 2>/dev/null | grep -q GNU; then
    sed -i "s/^NEXUS_SECRET_KEY=.*/NEXUS_SECRET_KEY=${KEY}/" .env
  else
    # macOS sed
    sed -i '' "s/^NEXUS_SECRET_KEY=.*/NEXUS_SECRET_KEY=${KEY}/" .env
  fi

  ok "Created .env with auto-generated secret key"
else
  ok ".env already exists — skipping"
fi

# ── Detect LAN IP ──────────────────────────────────────────────────────────
HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}')

# macOS fallback
if [ -z "$HOST_IP" ]; then
  HOST_IP=$(ipconfig getifaddr en0 2>/dev/null)
fi

# Last resort
if [ -z "$HOST_IP" ]; then
  HOST_IP="localhost"
  echo ""
  echo "  Warning: could not detect local IP — falling back to localhost."
  echo "  Other devices on your network won't be able to reach the dashboard."
  echo "  Set HOST_IP= in nexus/.env if needed."
fi

export HOST_IP

# ── Start ──────────────────────────────────────────────────────────────────
echo ""
info "Starting Nexus (pulling images on first run — may take 1–2 minutes)..."
echo ""
docker compose -f docker-compose-hub.yml up -d

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e " ${GREEN}Nexus is running${RESET}"
echo ""
echo "  Dashboard  →  http://${HOST_IP}:3000"
echo "  API        →  http://${HOST_IP}:8088"
echo ""
echo "  Config:  edit nexus/.env and run ./start.sh to apply"
echo "  Stop:    docker compose -f docker-compose-hub.yml down"
echo "  Update:  docker compose -f docker-compose-hub.yml pull && ./start.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
