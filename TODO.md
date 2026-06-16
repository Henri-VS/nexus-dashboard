# Nexus — Pre-Launch TODO

Last updated: 2026-06-15

---

## 🔴 Blockers — Fix Before Anything Else

These ship bugs or personal data to the public if left unfixed.

**→ Paste this prompt into Claude Code to fix all 5 blockers in one shot:**

```
You are working on Nexus Dashboard (read CLAUDE.md for full context).

Task: Fix 5 pre-launch blockers. Make only the changes described — do not refactor anything else.

═══ Fix 1: Scrub backend/.env.example ═══

Replace the entire file with this clean version (no personal data):
```
# ── Core ──────────────────────────────────────────────────────
# Secret key for API authentication. Set this to a random string before deploying.
# Leave empty to disable auth (dev mode only — never leave empty in production).
NEXUS_SECRET_KEY=change-me-to-a-random-secret

DB_PATH=./data/dashboard.db

# ── Ollama (AI) ───────────────────────────────────────────────
# Local dev:
OLLAMA_HOST=http://localhost:11434
# Inside Docker (use this when running via docker compose):
# OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_DEFAULT_MODEL=llama3.2

# ── Obsidian vault ────────────────────────────────────────────
# Path to your Obsidian vault on disk. Leave empty if not using Obsidian.
OBSIDIAN_VAULT_PATH=

# ── Wazuh (Security) ─────────────────────────────────────────
WAZUH_HOST=https://wazuh.local:55000
WAZUH_USER=wazuh-wui
WAZUH_PASS=
# Set to false to disable SSL verification (not recommended for production)
WAZUH_VERIFY_SSL=true

# ── Home Assistant ────────────────────────────────────────────
HA_HOST=http://homeassistant.local:8123
HA_TOKEN=

# ── TryHackMe ─────────────────────────────────────────────────
THM_USERNAME=

# ── Ntfy push notifications ───────────────────────────────────
NTFY_URL=https://ntfy.sh
NTFY_TOPIC=nexus-alerts
```

═══ Fix 2: Remove hardcoded name in backend/app/routers/learn.py ═══

Find the line:
  username = settings.thm_username or "Terry"

Replace with:
  username = settings.thm_username or ""

If username is empty after this change, the existing mock data fallback should handle it — check that the function still returns valid data when username is "". If it calls an external API with an empty username and would error, wrap the external call in a try/except that returns mock data instead.

═══ Fix 3: Log SSL warning in backend/app/routers/security.py ═══

Find the line containing `verify=False` in the Wazuh client call.

1. Add a WAZUH_VERIFY_SSL setting to backend/app/core/config.py:
   wazuh_verify_ssl: bool = Field(default=True, validation_alias=AliasChoices("WAZUH_VERIFY_SSL", "wazuh_verify_ssl"))

2. Replace the hardcoded verify=False with:
   verify = settings.wazuh_verify_ssl
   if not verify:
       logger.warning(
           "Wazuh SSL verification is DISABLED (WAZUH_VERIFY_SSL=false). "
           "Set a valid cert on your Wazuh host to re-enable."
       )
   async with httpx.AsyncClient(verify=verify, timeout=10.0) as client:

═══ Fix 4: Hide /docs in production in backend/app/main.py ═══

Find the FastAPI() constructor call. Change docs_url:
  docs_url="/docs" if not settings.nexus_secret_key else None,

This keeps docs available in dev (no key set) and hides them when deployed with a secret key.

═══ Fix 5: Rewrite README.md ═══

Rewrite README.md from scratch. Keep it concise — this is the public-facing project page.

Content to include:
- One-line description: "Nexus is a self-hosted homelab dashboard. SvelteKit + FastAPI. 100% local — no cloud, no accounts."
- Screenshot placeholder: `<!-- screenshot -->`
- Features list: widget grid, AI assistant (Ollama), Docker monitoring, security events (Wazuh), Home Assistant, calendar, notes, automations, news feed, heartbeat monitor, CSS snippets
- Requirements section: Docker + Docker Compose v2, Ollama (optional — needed for AI features)
- Quick start (4 steps: clone, cp .env.example .env + edit, docker compose up --build -d, open http://localhost:3000)
- GPU section: "If you have an NVIDIA GPU and want Ollama to use it: docker compose -f docker-compose.yml -f docker-compose.gpu.yml up --build -d"
- Dev section (backend: venv + uvicorn on port 8000, frontend: npm run dev on port 5173)
- Ports table: 3000 frontend, 8088 backend API, 3002 Excalidraw (whiteboard)
- Configuration section: brief description of what each .env var does
- Data section: explain ./data/ volume, .nexus/ folder structure
- Auth section: explain NEXUS_SECRET_KEY — set it, frontend stores it in localStorage after first run
- License: MIT

After all changes, run: git grep -r "wille\|Terry\|henri-dashboard\|192\.168\.68" --include="*.py" --include="*.ts" --include="*.svelte" --include="*.md" --include="*.yml" --include="*.example"
If any matches come back (excluding mock IP addresses in comments), fix them before finishing.
```

---

### 1. Scrub `.env.example`
File: `backend/.env.example`

Replace personal values with generic placeholders:
```
OBSIDIAN_VAULT_PATH=C:/Users/wille/obsidian  →  OBSIDIAN_VAULT_PATH=
THM_USERNAME=Terry                            →  THM_USERNAME=
NTFY_TOPIC=henri-dashboard                   →  NTFY_TOPIC=nexus-alerts
```
Also **add** `NEXUS_SECRET_KEY` — it's missing entirely:
```
NEXUS_SECRET_KEY=change-me-to-a-random-secret
```

### 2. Hardcoded name in `learn.py`
File: `backend/app/routers/learn.py` line 100

```python
# Before
username = settings.thm_username or "Terry"

# After
username = settings.thm_username or ""
```

### 3. Silent SSL bypass in `security.py`
File: `backend/app/routers/security.py` line 112

Add `WAZUH_VERIFY_SSL` env var and log a warning when it's disabled.

### 4. Public `/docs` endpoint
File: `backend/app/main.py` line 46

```python
docs_url="/docs" if not settings.nexus_secret_key else None,
```

### 5. Fix README
- Remove NVIDIA GPU as a requirement
- Fix backend port (8088 not 8000)
- Rewrite opening line for a public audience

---

## 🟡 Must Test — Implemented But Unverified

Run through each of these manually before tagging a release.

### 6. Auth end-to-end
- Set `NEXUS_SECRET_KEY=test-secret` in `.env`
- Start backend
- Confirm `GET /api/system` returns 401 without the header
- Confirm frontend sends `Authorization: Bearer test-secret` on every API call
- Confirm `/healthz` still works without auth

### 7. Docker Compose cold start
- Fresh clone of the repo, nothing running
- `cp .env.example .env` and fill in only the required fields
- `docker compose up --build -d`
- Confirm frontend loads at `http://localhost:3000`
- Confirm backend is healthy at `http://localhost:8088/healthz`

### 8. RAG ingest on startup
- Add at least one `.md` file to `.nexus/automations/`
- Start the backend
- Check logs for "RAG ingest complete" or "Indexed N chunks"
- Send a message in AI chat that references the automation
- Confirm "Based on N sources:" appears below the response

### 9. Onboarding flow
- Clear `nexus_onboarding_complete` from localStorage (`localStorage.removeItem('nexus_onboarding_complete')` in browser console)
- Refresh — onboarding should appear
- Complete all 7 steps
- Confirm weather location, AI model, widget visibility, and grid columns are applied after clicking "Open Nexus"
- Confirm "Quick Start" button closes immediately with all defaults applied
- Confirm "Skip setup →" jumps to step 7

### 10. Preset widget resize
- Enter edit mode
- Drag the bottom-right grip of any widget 100px to the right — should snap to next preset
- Drag back — should snap to previous preset
- Confirm resize label shows e.g. "W — 2col × 340px"
- Confirm size persists after page refresh

### 11. Fluid grid layout
- Confirm widgets in the same row sit flush (no gap between them)
- Confirm a 1px hairline appears between columns and rows
- Confirm no gap/spacing regressions in mobile view (≤700px)

---

## 🟢 Polish — Run These Prompts Through Claude Code

Not blocking launch but needed for a quality v1.

### 12. Phase 6B: Nav & Topbar Polish
Copy **Prompt 6B** from `NEXUS_CLAUDE_CODE_PROMPTS.md` and paste into Claude Code.

Covers: exact nav item active indicator (2.5px inset bar), nav badge pills, topbar height 57px, live timestamp in subtitle, notification bell dot, Ollama status dot, sidebar footer with avatar + host IP.

### 13. Phase 3C: News Error States
Copy **Prompt 3C** from `NEXUS_CLAUDE_CODE_PROMPTS.md` and paste into Claude Code.

Covers: shimmer loading state, error state, empty state for the news widget.

### 14. Phase 6A: Loading Skeletons
Copy **Prompt 6A** from `NEXUS_CLAUDE_CODE_PROMPTS.md` and paste into Claude Code.

Covers: Skeleton + WidgetSkeleton components already exist — verify they are actually wired up inside widgets that fetch data (WeatherWidget, DockerWidget, SystemWidget, etc.).

---

## 🔵 Pre-Publish Checklist

Run through this before pushing to GitHub / Docker Hub.

- [ ] All items in 🔴 section fixed
- [ ] All items in 🟡 section tested and passing
- [ ] `.env` is in `.gitignore` (it is — double-check)
- [ ] No personal data anywhere in tracked files (`git grep -i "wille\|terry\|henri\|192\.168\.68"`)
- [ ] `README.md` is accurate and describes the project for a stranger
- [ ] `docker-compose.yml` works without `docker-compose.gpu.yml`
- [ ] Version string in settings About tab matches the tag you're releasing
- [ ] `NEXUS_SECRET_KEY` is documented clearly in README and `.env.example`

---

## After Launch

Things that would improve the project but aren't needed for v1:

- Rate limiting on `/api/` endpoints
- `NEXUS_SECRET_KEY` rotation UI in Settings
- Multi-user support (currently single shared key by design)
- Automated tests (backend: pytest, frontend: vitest)
- CI/CD pipeline (GitHub Actions: build + push to Docker Hub on tag)
- Phase 4B: Calendar → Markdown files (decided against for v1, revisit later)
