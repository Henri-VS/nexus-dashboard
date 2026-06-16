# Nexus Dashboard

A self-hosted homelab dashboard. SvelteKit + FastAPI. 100% local — no cloud, no accounts, no telemetry.

![Nexus Dashboard](<!-- add screenshot here -->)

**Features:** Widget grid · AI assistant (Ollama/RAG) · Docker monitoring · Wazuh security alerts · Home Assistant · Calendar · Notes (Obsidian vault) · Automations · RSS news · Heartbeat monitor · CSS snippet overrides

Every integration fails gracefully — if Wazuh isn't configured you see realistic mock data, if Ollama isn't running the AI tab says so but nothing else breaks.

---

## ⚠️ Built with AI — read before deploying

This project was built 100% through AI-assisted development (vibe coding) using Claude.
No code was written manually by the author.

That means:
- **It may contain bugs** that a trained developer would have caught during review
- **Logic may not be optimal** — it works, but implementations were not hand-crafted
- **You should audit before deploying** on anything sensitive or production-facing
- **Contributions and reviews are very welcome** — especially from people who actually write code

---

## Method 1 — Pre-built images (recommended)

No source code. No building. Just Docker.

### Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- That's it

### Step 1: Download two files

**Linux / macOS:**
```bash
mkdir nexus && cd nexus

curl -O https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/docker-compose-hub.yml
curl -O https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/backend/.env.example
curl -O https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/start.sh
chmod +x start.sh
```

**Windows (PowerShell):**
```powershell
mkdir nexus; cd nexus

Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/docker-compose-hub.yml" -OutFile "docker-compose-hub.yml"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/backend/.env.example" -OutFile ".env.example"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/start.ps1" -OutFile "start.ps1"
```

### Step 2: Create your config

**Linux / macOS:**
```bash
cp .env.example .env
nano .env        # or open in any text editor
```

**Windows:**
```powershell
copy .env.example .env
notepad .env
```

The only required setting is `NEXUS_SECRET_KEY` — set it to any random string:

```
NEXUS_SECRET_KEY=pick-any-long-random-string-here
```

Leave everything else blank for now. You can configure integrations later from the Settings page inside Nexus.

### Step 3: Start

**Linux / macOS:**
```bash
./start.sh
```

**Windows (PowerShell, run as Administrator):**
```powershell
.\start.ps1
```

The script auto-detects your machine's local IP and prints the URL. Docker pulls the images (~300 MB, first run only). Ready in about 1–2 minutes.

### Step 4: Open the dashboard

The script prints your URL, e.g.:

```
Dashboard  →  http://192.168.1.50:3000
```

Open that in your browser. The first-run wizard walks you through setup.

**The dashboard is also accessible from any other device on your network** at the same IP and port — phone, tablet, another PC.

---

### Managing Nexus

```bash
# Stop
docker compose -f docker-compose-hub.yml down

# Start again (uses start script so IP is detected)
./start.sh          # Linux/Mac
.\start.ps1         # Windows

# Update to the latest version
docker compose -f docker-compose-hub.yml pull
./start.sh

# View logs (live)
docker compose -f docker-compose-hub.yml logs -f

# View backend logs only
docker compose -f docker-compose-hub.yml logs -f backend

# Restart a single service
docker compose -f docker-compose-hub.yml restart backend
```

---

## Method 2 — Manual (no start script)

If you prefer to run Docker Compose directly without the start script:

```bash
# 1. Find your local IP
#    Linux:   hostname -I
#    macOS:   ipconfig getifaddr en0
#    Windows: ipconfig   (look for IPv4 Address under your network adapter)

# 2. Set it in your .env
echo "HOST_IP=192.168.1.50" >> .env    # use your actual IP

# 3. Start
docker compose -f docker-compose-hub.yml up -d

# 4. Open http://192.168.1.50:3000
```

---

## Method 3 — Build from source

For developers who want to modify Nexus.

### Requirements

- Docker Desktop
- Git
- Node.js 22+ (for frontend)
- Python 3.12+ (for backend)

```bash
git clone https://github.com/Henri-VS/nexus-dashboard.git
cd nexus-dashboard
cp backend/.env.example .env
# Edit .env — set NEXUS_SECRET_KEY and HOST_IP

docker compose up --build -d
```

### Local dev without Docker

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8088
```

**Frontend (separate terminal):**
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

---

## Configuration

All settings live in `.env`. Open it in any text editor — every option has a comment.

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXUS_SECRET_KEY` | **Yes** | API auth key — any long random string |
| `HOST_IP` | Recommended | Your machine's LAN IP (auto-set by start script) |
| `OLLAMA_HOST` | No | Ollama endpoint — e.g. `http://host.docker.internal:11434` |
| `OLLAMA_DEFAULT_MODEL` | No | Model name — e.g. `llama3.2`, `mistral` |
| `OBSIDIAN_VAULT_PATH` | No | Path to your Obsidian vault on disk |
| `HA_HOST` | No | Home Assistant URL — e.g. `http://homeassistant.local:8123` |
| `HA_TOKEN` | No | Home Assistant long-lived access token |
| `WAZUH_HOST` | No | Wazuh manager API URL |
| `WAZUH_USER` / `WAZUH_PASS` | No | Wazuh API credentials |
| `THM_USERNAME` | No | TryHackMe username for progress tracking |
| `NTFY_URL` / `NTFY_TOPIC` | No | ntfy push notification settings |
| `WEATHER_LAT` / `WEATHER_LON` | No | Your coordinates for the weather widget |

Any integration left unconfigured shows mock/demo data inside Nexus.

---

## Ports

| Port | Service |
|------|---------|
| **3000** | Dashboard (open this) |
| 8088 | Backend API |
| 3002 | Excalidraw whiteboard |

To change a port, edit `docker-compose-hub.yml` before starting. Example — move dashboard to port 8080:
```yaml
ports:
  - "8080:3000"   # was 3000:3000
```

---

## Data and backups

All persistent data lives in `./data/` next to your compose file:

```
data/
├── dashboard.db          ← SQLite (logs, run history)
└── .nexus/
    ├── config.yml        ← your settings
    ├── calendar/         ← calendar events (.md files, human-editable)
    ├── automations/      ← automation rules (.md files)
    └── snippets/         ← custom CSS overrides
```

**To back up:** copy the `./data/` folder.  
**To migrate to a new machine:** copy `./data/` + `.env` to the new machine, then run `./start.sh`.

---

## NVIDIA GPU (faster Ollama inference)

Requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) on the host.

```bash
docker compose -f docker-compose-hub.yml -f docker-compose.gpu.yml up -d
```

---

## Auth

Set `NEXUS_SECRET_KEY` in `.env`. Every `/api/` request requires `Authorization: Bearer <key>`. The frontend prompts for it on first launch and stores it in `localStorage`.

Leave `NEXUS_SECRET_KEY` empty to disable auth entirely (local dev only — not recommended if accessible on your network).

---

## Troubleshooting

**Dashboard loads but "cannot connect to API"**  
Your `HOST_IP` is wrong or not set. Run the start script again — it auto-detects the IP. Or check the value in `.env` and make sure it matches your machine'