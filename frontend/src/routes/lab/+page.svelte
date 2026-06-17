<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { editMode } from '$lib/stores/dashConfig';
	import { security as securityApi } from '$lib/api';
	import { GripVertical, Eye, EyeOff, ScrollText } from '@lucide/svelte';

	const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8088';

	type Severity = 'ALL' | 'CRIT' | 'HIGH' | 'WARN' | 'INFO';

	interface Alert {
		id:          string;
		severity:    'CRIT' | 'HIGH' | 'WARN' | 'INFO';
		rule_id:     string;
		description: string;
		src_ip:      string;
		agent:       string;
		timestamp:   string;
	}

	interface Container {
		name:     string;
		image:    string;
		status:   'running' | 'exited' | 'paused' | 'restarting';
		uptime:   string;
		restarts: number;
	}

	// ── Mock data ─────────────────────────────────────────────────
	const ALERTS: Alert[] = [
		{ id: '1',  severity: 'CRIT', rule_id: '100010', description: 'Rootkit signatures matched on /tmp',            src_ip: '0.0.0.0',       agent: 'homelab-server', timestamp: '2026-06-07 14:55:02' },
		{ id: '2',  severity: 'CRIT', rule_id: '5710',   description: 'SSH brute force — 12 attempts in 60 s',        src_ip: '203.0.113.42',  agent: 'homelab-server', timestamp: '2026-06-07 14:32:01' },
		{ id: '3',  severity: 'HIGH', rule_id: '31103',  description: 'Multiple failed logins (threshold 5)',          src_ip: '10.0.0.12',     agent: 'pi-hole',        timestamp: '2026-06-07 14:28:44' },
		{ id: '4',  severity: 'HIGH', rule_id: '5715',   description: 'Port scan detected — 200 ports in 3 s',        src_ip: '198.51.100.9',  agent: 'homelab-server', timestamp: '2026-06-07 14:15:30' },
		{ id: '5',  severity: 'HIGH', rule_id: '550',    description: 'System file integrity check failed — /etc/passwd', src_ip: '127.0.0.1', agent: 'homelab-server', timestamp: '2026-06-07 13:59:18' },
		{ id: '6',  severity: 'WARN', rule_id: '1002',   description: 'Syslog error message burst (>50 in 1 min)',     src_ip: '127.0.0.1',     agent: 'homelab-server', timestamp: '2026-06-07 13:55:18' },
		{ id: '7',  severity: 'WARN', rule_id: '5402',   description: 'Successful sudo — privilege escalation',        src_ip: '192.168.1.10',  agent: 'homelab-server', timestamp: '2026-06-07 13:40:02' },
		{ id: '8',  severity: 'WARN', rule_id: '2502',   description: 'New cron entry added to /etc/crontab',          src_ip: '127.0.0.1',     agent: 'homelab-server', timestamp: '2026-06-07 13:12:44' },
		{ id: '9',  severity: 'INFO', rule_id: '5501',   description: 'User login success via SSH key',                src_ip: '192.168.1.10',  agent: 'homelab-server', timestamp: '2026-06-07 13:38:55' },
		{ id: '10', severity: 'INFO', rule_id: '5501',   description: 'User login success (console)',                  src_ip: '192.168.1.10',  agent: 'pi-hole',        timestamp: '2026-06-07 12:10:00' },
	];

	const CONTAINERS: Container[] = [];

	// ── State ─────────────────────────────────────────────────────
	let filter: Severity = 'ALL';
	let liveAlerts: Alert[] | null = null;
	let alertsLive = false;
	let alertsTimer: ReturnType<typeof setInterval>;

	async function fetchAlerts() {
		const res = await securityApi.alerts();
		if (!res) return;
		alertsLive = res.live;
		liveAlerts = res.alerts.map((a) => ({
			id:          a.id,
			severity:    a.severity,
			rule_id:     a.rule_id,
			description: a.rule_description,
			src_ip:      a.src_ip,
			agent:       a.agent_name,
			timestamp:   a.timestamp,
		}));
	}

	$: activeAlerts = liveAlerts ?? ALERTS;
	$: filtered = filter === 'ALL' ? activeAlerts : activeAlerts.filter((a) => a.severity === filter);

	// ── Heartbeat / service history ───────────────────────────────
	interface HbService {
		name:         string;
		status:       'up' | 'down';
		response_ms:  number | null;
		last_checked: string | null;
		uptime_pct:   number | null;
	}

	let hbServices: Record<string, HbService> = {};
	let hbSummary  = '';
	let hbHistories: Record<string, Array<{ status: string; checked_at: string }>> = {};
	let historyOpen  = true;
	let alertsOpen   = true;
	let networkOpen  = true;
	let dockerOpen   = true;
	let hbTimer: ReturnType<typeof setInterval>;

	async function fetchHeartbeat() {
		try {
			const r = await fetch(`${BASE}/api/heartbeat/status`);
			if (!r.ok) return;
			const d = await r.json();
			hbServices = d.services ?? {};
			hbSummary  = d.last_summary ?? '';
			// Fetch history for all services in parallel
			const names = Object.keys(hbServices);
			const results = await Promise.all(
				names.map((n) =>
					fetch(`${BASE}/api/heartbeat/history?service=${encodeURIComponent(n)}`)
						.then((res) => res.ok ? res.json() : null)
						.catch(() => null)
				)
			);
			const hist: typeof hbHistories = {};
			names.forEach((n, i) => {
				if (results[i]) hist[n] = results[i].history ?? [];
			});
			hbHistories = hist;
		} catch { /* backend offline */ }
	}

	function hbTimeAgo(iso: string | null): string {
		if (!iso) return '—';
		const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
		if (m < 1)   return 'now';
		if (m < 60)  return `${m}m`;
		return `${Math.floor(m / 60)}h`;
	}

	function hbDisplayName(name: string): string {
		return name.startsWith('docker/') ? name.slice(7) : name;
	}

	// ── Edit mode layout ──────────────────────────────────────────
	const PAGE_KEY = 'dashboard_config.lab';
	const DEFAULT_ORDER = ['alerts', 'network', 'docker', 'history'];
	const SECTION_LABELS: Record<string, string> = {
		alerts:  'wazuh alerts',
		network: 'network status',
		docker:  'docker containers',
		history: 'service history',
	};

	let sectionOrder: string[] = [...DEFAULT_ORDER];
	let disabledSet  = new Set<string>();
	let draggedId:    string | null = null;
	let dropTargetId: string | null = null;
	let cfgMounted = false;

	onMount(() => {
		try {
			const raw = localStorage.getItem(PAGE_KEY);
			if (raw) {
				const cfg = JSON.parse(raw);
				if (Array.isArray(cfg.order))    sectionOrder = cfg.order;
				if (Array.isArray(cfg.disabled)) disabledSet  = new Set(cfg.disabled);
				if (cfg.collapsed) {
					if ('alerts'  in cfg.collapsed) alertsOpen  = !cfg.collapsed.alerts;
					if ('network' in cfg.collapsed) networkOpen = !cfg.collapsed.network;
					if ('docker'  in cfg.collapsed) dockerOpen  = !cfg.collapsed.docker;
					if ('history' in cfg.collapsed) historyOpen = !cfg.collapsed.history;
				}
			}
		} catch { /* ignore */ }
		try {
			const h = parseInt(localStorage.getItem(LOG_DRAWER_KEY) ?? '', 10);
			if (!isNaN(h)) logsHeight = h;
		} catch { /* ignore */ }
		// Append any new section IDs not yet saved in localStorage
		for (const id of DEFAULT_ORDER) {
			if (!sectionOrder.includes(id)) sectionOrder = [...sectionOrder, id];
		}
		cfgMounted = true;
		fetchAlerts();
		fetchHeartbeat();
		alertsTimer = setInterval(fetchAlerts, 30_000);
		hbTimer     = setInterval(fetchHeartbeat, 60_000);
	});

	onDestroy(() => {
		clearInterval(alertsTimer);
		clearInterval(hbTimer);
	});

	$: if (cfgMounted) {
		try {
			localStorage.setItem(PAGE_KEY, JSON.stringify({
				order:    sectionOrder,
				disabled: [...disabledSet],
				collapsed: {
					alerts:  !alertsOpen,
					network: !networkOpen,
					docker:  !dockerOpen,
					history: !historyOpen,
				},
			}));
		} catch { /* ignore */ }
	}

	function startDrag(id: string) { draggedId = id; }
	function onDragOver(id: string) { if (id !== draggedId) dropTargetId = id; }
	function onDrop(id: string) {
		if (!draggedId || draggedId === id) return;
		const from = sectionOrder.indexOf(draggedId);
		const to   = sectionOrder.indexOf(id);
		if (from < 0 || to < 0) return;
		const arr = [...sectionOrder];
		arr.splice(from, 1);
		arr.splice(to, 0, draggedId);
		sectionOrder = arr;
	}
	function onDragEnd() { draggedId = null; dropTargetId = null; }

	function toggleSection(id: string) {
		const s = new Set(disabledSet);
		if (s.has(id)) s.delete(id); else s.add(id);
		disabledSet = s;
	}

	// ── Log drawer ────────────────────────────────────────────────
	const LOG_DRAWER_KEY = 'dashboard_config.lab.logDrawerH';
	const DRAWER_MIN     = 150;

	let logsOpen           = false;
	let logsHeight         = 300;
	let logEntries: Array<{ts: string; level: string; source: string; message: string}> = [];
	let logsDrawerResizing = false;
	let logsResStartY      = 0;
	let logsResStartH      = 300;

	async function fetchDrawerLogs() {
		try {
			const r = await fetch(`${BASE}/api/logs/history?limit=200`);
			if (!r.ok) return;
			const d = await r.json();
			const all: any[] = d.logs ?? [];
			logEntries = all.filter((l) => ['backend', 'docker', 'wazuh'].includes(l.source));
		} catch { /* offline */ }
	}

	function startDrawerResize(e: MouseEvent | TouchEvent) {
		const cy = 'touches' in e ? (e as TouchEvent).touches[0].clientY : (e as MouseEvent).clientY;
		logsDrawerResizing = true;
		logsResStartY = cy;
		logsResStartH = logsHeight;
		e.preventDefault();
	}

	function onDrawerResizeMove(e: MouseEvent | TouchEvent) {
		if (!logsDrawerResizing) return;
		const cy = 'touches' in e ? (e as TouchEvent).touches[0].clientY : (e as MouseEvent).clientY;
		const maxH = window.innerHeight * 0.8;
		logsHeight = Math.max(DRAWER_MIN, Math.min(maxH, Math.round(logsResStartH - (cy - logsResStartY))));
	}

	function stopDrawerResize() {
		if (!logsDrawerResizing) return;
		logsDrawerResizing = false;
		try { localStorage.setItem(LOG_DRAWER_KEY, String(logsHeight)); } catch { /* ignore */ }
	}

	function drawerLevelColor(level: string): string {
		const l = level.toUpperCase();
		if (l === 'ERROR' || l === 'CRITICAL') return 'var(--red)';
		if (l === 'WARNING' || l === 'WARN')   return 'var(--yellow)';
		if (l === 'INFO')                       return 'var(--green)';
		return 'var(--text2)';
	}

	// ── Helpers ───────────────────────────────────────────────────
	function sevColor(s: string): string {
		if (s === 'CRIT' || s === 'HIGH') return 'var(--red)';
		if (s === 'WARN')                 return 'var(--yellow)';
		return 'var(--accent2)';
	}

	const STATUS_COLOR: Record<string, string> = {
		running:    'var(--green)',
		exited:     'var(--red)',
		paused:     'var(--yellow)',
		restarting: 'var(--yellow)',
	};
</script>

<svelte:head>
	<title>Nexus — Lab</title>
</svelte:head>

<svelte:window
	on:mousemove={onDrawerResizeMove}
	on:mouseup={stopDrawerResize}
	on:touchmove|passive={false}
	on:touchend={stopDrawerResize}
/>

<div class="lab-page">

	{#each sectionOrder as id (id)}
		{#if !disabledSet.has(id) || $editMode}
			<div
				class="section-wrap"
				role="region"
				aria-label={SECTION_LABELS[id]}
				class:is-dragging={draggedId === id}
				class:is-target={dropTargetId === id}
				class:is-hidden={disabledSet.has(id)}
				draggable={$editMode ? 'true' : 'false'}
				on:dragstart={() => startDrag(id)}
				on:dragover|preventDefault={() => onDragOver(id)}
				on:drop|preventDefault={() => onDrop(id)}
				on:dragend={onDragEnd}
			>
				{#if $editMode}
					<div class="edit-bar">
						<GripVertical size={13} strokeWidth={1.5} class="grip" />
						<span class="edit-label">{SECTION_LABELS[id]}</span>
						<button
							class="vis-btn"
							on:click={() => toggleSection(id)}
							title={disabledSet.has(id) ? 'Show section' : 'Hide section'}
							aria-label={disabledSet.has(id) ? 'Show section' : 'Hide section'}
						>
							{#if disabledSet.has(id)}
								<EyeOff size={13} strokeWidth={1.5} />
							{:else}
								<Eye size={13} strokeWidth={1.5} />
							{/if}
						</button>
					</div>
				{/if}

				{#if id === 'alerts'}
					<!-- ── Alert feed ─────────────────────────────── -->
					<section class="section">
						<div class="section-header">
							<div class="title-row">
								<span class="accent-bar" style="background: var(--red)"></span>
								<h2>wazuh alerts</h2>
								<span class="pill" style="color: var(--red); border-color: color-mix(in srgb, var(--red) 30%, var(--border))">
									{activeAlerts.length} events
								</span>
							</div>
							<div class="header-right">
								{#if !alertsLive}<span class="offline-badge">— offline —</span>{/if}
								<a href="/logs" class="view-logs-link">view logs →</a>
								<div class="filter-bar" role="group" aria-label="Filter severity">
									{#each ['ALL', 'CRIT', 'HIGH', 'WARN', 'INFO'] as sev}
										<button
											class="filter-btn"
											class:active={filter === sev}
											style={filter === sev && sev !== 'ALL' ? `color:${sevColor(sev)};border-color:color-mix(in srgb,${sevColor(sev)} 40%,var(--border))` : ''}
											on:click={() => (filter = sev as Severity)}
										>{sev}</button>
									{/each}
								</div>
								<button
									class="collapse-btn"
									on:click={() => (alertsOpen = !alertsOpen)}
									aria-label={alertsOpen ? 'Collapse' : 'Expand'}
								>{alertsOpen ? '▲' : '▼'}</button>
							</div>
						</div>
						{#if alertsOpen}
						<div class="scroll-wrap">
							<table>
								<thead>
									<tr>
										<th>SEV</th><th>RULE</th><th>DESCRIPTION</th><th>SRC IP</th><th>AGENT</th><th>TIME</th>
									</tr>
								</thead>
								<tbody>
									{#each filtered as a (a.id)}
										<tr>
											<td>
												<span class="sev-badge"
													style="color:{sevColor(a.severity)};border-color:color-mix(in srgb,{sevColor(a.severity)} 30%,var(--border));background:color-mix(in srgb,{sevColor(a.severity)} 10%,transparent)"
												>{a.severity}</span>
											</td>
											<td><code class="mono">{a.rule_id}</code></td>
											<td class="desc">{a.description}</td>
											<td><code class="mono ip">{a.src_ip}</code></td>
											<td class="agent">{a.agent}</td>
											<td><code class="mono dim">{a.timestamp}</code></td>
										</tr>
									{/each}
									{#if filtered.length === 0}
										<tr><td colspan="6" class="empty">no alerts match this filter</td></tr>
									{/if}
								</tbody>
							</table>
						</div>
						{/if}
					</section>

				{:else if id === 'network'}
					<!-- ── Network stats ──────────────────────────── -->
					<section class="section">
						<div class="section-header">
							<div class="title-row">
								<span class="accent-bar" style="background: var(--accent2)"></span>
								<h2>network status</h2>
							</div>
							<div class="header-right">
								<span class="offline-badge">— offline —</span>
								<button
									class="collapse-btn"
									on:click={() => (networkOpen = !networkOpen)}
									aria-label={networkOpen ? 'Collapse' : 'Expand'}
								>{networkOpen ? '▲' : '▼'}</button>
							</div>
						</div>
						{#if networkOpen}
						<div class="stat-row">
							<div class="stat-card">
								<span class="stat-label">active connections</span>
								<span class="stat-val" style="color: var(--accent2)">147</span>
								<span class="stat-sub">TCP established</span>
							</div>
							<div class="stat-card">
								<span class="stat-label">blocked IPs</span>
								<span class="stat-val" style="color: var(--red)">23</span>
								<span class="stat-sub">firewall DROP entries</span>
							</div>
							<div class="stat-card">
								<span class="stat-label">events last 24h</span>
								<span class="stat-val" style="color: var(--yellow)">168</span>
								<span class="stat-sub">2 critical · 3 high</span>
							</div>
						</div>
						{/if}
					</section>

				{:else if id === 'history'}
					<!-- ── Service history sparklines ─────────────── -->
					<section class="section">
						<div class="section-header">
							<div class="title-row">
								<span class="accent-bar" style="background: var(--accent2)"></span>
								<h2>service history</h2>
								{#if hbSummary}
									<span class="hb-summary">{hbSummary}</span>
								{/if}
							</div>
							<button
								class="collapse-btn"
								on:click={() => (historyOpen = !historyOpen)}
								aria-label={historyOpen ? 'Collapse' : 'Expand'}
							>
								{historyOpen ? '▲' : '▼'}
							</button>
						</div>

						{#if historyOpen}
							{#if Object.keys(hbServices).length === 0}
								<div class="hb-empty">No heartbeat data yet — checks run every 15 minutes.</div>
							{:else}
								<div class="hb-grid">
									{#each Object.entries(hbServices) as [name, svc]}
										<div class="hb-row">
											<div class="hb-meta">
												<span
													class="hb-dot"
													class:up={svc.status === 'up'}
													class:down={svc.status === 'down'}
												></span>
												<span class="hb-name" title={name}>{hbDisplayName(name)}</span>
												<span
													class="hb-pct"
													style="color:{svc.uptime_pct != null && svc.uptime_pct >= 95 ? 'var(--green)' : svc.uptime_pct != null && svc.uptime_pct >= 80 ? 'var(--yellow)' : 'var(--red)'}"
												>
													{svc.uptime_pct != null ? svc.uptime_pct + '%' : '—'}
												</span>
												<span class="hb-ago">{hbTimeAgo(svc.last_checked)}</span>
											</div>
											<div class="sparkline" aria-label="24h uptime for {name}">
												{#each (hbHistories[name] ?? []) as check}
													<span
														class="spark"
														class:spark-up={check.status === 'up'}
														class:spark-down={check.status === 'down'}
														title="{check.status} · {new Date(check.checked_at).toLocaleTimeString()}"
													></span>
												{/each}
												{#if !(hbHistories[name]?.length)}
													<span class="spark-none">no data yet</span>
												{/if}
											</div>
										</div>
									{/each}
								</div>
							{/if}
						{/if}
					</section>

				{:else if id === 'docker'}
					<!-- ── Docker table ───────────────────────────── -->
					<section class="section">
						<div class="section-header">
							<div class="title-row">
								<span class="accent-bar" style="background: var(--teal)"></span>
								<h2>docker containers</h2>
								{#if CONTAINERS.length > 0}
								<span class="pill" style="color: var(--green); border-color: color-mix(in srgb, var(--green) 30%, var(--border))">
									{CONTAINERS.filter((c) => c.status === 'running').length}/{CONTAINERS.length} running
								</span>
								{/if}
							</div>
							<div class="header-right">
							<span class="offline-badge">— offline —</span>
							<button
								class="collapse-btn"
								on:click={() => (dockerOpen = !dockerOpen)}
								aria-label={dockerOpen ? 'Collapse' : 'Expand'}
							>{dockerOpen ? '▲' : '▼'}</button>
						</div>
						</div>
						{#if dockerOpen}
						{#if CONTAINERS.length === 0}
						<div class="empty">Connect Docker to see your containers</div>
						{:else}
						<div class="scroll-wrap">
							<table>
								<thead>
									<tr>
										<th></th><th>NAME</th><th>IMAGE</th><th>STATUS</th><th>UPTIME</th><th>RESTARTS</th>
									</tr>
								</thead>
								<tbody>
									{#each CONTAINERS as c}
										<tr>
											<td><span class="dot" style="background:{STATUS_COLOR[c.status]}"></span></td>
											<td><code class="mono">{c.name}</code></td>
											<td class="dim-cell">{c.image}</td>
											<td>
												<span class="sev-badge"
													style="color:{STATUS_COLOR[c.status]};border-color:color-mix(in srgb,{STATUS_COLOR[c.status]} 30%,var(--border))"
												>{c.status}</span>
											</td>
											<td><code class="mono">{c.uptime}</code></td>
											<td class={c.restarts > 0 ? 'warn-val' : 'dim-val'}>{c.restarts}</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
						{/if}
						{/if}
					</section>
				{/if}

			</div>
		{/if}
	{/each}

</div>

<!-- ── Log drawer FAB ──────────────────────────────────────────── -->
<button
	class="logs-fab"
	on:click={() => { logsOpen = !logsOpen; if (logsOpen) fetchDrawerLogs(); }}
	title="Toggle log drawer"
>
	<ScrollText size={15} strokeWidth={1.5} />
	Logs
</button>

{#if logsOpen}
<div
	class="log-drawer"
	class:is-resizing={logsDrawerResizing}
	style="height: {logsHeight}px"
>
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="drawer-resize-handle"
		title="Drag to resize"
		on:mousedown={startDrawerResize}
		on:touchstart={startDrawerResize}
	></div>

	<div class="drawer-header">
		<ScrollText size={13} strokeWidth={1.5} />
		<span class="drawer-title">logs</span>
		<span class="drawer-sources">backend · docker · wazuh</span>
		<span class="drawer-count">{logEntries.length} entries</span>
		<button class="drawer-close" on:click={() => (logsOpen = false)} title="Close">✕</button>
	</div>

	<div class="drawer-body">
		{#if logEntries.length === 0}
			<div class="drawer-empty">No log entries — backend may be offline or no logs yet.</div>
		{:else}
			{#each logEntries as entry}
				<div class="log-row">
					<span class="log-level" style="color: {drawerLevelColor(entry.level)}">{entry.level.slice(0,4)}</span>
					<span class="log-src">{entry.source}</span>
					<span class="log-ts">{entry.ts.slice(11, 19)}</span>
					<span class="log-msg">{entry.message}</span>
				</div>
			{/each}
		{/if}
	</div>
</div>
{/if}

<style>
	.lab-page {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	/* ── Edit mode ──────────────────────────────────────────── */
	.section-wrap {
		display: flex;
		flex-direction: column;
	}

	.section-wrap.is-dragging {
		opacity: 0.45;
		outline: 2px dashed var(--accent);
		outline-offset: 2px;
		border-radius: var(--radius);
	}

	.section-wrap.is-target {
		outline: 2px dashed var(--accent3);
		outline-offset: 2px;
		border-radius: var(--radius);
	}

	.section-wrap.is-hidden { opacity: 0.35; }

	.edit-bar {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.3rem 0.75rem;
		background: color-mix(in srgb, var(--accent) 8%, var(--bg2));
		border: 1px dashed color-mix(in srgb, var(--accent) 35%, var(--border));
		border-bottom: none;
		border-radius: var(--radius) var(--radius) 0 0;
		cursor: grab;
		user-select: none;
	}

	.edit-bar :global(.grip) { color: var(--text2); flex-shrink: 0; }

	.edit-label {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text2);
		flex: 1;
	}

	.vis-btn {
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		padding: 0.15rem;
		border-radius: 3px;
		display: flex;
		align-items: center;
		transition: color 0.1s;
	}

	.vis-btn:hover { color: var(--text0); }

	/* ── Section ────────────────────────────────────────────── */
	.section {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.65rem 1rem;
		border-bottom: 1px solid var(--border);
		gap: 0.75rem;
		flex-wrap: wrap;
	}

	.title-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.accent-bar {
		width: 3px;
		height: 1rem;
		border-radius: 2px;
		flex-shrink: 0;
	}

	h2 {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text1);
		margin: 0;
	}

	.pill {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		border: 1px solid;
		border-radius: 20px;
		padding: 0.1rem 0.5rem;
	}

	.offline-badge {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		letter-spacing: 0.04em;
		flex-shrink: 0;
	}

	.view-logs-link {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--red);
		text-decoration: none;
		flex-shrink: 0;
	}
	.view-logs-link:hover { text-decoration: underline; }

	.header-right {
		display: flex;
		align-items: center;
		gap: 0.75rem;
	}

	/* ── Filter buttons ─────────────────────────────────────── */
	.filter-bar { display: flex; gap: 0.2rem; }

	.filter-btn {
		background: none;
		border: 1px solid var(--border);
		border-radius: 3px;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 700;
		padding: 0.2rem 0.5rem;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}

	.filter-btn:hover { color: var(--text0); border-color: var(--text1); }
	.filter-btn.active { background: color-mix(in srgb, currentColor 8%, transparent); }

	/* ── Table shared ───────────────────────────────────────── */
	.scroll-wrap { overflow-x: auto; }

	table {
		width: 100%;
		border-collapse: collapse;
		font-family: var(--font-mono);
		font-size: 0.78rem;
	}

	thead tr { border-bottom: 1px solid var(--border); }

	th {
		padding: 0.45rem 0.75rem;
		text-align: left;
		font-size: 0.62rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text2);
		white-space: nowrap;
	}

	tbody tr {
		border-bottom: 1px solid color-mix(in srgb, var(--border) 50%, transparent);
		transition: background 0.1s;
	}

	tbody tr:last-child { border-bottom: none; }
	tbody tr:hover      { background: var(--bg2); }

	tbody td {
		padding: 0.42rem 0.75rem;
		color: var(--text0);
		vertical-align: middle;
	}

	.sev-badge {
		display: inline-block;
		font-family: var(--font-mono);
		font-size: 0.62rem;
		font-weight: 700;
		border: 1px solid;
		border-radius: 3px;
		padding: 0.08rem 0.4rem;
		white-space: nowrap;
	}

	.mono     { font-family: var(--font-mono); font-size: 0.75rem; color: var(--text1); background: none; border: none; padding: 0; }
	.mono.ip  { color: var(--accent2); }
	.mono.dim { color: var(--text2); font-size: 0.68rem; }

	.desc  { color: var(--text0); max-width: 260px; }
	.agent { color: var(--text1); white-space: nowrap; }

	.dim-cell { font-family: var(--font-mono); font-size: 0.68rem; color: var(--text2); max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.warn-val { font-family: var(--font-mono); font-weight: 700; color: var(--yellow); }
	.dim-val  { font-family: var(--font-mono); color: var(--text2); }

	.empty { padding: 1.25rem 0.75rem; text-align: center; color: var(--text2); font-family: var(--font-mono); font-size: 0.78rem; }

	.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; }

	/* ── Network stats ──────────────────────────────────────── */
	.stat-row {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
	}

	.stat-card {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		padding: 1.1rem 1.5rem;
		border-right: 1px solid var(--border);
	}

	.stat-card:last-child { border-right: none; }

	.stat-label {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text2);
	}

	.stat-val {
		font-family: var(--font-mono);
		font-size: 2rem;
		font-weight: 700;
		line-height: 1.1;
	}

	.stat-sub {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
	}

	@media (max-width: 700px) {
		.stat-row { grid-template-columns: 1fr; }
		.stat-card { border-right: none; border-bottom: 1px solid var(--border); }
		.stat-card:last-child { border-bottom: none; }
		.dim-cell { display: none; }
	}

	/* ── Service history ─────────────────────────────────────── */
	.collapse-btn {
		background: none;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.6rem;
		padding: 0.1rem 0.45rem;
		cursor: pointer;
		flex-shrink: 0;
		min-height: unset;
		transition: color 0.1s, border-color 0.1s;
	}
	.collapse-btn:hover { color: var(--accent2); border-color: var(--accent2); }

	.hb-summary {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		font-style: italic;
		color: var(--text1);
		margin-left: 0.75rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.hb-empty {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text2);
		padding: 1rem 0;
	}

	.hb-grid {
		display: flex;
		flex-direction: column;
		gap: 0.6rem;
		padding: 0.5rem 0;
	}

	.hb-row {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.hb-meta {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-family: var(--font-mono);
		font-size: 0.7rem;
	}

	.hb-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--text2);
		flex-shrink: 0;
		transition: background 0.3s;
	}
	.hb-dot.up   { background: var(--green); }
	.hb-dot.down { background: var(--red);   }

	.hb-name {
		color: var(--text0);
		font-weight: 600;
		min-width: 120px;
	}

	.hb-pct {
		font-size: 0.65rem;
		font-weight: 700;
		min-width: 36px;
	}

	.hb-ago {
		color: var(--text2);
		font-size: 0.65rem;
	}

	/* ── Sparkline ───────────────────────────────────────────── */
	.sparkline {
		display: flex;
		align-items: center;
		gap: 2px;
		flex-wrap: nowrap;
		overflow-x: auto;
		padding-bottom: 2px;
		scrollbar-width: none;
	}
	.sparkline::-webkit-scrollbar { display: none; }

	.spark {
		display: inline-block;
		flex-shrink: 0;
		width: 8px;
		height: 20px;
		border-radius: 2px;
		background: var(--bg3);
	}
	.spark-up   { background: var(--green); opacity: 0.8; }
	.spark-down { background: var(--red);                 }

	.spark-none {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text2);
		font-style: italic;
	}

	/* ── Log drawer FAB ─────────────────────────────────────────── */
	.logs-fab {
		position: fixed;
		bottom: 1.25rem;
		right: 1.25rem;
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.45rem 0.85rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 999px;
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		cursor: pointer;
		z-index: 100;
		transition: color 0.12s, border-color 0.12s, background 0.12s;
		box-shadow: 0 4px 12px rgba(0,0,0,0.3);
	}
	.logs-fab:hover {
		color: var(--accent);
		border-color: var(--accent);
		background: color-mix(in srgb, var(--accent) 8%, var(--bg2));
	}

	/* ── Log drawer ─────────────────────────────────────────────── */
	.log-drawer {
		position: fixed;
		bottom: 0;
		left: 52px; /* sidebar width */
		right: 0;
		background: var(--bg1);
		border-top: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		z-index: 90;
		min-height: 150px;
	}

	.log-drawer.is-resizing { user-select: none; }

	.drawer-resize-handle {
		width: 100%;
		height: 4px;
		cursor: row-resize;
		background: var(--border);
		flex-shrink: 0;
		transition: background 0.12s;
		touch-action: none;
	}
	.drawer-resize-handle:hover,
	.log-drawer.is-resizing .drawer-resize-handle {
		background: var(--accent);
	}

	.drawer-header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.35rem 1rem;
		border-bottom: 1px solid var(--border);
		background: var(--bg2);
		flex-shrink: 0;
		color: var(--text2);
	}

	.drawer-title {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--text0);
	}

	.drawer-sources {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
	}

	.drawer-count {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--accent);
		margin-left: auto;
	}

	.drawer-close {
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		font-size: 0.8rem;
		padding: 0.1rem 0.25rem;
		border-radius: 3px;
		transition: color 0.1s;
	}
	.drawer-close:hover { color: var(--text0); }

	.drawer-body {
		flex: 1;
		overflow-y: auto;
		padding: 0.25rem 0;
		scrollbar-width: thin;
		scrollbar-color: var(--border) transparent;
	}

	.drawer-empty {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text2);
		padding: 1.5rem 1rem;
		text-align: center;
	}

	.log-row {
		display: grid;
		grid-template-columns: 3.5rem 4rem 4.5rem 1fr;
		gap: 0.5rem;
		align-items: baseline;
		padding: 0.12rem 1rem;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		border-bottom: 1px solid color-mix(in srgb, var(--border) 40%, transparent);
	}
	.log-row:hover { background: var(--bg2); }

	.log-level {
		font-weight: 700;
		font-size: 0.62rem;
		flex-shrink: 0;
	}

	.log-src {
		color: var(--accent2);
		font-size: 0.65rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.log-ts {
		color: var(--text2);
		font-size: 0.62rem;
		flex-shrink: 0;
	}

	.log-msg {
		color: var(--text1);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	@media (max-width: 768px) {
		.log-drawer { left: 0; bottom: 56px; }
		.logs-fab   { bottom: 4.5rem; }
		.log-row    { grid-template-columns: 3rem 3.5rem 1fr; }
		.log-ts     { display: none; }
	}
</style>
