# homelab dashboard — project spec

## what this is
A self-hosted personal dashboard built with SvelteKit + FastAPI.
Dark terminal theme. Markdown-native aesthetic. Fully customisable.
Runs in Docker on a homelab server. Built for one user (me).

## tech stack
- Frontend: SvelteKit (TypeScript)
- Backend: FastAPI (Python 3.12)
- Database: SQLite via SQLModel
- AI: Ollama (local, RTX 5060)
- Fonts: JetBrains Mono (NerdFont) + system-ui fallback
- Containerisation: Docker Compose

## my setup
- OS (dev machine): Windows 11, CachyOS Linux (dual boot)
- Homelab runs: CachyOS Linux
- GPU: NVIDIA RTX 5060 (in homelab machine)
- Ollama port: 11434
- Home Assistant port: 8124
- Wazuh API: http://localhost:55000   # CHANGE to your actual endpoint
- Obsidian vault path: /home/henri/obsidian   # CHANGE to actual path
- Mosquitto MQTT: localhost:1883

## ports (no conflicts)
- 3000  frontend (SvelteKit)
- 8000  backend (FastAPI)
- 11434 Ollama (existing)
- 8124  Home Assistant (existing)
- 8123  Crafty Controller (existing, do not touch)

## design rules
- Theme: dark terminal, GitHub-dark palette
- Font: JetBrains Mono NerdFont for all monospace elements
- Accent colors defined as CSS variables — user-switchable
- Left-border accent bars on cards (3px, color per category)
- Markdown syntax visible in notes widget (not rendered away)
- Everything customisable via a theme config JSON

## pages
1. / — dashboard home (widget grid)
2. /ai — full AI chat (ChatGPT-style, streaming, conversation history)
3. /lab — security monitoring (Wazuh, network, Docker)
4. /notes — Obsidian vault viewer (markdown rendered)
5. /learn — THM progress, cert timers, study tracker
6. /home — Home Assistant entities, gate control

## widgets (dashboard home)
- weather (OpenMeteo, Somerset West, no API key needed)
- system stats (CPU, RAM, temps, disk, battery via psutil)
- security alerts (Wazuh feed, severity colour coded)
- notes preview (Obsidian vault, last edited notes)
- docker status (container health via Docker SDK)
- learning tracker (THM progress, cert countdowns)
- home automation (HA entities, gate status)

## ai features
- streaming responses (SSE)
- conversation history (SQLite)
- model switching (any Ollama model)
- context-aware (can query homelab data)
- floating overlay (Ctrl+Space from any page)
- full page (/ai) for long conversations
