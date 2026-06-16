# Nexus Dashboard — Security Review

**Date:** 2026-06-16
**Scope:** FastAPI backend (`backend/app`), SvelteKit frontend (`frontend/src`), Docker/deploy config, secret handling.
**Reviewer:** Claude (Cowork)

---

## Verdict

**Safe to deploy on a trusted LAN or over Tailscale, with `NEXUS_SECRET_KEY` set.** The core design is sound and several things are done genuinely well.

**Not safe to expose directly to the public internet as-is.** Three things block that: no TLS (the session cookie is sent in cleartext), unsanitized HTML rendering (XSS), and server-side request forgery on the URL-ping endpoints. Fix the HIGH items below before any internet exposure.

There are **no committed secrets and no obvious RCE reachable by an unauthenticated user.** The most serious realistic attack is an XSS that steals the API key from `localStorage`.

---

## What's done well (credit where due)

- `.gitignore` correctly excludes `.env`, and git history confirms **`.env` was never committed.**
- Startup **refuses to boot** with a missing, default, or <16-char secret key (`main.py` lifespan).
- **Path traversal is properly blocked** in `/api/notes/file` (resolves both paths, checks `relative_to`).
- All SQL is **parameterized** — no SQL injection.
- YAML parsing uses `yaml.safe_load` everywhere — no deserialization RCE.
- The logs view **HTML-escapes before highlighting** (`escHtml` then wraps matches) — that path is XSS-safe.
- Wazuh SSL verification **defaults to on**; API docs are disabled when auth is enabled.
- The main compose files route Docker access through a **read-only socket-proxy**, not the raw socket.
- `install.sh` auto-generates a 32-char random key; the Obsidian vault is mounted `:ro`.

---

## Findings (severity-ranked)

### HIGH

**H1 — Unsanitized markdown → HTML rendering (stored XSS), and the API key is reachable from JS.**
`marked.parse()` output is rendered with `{@html ...}` in `AiOverlay.svelte`, `ai/+page.svelte`, `resources/+page.svelte`, and `notes/NotesEditor.svelte`. `marked` v12 does **not** sanitize HTML by default and **no DOMPurify is present anywhere**. So HTML/`<script>`/`<img onerror=...>` in any of these inputs executes:
- AI chat content (the local LLM's output — reachable via prompt injection through RAG context ingested from your Obsidian vault / automation files),
- uploaded resource documents (PDF/PPTX/MD),
- note content.

This matters because `api.ts` stores the secret in `localStorage` as `nexus_api_key`. A successful XSS can read it and exfiltrate it → full authenticated API access, and **arbitrary command execution if `ALLOW_BASH_AUTOMATION` is on** (see M1). The HttpOnly session cookie is safe from JS — but the `localStorage` copy defeats that protection.

*Fix:* sanitize all `marked` output with DOMPurify before `{@html}`, and stop storing the key in `localStorage` — rely on the HttpOnly cookie only (it's already set by `/api/auth/verify`).

**H2 — `docker-compose.hub.yml` mounts the raw Docker socket.**
The main compose files (`docker-compose.yml`, `docker-compose-hub.yml`) correctly use the read-only `docker-socket-proxy`. But `docker-compose.hub.yml` (the dot-variant, still in the repo) mounts `/var/run/docker.sock:/var/run/docker.sock:ro` directly into the backend. **The `:ro` flag does not restrict Docker API calls** — it only makes the socket *file* read-only; the API is fully usable, which is equivalent to **root on the host** (create a privileged container → escape). If anyone runs that file, the backend (and any XSS/RCE in it) owns the host.

*Fix:* delete `docker-compose.hub.yml` or add a clear "INSECURE — do not use" header. Standardize on the socket-proxy variant.

### MEDIUM

**M1 — RCE by design: `bash_script` automation runs `subprocess.run(..., shell=True)`.**
Gated behind `ALLOW_BASH_AUTOMATION` (off by default — good). When enabled, **any holder of the API key can run arbitrary shell commands** in the backend container. This is intentional, but combine it with H1 and it becomes XSS → full RCE.
*Fix:* keep it off; if used, avoid `shell=True`, consider an allowlist, and document the risk loudly.

**M2 — SSRF on URL-fetch endpoints.**
`/api/quicklinks/ping`, `/api/services/ping`, heartbeat host add, and the `webhook` automation all fetch **arbitrary user-supplied URLs server-side**, with `follow_redirects=True`. From inside your network this can probe internal services or hit cloud metadata (`169.254.169.254`). Authenticated + single-user keeps severity moderate.
*Fix:* if ever internet-exposed, block private/link-local/loopback ranges and disable redirects on these pings.

**M3 — Plaintext transport.**
The session cookie is set with `secure=False` and there's no TLS. Fine on a wired/trusted LAN; over untrusted networks the key and cookie are sniffable. Ports also bind to `0.0.0.0` (whole LAN), not loopback.
*Fix:* put it behind a TLS reverse proxy (or Tailscale) before any non-trusted exposure; set `secure=True` then. Optionally bind published ports to your LAN IP only.

### LOW / INFO

- **L1** — API key duplicated in `localStorage` (see H1). Drop it.
- **L2** — Key comparison uses `!=`, not constant-time. Timing attack is impractical against a 32-char random key, but `hmac.compare_digest` is the correct primitive.
- **L3** — No rate limiting on `/api/auth/verify`. Brute force is infeasible against a 32-char key; add a limiter if you expose it publicly.
- **L4** — CORS uses `allow_methods=["*"]`/`allow_headers=["*"]` with `allow_credentials=True`. Acceptable because the origin list is explicit (not `*`).
- **L5** — Your live `.env` holds real secrets (`HA_TOKEN`, `WAZUH_PASS`). It's correctly gitignored and never committed — but note this `_Dashboard` folder is inside **OneDrive**, so those tokens are being synced to the cloud. Consider whether that's acceptable for your threat model.

---

## Priority order

1. Add DOMPurify to all `{@html marked.parse(...)}` sinks and remove the `localStorage` key (H1, L1).
2. Delete or clearly mark `docker-compose.hub.yml` (H2).
3. Keep `ALLOW_BASH_AUTOMATION` off unless you need it (M1).
4. Only expose beyond a trusted LAN behind TLS, and add SSRF guards first (M2, M3).
