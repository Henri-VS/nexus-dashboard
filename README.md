# Nexus Dashboard

A self-hosted homelab dashboard. SvelteKit frontend, FastAPI backend, SQLite storage. 100% local — no cloud, no accounts, no telemetry.

![Nexus Dashboard](docs/screenshots/hero.png)
<!-- Screenshot: full dashboard overview — the widget grid with multiple widgets visible -->

---

## Contents

- [⚠️ Built with AI](#️-built-with-ai--read-before-deploying)
- [What Nexus does](#what-nexus-does)
  - [Dashboard](#dashboard-widget-grid)
  - [AI assistant](#ai-assistant)
  - [Notes](#notes-built-in-editor)
  - [Resources](#resources-document-library--ai-study-tools)
  - [Security](#security-wazuh-integration)
  - [Automations](#automations)
  - [Calendar](#calendar)
  - [Logs](#logs)
  - [Settings](#settings)
- [Tech stack](#tech-stack)
- [Requirements](#requirements)
- [Install](#install)
  - [Method 1 — One-liner](#method-1--one-liner-linux--macos)
  - [Method 2 — Docker Compose only](#method-2--docker-compose-only-any-os-full-manual-control)
  - [Method 3 — Start script](#method-3--start-script-auto-ip-detection--nice-output)
  - [Method 4 — Build from source](#method-4--build-from-source)
- [Managing Nexus](#managing-nexus)
- [Configuration](#configuration)
- [Data and backups](#data-and-backups)
- [Ports](#ports)
- [NVIDIA GPU](#nvidia-gpu-faster-ollama-inference)
- [Auth](#auth)
- [Security Notes](#security-notes)
- [Troubleshooting](#troubleshooting)

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

## What Nexus does

Nexus is a single-page-of-glass for your homelab. Everything you'd normally check across five browser tabs — system load, container health, security alerts, AI chat, your notes — lives in one dark-themed, self-hosted interface. Every integration degrades gracefully: if something isn't configured, you see realistic demo data instead of a broken widget.

> **Integration status:** Widgets show realistic mock data when an integration is not configured. "Not configured" means the relevant env var is empty — the widget switches to live data automatically once you set it. All integrations listed below have working backend implementations; none are UI-only placeholders.

### Dashboard (widget grid)

![Dashboard](docs/screenshots/dashboard.png)
<!-- Screenshot: the main widget grid — system stats, docker containers, weather, security alerts, notes preview all visible -->

The home screen is a configurable widget grid. Available widgets:

**System** — live CPU, RAM, disk, temperature, and network I/O pulled from the host via psutil. Sparkline graphs update every 10 seconds.

**Docker** — lists all containers with health status, uptime, image name, and a one-click restart button. Uses the Docker SDK — no port mapping required.

**Weather** — current conditions plus a 7-day forecast. Powered by [Open-Meteo](https://open-meteo.com/) — no API key needed. Automatically detects timezone from your coordinates.

**Security alerts** — shows the latest alerts from Wazuh (your SIEM), colour-coded by severity (CRIT / HIGH / WARN / INFO). Click any alert to expand the raw JSON. Full mock data if Wazuh isn't configured.

**Notes preview** — shows your most recently edited notes, with clickable links to open them in the full editor.

**Learning tracker** — your TryHackMe rank, points, and badge count, plus countdown timers for any certifications you're working toward.

**Home automation** — Home Assistant entity cards. See and control lights, switches, sensors, and any other HA entity directly from the dashboard.

**News** — RSS feed aggregator. Add any number of feeds; articles are fetched and cached on the backend.

**Heartbeat monitor** — pings your self-hosted services on a schedule and shows uptime/downtime history. Green dot = up, red = down.

**Quick links** — a pinned shortcut bar for your frequently used services (Proxmox, router, NAS, etc.).

You can reorder and configure widgets from the settings panel. Layout presets let you switch between configurations (Overview, Security Ops, Developer, Minimal, etc.) in one click.

---

### AI assistant

![AI assistant](docs/screenshots/ai.png)
<!-- Screenshot: the /ai page showing a chat conversation with streaming response, model selector visible -->

Full local AI chat powered by [Ollama](https://ollama.com/). No data leaves your machine.

- **Streaming responses** via Server-Sent Events — characters appear as they generate
- **Conversation history** stored in SQLite — pick up where you left off
- **Model switching** — switch between any model you have pulled in Ollama (llama3, mistral, qwen, etc.)
- **RAG (Retrieval-Augmented Generation)** — upload documents in the Resources section and the AI can answer questions about them, pulling relevant chunks as context
- **Floating overlay** — press `Ctrl+Space` from any page to open a quick AI bar without leaving what you're doing
- **Full page** at `/ai` for longer conversations with a ChatGPT-style interface

If Ollama isn't running, the AI tab tells you clearly — no other part of the dashboard breaks.

---

### Notes (built-in editor)

![Notes editor](docs/screenshots/notes.png)
<!-- Screenshot: the /notes page — file tree on left, markdown editor in centre (split view), properties panel on right -->

A full Obsidian-inspired notes system, completely local.

- **Vault system** — create multiple vaults and switch between them
- **File tree** with folders, drag-to-move, rename, delete
- **Markdown editor** with split view (edit + preview side-by-side) or preview-only mode
- **YAML frontmatter** — add tags, dates, and custom metadata at the top of any note; the Properties panel on the right parses and displays it
- **Excalidraw support** — create and edit `.excalidraw` diagrams directly inside the editor
- **Command palette** (`Ctrl+P`) — fuzzy-search all files and actions
- **Tab bar** — open multiple files at once, switch between them
- **Wikilinks** — `[[link to another note]]` style internal links, clickable in preview mode
- **Backlinks** — the Properties panel shows which other notes link to the current one

Notes are stored in your browser's localStorage by default. Wire up the backend vault path to sync with a real folder on disk (e.g. your existing Obsidian vault).

---

### Resources (document library + AI study tools)

![Resources](docs/screenshots/resources.png)
<!-- Screenshot: the /resources page — folder tree on left, PDF preview in centre, file info + AI actions panel on right -->

Upload your study materials, docs, and reference files. The AI can process them and turn them into interactive study tools.

- **Upload** PDFs, PowerPoints, Markdown files, and images
- **PDF viewer** — reads PDFs inline in the browser
- **AI processing** — extract text from any document so the AI can read it
- **Flashcard generator** — the AI reads a processed document and generates a set of flashcards. Flip through them with keyboard or mouse
- **Past paper mode** — upload a past exam paper; the AI extracts the questions, presents them one by one, accepts your written answers, and marks them with feedback and study tips
- **Ask AI** — jump directly to the AI chat with the document loaded as context
- **Folder tree** — organise files into folders and subfolders; rename, move, delete via right-click context menu

---

### Security (Wazuh integration)

![Security](docs/screenshots/security.png)
<!-- Screenshot: the /security page — severity summary cards at top, alert table below with one row expanded showing full JSON -->

A dedicated security monitoring page at `/security`.

- Summary cards showing counts of CRIT / HIGH / WARN / INFO alerts
- Click a severity to filter the table
- Expandable alert rows showing full event details
- Live/mock badge so you always know if you're seeing real data
- 30-second auto-refresh

If Wazuh isn't configured, the page shows realistic mock alerts so the UI is always functional.

---

### Automations

![Automations](docs/screenshots/automations.png)
<!-- Screenshot: the /automations page — list of automation rules with enabled/disabled toggles, last run time -->

Event-driven automation rules stored as Markdown files in `.nexus/automations/`. Human-editable — no GUI required, but a UI is provided.

Example triggers: Wazuh alert above a severity threshold, a heartbeat going down, a schedule (cron).  
Example actions: ntfy push notification, webhook call.

Each automation is a `.md` file with YAML frontmatter:

```markdown
---
name: Critical Security Alert
enabled: true
trigger:
  type: wazuh_alert
  min_severity: CRIT
action:
  type: ntfy_notify
  title: "🚨 Critical Alert"
  message: "Wazuh detected a CRITICAL event"
  priority: 5
---
```

---

### Calendar

A calendar view with events stored as Markdown files in `.nexus/calendar/`. Each event is a file with YAML frontmatter (title, date, duration, tags, colour). The body of the file is rendered as Markdown in the detail view.

---

### Logs

A streaming log viewer at `/logs` that tails live log output from the backend via SSE. Historical logs are stored in SQLite and searchable by level and time range.

---

### Settings

![Settings](docs/screenshots/settings.png)
<!-- Screenshot: the /settings page — theme picker, integration config fields, widget toggles -->

- **Theme switching** — built-in themes, switchable at runtime without a page reload
- **CSS snippets** — drop `.css` files into `.nexus/snippets/` and they load automatically, like Obsidian snippets. Lets you tweak any part of the UI without touching source code
- **Widget configuration** — show/hide widgets, change their data source settings
- **Integration setup** — configure Ollama, Home Assistant, Wazuh, TryHackMe, weather coordinates, and notification settings through a UI instead of editing `.env` by hand

---

## Tech stack

| Layer | Tech |
|-------|------|
| Frontend | SvelteKit (Svelte 5), TypeScript, plain CSS with CSS custom properties |
| Backend | Python 3.13, FastAPI, SQLModel |
| Database | SQLite (logs, history, events) |
| AI | Ollama (any local model) |
| Deployment | Docker Compose |
| Fonts | JetBrains Mono (data/code), Geist Sans (labels/prose) |

---

## Requirements

Docker must be installed and running.

- **Linux / server:** [Docker Engine install guide](https://docs.docker.com/engine/install/) — `apt install docker.io` or the official script
- **macOS:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) or [OrbStack](https://orbstack.dev/) (lighter alternative)
- **Windows:** [Docker Desktop](https://www.docker.com/products/docker-desktop/)

Docker Compose v2 is included with Docker Engine 20.10+ and Docker Desktop. Verify with: `docker compose version`

---

## Install

### Method 1 — One-liner (Linux / macOS)

```bash
curl -fsSL https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/install.sh | bash
```

That's it. The script checks for Docker, creates a `nexus/` folder, downloads everything, generates a random secret key, and starts Nexus. Open the URL it prints.

---

### Method 2 — Docker Compose only (any OS, full manual control)

Download one file, set two variables, run one command.

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/docker-compose-hub.yml -o docker-compose-hub.yml

# Create .env
echo "NEXUS_SECRET_KEY=$(tr -dc 'a-zA-Z0-9' </dev/urandom | head -c 32)" > .env
echo "HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ipconfig getifaddr en0)" >> .env

docker compose -f docker-compose-hub.yml up -d
```

**Windows (PowerShell):**
```powershell
Invoke-WebRequest "https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/docker-compose-hub.yml" -OutFile "docker-compose-hub.yml"

# Create .env — replace values with your own
"NEXUS_SECRET_KEY=change-this-to-any-random-string" | Out-File .env -Encoding utf8
"HOST_IP=YOUR_LAN_IP_HERE" | Add-Content .env   # run ipconfig to find it

docker compose -f docker-compose-hub.yml up -d
```

Open `http://YOUR_IP:3000`. Docker pulls images (~300 MB) on the first run — ready in 1–2 minutes.

---

### Method 3 — Start script (auto IP detection + nice output)

**Linux / macOS:**
```bash
mkdir nexus && cd nexus
curl -fsSL https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/docker-compose-hub.yml -o docker-compose-hub.yml
curl -fsSL https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/backend/.env.example -o .env.example
curl -fsSL https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/start.sh -o start.sh
chmod +x start.sh
cp .env.example .env
nano .env    # set NEXUS_SECRET_KEY to any random string
./start.sh
```

**Windows (PowerShell):**
```powershell
mkdir nexus; cd nexus
Invoke-WebRequest "https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/docker-compose-hub.yml" -OutFile "docker-compose-hub.yml"
Invoke-WebRequest "https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/backend/.env.example" -OutFile ".env.example"
Invoke-WebRequest "https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/start.ps1" -OutFile "start.ps1"
copy .env.example .env
notepad .env    # set NEXUS_SECRET_KEY to any random string
.\start.ps1
```

The start script auto-detects your LAN IP and prints a clean startup block:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Nexus is running

 Dashboard  →  http://192.168.1.50:3000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Method 4 — Build from source

```bash
git clone https://github.com/Henri-VS/nexus-dashboard.git
cd nexus-dashboard
cp backend/.env.example .env
# Edit .env — set NEXUS_SECRET_KEY and HOST_IP
docker compose up --build -d
```

**Without Docker (local dev):**
```bash
# Backend
cd backend && python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8088

# Frontend (separate terminal)
cd frontend && npm install && npm run dev    # http://localhost:5173
```

---

## Managing Nexus

```bash
# Stop
docker compose -f docker-compose-hub.yml down

# Start again
./start.sh          # Linux/Mac
.\start.ps1         # Windows

# Update to latest version
docker compose -f docker-compose-hub.yml pull
./start.sh

# View logs (live)
docker compose -f docker-compose-hub.yml logs -f

# Restart a single service
docker compose -f docker-compose-hub.yml restart backend
```

---

## Configuration

All settings live in `.env`. Every option has a comment explaining it.

| Variable | Required | What it does |
|----------|----------|-------------|
| `NEXUS_SECRET_KEY` | **Yes** | API auth key — any long random string |
| `HOST_IP` | Recommended | Your machine's LAN IP (auto-set by start script) |
| `OLLAMA_HOST` | No | Ollama endpoint, e.g. `http://host.docker.internal:11434` |
| `OLLAMA_DEFAULT_MODEL` | No | Default model, e.g. `llama3.2`, `mistral`, `qwen2.5` |
| `OBSIDIAN_VAULT_PATH` | No | Path to a folder on disk to use as the notes vault |
| `HA_HOST` | No | Home Assistant URL, e.g. `http://homeassistant.local:8123` |
| `HA_TOKEN` | No | Home Assistant long-lived access token |
| `WAZUH_HOST` | No | Wazuh manager API URL |
| `WAZUH_USER` / `WAZUH_PASS` | No | Wazuh API credentials |
| `THM_USERNAME` | No | TryHackMe username for the learning tracker |
| `NTFY_URL` / `NTFY_TOPIC` | No | ntfy endpoint for push notifications |
| `WEATHER_LAT` / `WEATHER_LON` | No | Your coordinates for the weather widget |
| `WEATHER_TIMEZONE` | No | Timezone string or `auto` (default) |
| `NEWS_FEEDS` | No | Comma-separated RSS feed URLs |

Any integration left blank shows mock/demo data — nothing breaks.

---

## Data and backups

All persistent data lives in `./data/` next to your compose file:

```
data/
├── dashboard.db          ← SQLite: logs, automation history, heartbeat records
└── .nexus/
    ├── config.yml        ← main user config (human-editable)
    ├── calendar/         ← one .md file per calendar event
    ├── automations/      ← one .md file per automation rule
    └── snippets/         ← custom CSS overrides (loaded at runtime)
```

**To back up:** copy the `./data/` folder.  
**To migrate:** copy `./data/` and `.env` to the new machine, run `./start.sh`.

---

## Ports

| Port | Service |
|------|---------|
| **3000** | Dashboard |
| 8088 | Backend API |
| 3002 | Excalidraw whiteboard |

To change a port, edit `docker-compose-hub.yml`:
```yaml
ports:
  - "8080:3000"    # moves dashboard to port 8080
```

---

## NVIDIA GPU (faster Ollama inference)

Requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) on the host.

```bash
docker compose -f docker-compose-hub.yml -f docker-compose.gpu.yml up -d
```

---

## Auth

Every `/api/` request requires `Authorization: Bearer <NEXUS_SECRET_KEY>`. The frontend prompts for the key on first launch and stores it in `localStorage`. `/healthz` is public (for uptime monitoring).

Set `NEXUS_SECRET_KEY` to an empty string to disable auth entirely — only do this on a fully isolated local network.

---

## Security Notes

**Docker socket access.** The backend container mounts `/var/run/docker.sock` to power the Containers widget. Even with `:ro`, this gives the container root-equivalent access to the Docker daemon on your host. For a homelab on a trusted local network this is an acceptable tradeoff, but do not expose the backend port (8088) to the internet — use a reverse proxy with auth if you need external access.

**Auth model.** After the first-launch setup screen, the secret key is stored in your browser's `localStorage`. This is sufficient for a single-user local network tool but is not hardened against a compromised browser extension or a malicious CSS import. Do not reuse your `NEXUS_SECRET_KEY` for anything else, and treat it like a password.

**Notes storage.** Notes are stored in browser `localStorage` by default, which has a 5–10 MB browser limit. For serious note-taking, set `OBSIDIAN_VAULT_PATH` in `.env` to point at your Obsidian vault — that directory is mounted read-only into the backend container and served directly, with no size limit.

---

## Troubleshooting

**Dashboard loads but "cannot connect to API"** — `HOST_IP` is wrong or unset. Run the start script again (it auto-detects), or check `.env` and make sure `HOST_IP` matches your machine's actual LAN IP (not `127.0.0.1`).

**Port 3000 already in use** — edit `docker-compose-hub.yml` and change `"3000:3000"` to `"3001:3000"` (or any free port).

**Images won't pull** — check your internet connection and that Docker Desktop is running. Try `docker pull henrivs/nexus-frontend:latest` manually to see the full error.

**Backend health check failing** — run `docker compose -f docker-compose-hub.yml logs backend` and check for Python errors. Most common cause: `NEXUS_SECRET_KEY` not set in `.env`.

**Weather widget shows wrong location** — set `WEATHER_LAT` and `WEATHER_LON` in `.env` to your actual coordinates.

**Wazuh / Home Assistant widget shows mock data** — that's expected until you set the relevant environment variables and restart the backend.

---

## License

MIT — free to use, modify, and self-host.
