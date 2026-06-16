<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import WidgetSkeleton from '$lib/components/WidgetSkeleton.svelte';
	import { heartbeat as heartbeatApi, type HBHost } from '$lib/api';
	import { editMode } from '$lib/stores/dashConfig';
	import { Lock, Trash2, Plus } from '@lucide/svelte';

	interface ServiceStatus {
		name:         string;
		status:       'up' | 'down';
		response_ms:  number | null;
		last_checked: string | null;
		last_seen_up: string | null;
		uptime_pct:   number | null;
	}

	interface StatusResponse {
		services:     Record<string, ServiceStatus>;
		last_summary: string;
		fetched_at:   string;
	}

	// ── State ─────────────────────────────────────────────────────
	let data:    StatusResponse | null = null;
	let hosts:   HBHost[]             = [];
	let loading  = true;
	let skeletonMinShown = false;
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	// Add-host form
	let showAdd = false;
	let newName = '';
	let newUrl  = 'http://';
	let adding  = false;

	$: services = data ? Object.values(data.services) : [];
	$: summary  = data?.last_summary ?? '';
	$: hostMap  = Object.fromEntries(hosts.map((h) => [h.name, h])) as Record<string, HBHost>;

	// ── Load ──────────────────────────────────────────────────────
	async function load() {
		const res = await heartbeatApi.status();
		if (res) data = res as unknown as StatusResponse;
		loading = false;
	}

	async function loadHosts() {
		const res = await heartbeatApi.hosts();
		if (res) hosts = res.hosts;
	}

	// ── Host management ──────────────────────────────────────────
	async function addHost() {
		if (!newName.trim() || !newUrl.trim()) return;
		adding = true;
		await heartbeatApi.addHost(newName.trim(), newUrl.trim());
		newName = '';
		newUrl  = 'http://';
		showAdd = false;
		adding  = false;
		await loadHosts();
	}

	async function removeHost(id: string) {
		await heartbeatApi.removeHost(id);
		await loadHosts();
	}

	// ── Helpers ───────────────────────────────────────────────────
	function timeAgo(iso: string | null): string {
		if (!iso) return '—';
		const diff = Date.now() - new Date(iso).getTime();
		const m    = Math.floor(diff / 60_000);
		if (m < 1)  return 'just now';
		if (m < 60) return `${m}m ago`;
		return `${Math.floor(m / 60)}h ago`;
	}

	function uptimeColor(pct: number | null): string {
		if (pct === null) return 'var(--text2)';
		if (pct >= 95)   return 'var(--green)';
		if (pct >= 80)   return 'var(--yellow)';
		return 'var(--red)';
	}

	function displayName(name: string): string {
		return name.startsWith('docker/') ? name.slice(7) : name;
	}

	onMount(() => {
		setTimeout(() => { skeletonMinShown = true; }, 400);
		load();
		loadHosts();
		pollTimer = setInterval(load, 60_000);
	});

	onDestroy(() => {
		if (pollTimer) clearInterval(pollTimer);
	});
</script>

<div class="widget">
	<div class="accent-bar"></div>
	<div class="body">

		<div class="header">
			<span class="title">heartbeat</span>
			{#if data}
				<span class="count" class:warn={services.some((s) => s.status === 'down')}>
					{services.filter((s) => s.status === 'up').length}/{services.length} up
				</span>
			{/if}
		</div>

		{#if summary}
			<p class="summary">{summary}</p>
		{/if}

		{#if !skeletonMinShown || loading}
			<WidgetSkeleton variant="list" />
		{:else if !data || services.length === 0}
			<div class="empty">no heartbeat data — backend starting…</div>
		{:else}
			<div class="service-list">
				{#each services as svc}
					{@const host = hostMap[svc.name]}
					<div class="row" class:editable={$editMode}>
						<span
							class="dot"
							class:up={svc.status === 'up'}
							class:down={svc.status === 'down'}
							title={svc.status}
						></span>

						<span class="svc-name" title={svc.name}>{displayName(svc.name)}</span>

						<span class="ms">
							{#if svc.response_ms != null}{svc.response_ms}ms{:else}—{/if}
						</span>

						<span class="ago">{timeAgo(svc.last_checked)}</span>

						{#if $editMode}
							{#if host?.auto}
								<span class="auto-badge">auto</span>
							{:else}
								<span class="uptime" style="color:{uptimeColor(svc.uptime_pct)}">
									{#if svc.uptime_pct != null}{svc.uptime_pct}%{:else}—{/if}
								</span>
							{/if}
							<div class="row-act">
								{#if host?.auto}
									<span class="lock-icon" title="Auto-configured from .env">
										<Lock size={10} strokeWidth={1.8} />
									</span>
								{:else if host?.id}
									<button
										class="rm-btn"
										title="Remove host"
										on:click={() => host.id && removeHost(host.id)}
									>
										<Trash2 size={10} strokeWidth={1.8} />
									</button>
								{/if}
							</div>
						{:else}
							<span class="uptime" style="color:{uptimeColor(svc.uptime_pct)}">
								{#if svc.uptime_pct != null}{svc.uptime_pct}%{:else}—{/if}
							</span>
						{/if}
					</div>
				{/each}
			</div>

			<!-- Edit mode: add host form -->
			{#if $editMode}
				{#if showAdd}
					<div class="add-form">
						<input
							class="add-inp"
							type="text"
							placeholder="Name"
							bind:value={newName}
							on:keydown={(e) => e.key === 'Enter' && addHost()}
						/>
						<input
							class="add-inp add-inp-url"
							type="url"
							placeholder="http://192.168.1.10:8096"
							bind:value={newUrl}
							on:keydown={(e) => e.key === 'Enter' && addHost()}
						/>
						<button class="add-btn" on:click={addHost} disabled={adding}>
							{adding ? '…' : 'Add'}
						</button>
						<button class="cancel-btn" on:click={() => { showAdd = false; newName = ''; newUrl = 'http://'; }}>
							✕
						</button>
					</div>
				{:else}
					<button class="add-trigger" on:click={() => (showAdd = true)}>
						<Plus size={10} strokeWidth={2} />
						Add host
					</button>
				{/if}
			{/if}
		{/if}

	</div>
</div>

<style>
	.widget {
		display: flex;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
	}

	.accent-bar {
		width: 3px;
		background: var(--accent2);
		flex-shrink: 0;
	}

	.body {
		flex: 1;
		padding: 0.7rem 0.85rem;
		min-width: 0;
	}

	/* ── Header ──────────────────────────────────────────────── */
	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.5rem;
	}

	.title {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text2);
	}

	.count {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--green);
	}
	.count.warn { color: var(--red); }

	/* ── Summary ─────────────────────────────────────────────── */
	.summary {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		font-style: italic;
		color: var(--text1);
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 0.35rem 0.6rem;
		margin-bottom: 0.6rem;
		line-height: 1.5;
	}

	/* ── Service rows ────────────────────────────────────────── */
	.service-list {
		display: flex;
		flex-direction: column;
		gap: 0;
		min-height: 220px;
		max-height: 400px;
		overflow-y: auto;
	}

	/* Normal mode: dot | name | ms | ago | uptime (5 cols) */
	.row {
		display: grid;
		grid-template-columns: 10px 1fr 52px 52px 36px;
		align-items: center;
		gap: 0.5rem;
		padding: 0.28rem 0;
		border-bottom: 1px solid var(--border);
		font-family: var(--font-mono);
		font-size: 0.7rem;
	}
	.row:last-child { border-bottom: none; }

	/* Edit mode: dot | name | ms | ago | badge/uptime | action (6 cols) */
	.row.editable {
		grid-template-columns: 10px 1fr 44px 44px 30px 22px;
	}

	.dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--text2);
		flex-shrink: 0;
		transition: background 0.3s;
	}
	.dot.up   { background: var(--green); }
	.dot.down { background: var(--red);   }

	.svc-name {
		color: var(--text0);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.ms {
		color: var(--text2);
		text-align: right;
		font-size: 0.65rem;
	}

	.ago {
		color: var(--text2);
		text-align: right;
		font-size: 0.65rem;
	}

	.uptime {
		text-align: right;
		font-size: 0.65rem;
		font-weight: 600;
	}

	/* ── Edit mode: auto badge ───────────────────────────────── */
	.auto-badge {
		font-family: var(--font-mono);
		font-size: 9px;
		color: #484f58;
		text-align: right;
	}

	/* ── Edit mode: row actions ──────────────────────────────── */
	.row-act {
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.lock-icon {
		display: flex;
		align-items: center;
		color: var(--text2);
	}

	.rm-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 20px;
		height: 20px;
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		border-radius: 3px;
		padding: 0;
		min-height: unset;
		transition: color 0.1s, background 0.1s;
	}
	.rm-btn:hover {
		color: var(--red);
		background: color-mix(in srgb, var(--red) 10%, transparent);
	}

	/* ── Add host UI ─────────────────────────────────────────── */
	.add-trigger {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		margin-top: 0.5rem;
		padding: 0.2rem 0.4rem;
		background: none;
		border: 1px dashed var(--border);
		border-radius: 4px;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.65rem;
		cursor: pointer;
		min-height: unset;
		transition: color 0.1s, border-color 0.1s;
		width: 100%;
		justify-content: center;
	}
	.add-trigger:hover { color: var(--text1); border-color: var(--text2); }

	.add-form {
		display: flex;
		gap: 0.3rem;
		margin-top: 0.5rem;
		flex-wrap: wrap;
	}

	.add-inp {
		flex: 1;
		min-width: 80px;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 0.2rem 0.4rem;
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text0);
		outline: none;
		transition: border-color 0.1s;
	}
	.add-inp:focus        { border-color: var(--accent2); }
	.add-inp::placeholder { color: var(--text2); }
	.add-inp-url          { flex: 2; min-width: 140px; }

	.add-btn {
		padding: 0.2rem 0.6rem;
		background: var(--accent);
		border: 1px solid var(--accent);
		border-radius: 4px;
		color: #0d1117;
		font-family: var(--font-mono);
		font-size: 0.68rem;
		font-weight: 700;
		cursor: pointer;
		min-height: unset;
		transition: opacity 0.1s;
	}
	.add-btn:hover    { opacity: 0.85; }
	.add-btn:disabled { opacity: 0.4; cursor: not-allowed; }

	.cancel-btn {
		padding: 0.2rem 0.45rem;
		background: none;
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		cursor: pointer;
		min-height: unset;
		transition: color 0.1s;
	}
	.cancel-btn:hover { color: var(--text1); }

	/* ── States ──────────────────────────────────────────────── */
	.empty {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text2);
		padding: 0.75rem 0;
	}
</style>
