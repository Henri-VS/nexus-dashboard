# Nexus Dashboard — Claude Code Context

## What This Project Is

**Nexus Dashboard** is a self-hosted homelab dashboard. It is open-source, intended for distribution via Docker Hub and GitHub. It is 100% local — no cloud, no telemetry, no accounts. Everything persists either in SQLite (time-series / append-only data) or Markdown files (user-editable config and structured data).

The target user is a homelabber / developer who wants a single pane of glass for their self-hosted infrastructure. The aesthetic is "professional DIY" — intentional and clean, but with a hacker/terminal character. Think Obsidian, not Vercel.

## Tech Stack

- **Frontend**: SvelteKit (Svelte 5), TypeScript, plain CSS with CSS custom properties
- **Backend**: Python 3.13, FastAPI, SQLModel, SQLite, uvicorn
- **Fonts**: JetBrains Mono (data/code), Geist Sans (prose/labels — to be added)
- **Icons**: Lucide (via @lucide/svelte)
- **Deployment**: Docker Compose

## Directory Structure

```
/
├── CLAUDE.md                  ← you are here
├── SPEC.md                    ← original feature spec
├── docker-compose.yml
├── docker-compose.gpu.yml     ← GPU override (optional)
├── .env.example
├── frontend/
│   └── src/
│       ├── app.css            ← global CSS, CSS variables, design tokens
│       ├── lib/
│       │   ├── api.ts         ← all fetch calls to backend
│       │   ├── theme.ts       ← theme definitions
│       │   ├── stores.ts      ← nexusSettings store
│       │   ├── types.ts
│       │   ├── components/
│       │   │   ├── Nav.svelte
│       │   │   ├── Topbar.svelte
│       │   │   ├── Card.svelte           ← THE canonical Card — use this one
│       │   │   ├── AiOverlay.svelte
│       │   │   ├── AiQuickBar.svelte
│       │   │   ├── WidgetTray.svelte
│       │   │   ├── WidgetSettingsPopover.svelte
│       │   │   ├── EmptyState.svelte     ← shared empty state component (to create)
│       │   │   └── widgets/
│       │   │       ├── Card.svelte       ← DUPLICATE — to be deleted, use lib/components/Card.svelte
│       │   │       └── [widget].svelte
│       │   └── stores/
│       │       └── dashConfig.ts         ← widget layout config
│       └── routes/
│           ├── +layout.svelte
│           ├── +page.svelte              ← main dashboard grid
│           ├── ai/
│           ├── automations/
│           ├── calendar/
│           ├── home/
│           ├── lab/
│           ├── learn/
│           ├── logs/
│           ├── news/
│           ├── notes/
│           ├── resources/
│           └── settings/
└── backend/
    ├── app/
    │   ├── main.py
    │   ├── core/
    │   │   ├── config.py      ← Settings (pydantic-settings, reads .env)
    │   │   └── database.py    ← SQLite engine + init_db()
    │   ├── routers/           ← one file per domain
    │   │   ├── ai.py
    │   │   ├── automations.py
    │   │   ├── calendar.py
    │   │   ├── docker.py
    │   │   ├── heartbeat.py
    │   │   ├── home.py
    │   │   ├── learn.py
    │   │   ├── logs.py        ← SSE streaming + SQLite log storage
    │   │   ├── news.py        ← RSS feed aggregator
    │   │   ├── notes.py       ← Obsidian vault reader
    │   │   ├── notifications.py
    │   │   ├── quicklinks.py
    │   │   ├── resources.py
    │   │   ├── security.py    ← Wazuh integration + mock fallback
    │   │   ├── system.py
    │   │   └── weather.py
    │   └── models/
    └── requirements.txt

## Design System

All design tokens are CSS custom properties in `frontend/src/app.css`.

### Typography Rules (ENFORCE THESE)
- **JetBrains Mono**: numbers, metrics, IP addresses, timestamps, code, log lines, status badges, widget header labels, terminal-style content
- **Geist Sans** (to be added): page titles, section labels, descriptions, news summaries, empty state text, navigation labels, settings prose

### Color Tokens (exact values — confirmed from UI reference mockup)
```
--bg0:    #0d1117   /* app frame base */
--bg1:    #161b22   /* sidebar, topbar, cards */
--bg2:    #21262d   /* overlays, inputs, hover states */
--bg3:    #2c3440   /* shimmer highlight, tooltips */
--border: #30363d   /* all borders */
--text0:  #e6edf3   /* primary text */
--text1:  #8b949e   /* secondary / labels */
--text2:  #484f58   /* muted / disabled */
--accent: #3fb950   /* primary accent (green) */
--accent2: #58a6ff  /* blue */
--accent3: #bc8cff  /* purple */
--yellow: #e3b341
--red:    #f85149
--green:  #3fb950   /* same as --accent */
```

### Widget Category Accents
Each widget has a category color. Use the **left-border accent bar pattern (3px left border)**:
```
--accent-system:   #3fb950   green   (CPU/RAM/network widgets)
--accent-security: #f85149   red     (Wazuh / security widget)
--accent-docker:   #58a6ff   blue    (containers widget — NOTE: blue, not green)
--accent-notes:    #bc8cff   purple  (notes / obsidian widget)
--accent-learn:    #e3b341   yellow  (TryHackMe / learning widget)
--accent-home:     orange            (home assistant widget)
--accent-weather:  #58a6ff   blue    (weather widget)
--accent-news:     #30363d   neutral (news widget — no color accent, uses border color)
```

### Nav Badge Colors
Status pills shown next to nav items (e.g. container count, security alert count):
```
green pill: bg #0d2010, border #1d4a25, text #3fb950
red pill:   bg #1d0808, border #4d1515, text #f85149
```

## Data Storage Rules

**SQLite** (via SQLModel): logs, automation run history, heartbeat history, calendar events (until markdown migration), notifications config.

**Markdown files** (`.nexus/` folder in data volume): automations config, calendar events, user config, CSS snippets. Format: YAML frontmatter + markdown body. Like Obsidian's `.obsidian/` folder.

**localStorage** (frontend): widget layout/sizes, current theme selection, expanded sidebar state. ONLY UI preferences — nothing that affects backend behavior.

## `.nexus/` Folder Structure (Obsidian-inspired)

```
data/
└── .nexus/
    ├── config.yml             ← main user config (replaces scattered .env for user-facing settings)
    ├── calendar/
    │   └── 2026-06-14.md      ← one file per event, YAML frontmatter
    ├── automations/
    │   └── critical-alert.md  ← one file per automation, YAML frontmatter
    ├── snippets/
    │   └── custom.css         ← CSS overrides loaded at runtime (like Obsidian snippets)
    └── themes/
        └── my-theme.css       ← user-defined themes
```

### Calendar Event Format
```markdown
---
title: Study Session
date: 2026-06-14T14:00:00
duration: 90m
tags: [study, compTIA]
color: yellow
---
Notes about this event go here. Rendered as markdown in the detail view.
```

### Automation Format
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
Fires whenever Wazuh reports a CRIT-level security event.
Send a push notification via ntfy.
```

## Authentication

Every backend route under `/api/` requires `Authorization: Bearer <NEXUS_SECRET_KEY>` header. The key comes from `.env`. The frontend stores the key in localStorage after a one-time setup screen. `/healthz` is exempt from auth.

See `backend/app/core/auth.py` (to be created) for the middleware implementation.

## Naming Conventions

- Product name: **Nexus** (not "dashboard", not "homelab-dashboard")
- Python: snake_case, type hints everywhere, no bare `except:`
- Svelte: PascalCase components, camelCase variables
- CSS: kebab-case custom properties, BEM-light class names
- No `any` types in TypeScript unless genuinely unavoidable

## Known Issues (Active Backlog)

1. `widgets/Card.svelte` is a duplicate of `components/Card.svelte` — delete `widgets/Card.svelte`
2. `weather_lat/lon` defaults are a real personal location — replace with `0.0` + require user config
3. NVIDIA GPU reservation is unconditional in `docker-compose.yml` — move to `docker-compose.gpu.yml`
4. `${OBSIDIAN_VAULT_PATH}` volume mount fails if var is unset — make optional
5. Notification settings are 30+ individual `let` variables — refactor to typed object
6. Page `<title>` tags are inconsistent and lowercase
7. Product is called "Nexus" in sidebar but "dashboard" everywhere else

## Constraints (Never Violate)

- **No cloud dependencies** — everything runs locally
- **No user accounts / multi-user auth** — single shared secret key
- **Markdown-first for user data** — if a user would want to edit it, it should be a .md or .yml file
- **Mock fallbacks always** — every integration must degrade gracefully with realistic mock data
- **No breaking the offline badge pattern** — widgets must always show data source status
- **SQLite only** — no PostgreSQL, no Redis, no external databases
- **Do not commit `.env`** — always use `.env.example`
