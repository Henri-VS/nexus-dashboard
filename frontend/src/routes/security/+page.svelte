<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { Shield, RefreshCw, AlertTriangle, Info, ChevronDown } from '@lucide/svelte';
	import { security as securityApi } from '$lib/api';
	import type { SecurityAlert } from '$lib/types';

	// ── Mock data ─────────────────────────────────────────────────
	const MOCK: SecurityAlert[] = [
		{ id: '1', timestamp: new Date(Date.now() - 12 * 60_000).toISOString(),  severity: 'CRIT', rule_id: '5712',  rule_description: 'SSHD brute-force attempt detected',               rule_level: 12, agent_name: 'homelab-01', src_ip: '203.0.113.42' },
		{ id: '2', timestamp: new Date(Date.now() - 47 * 60_000).toISOString(),  severity: 'HIGH', rule_id: '550',   rule_description: 'Multiple authentication failures (root)',          rule_level: 10, agent_name: 'homelab-01', src_ip: '198.51.100.9' },
		{ id: '3', timestamp: new Date(Date.now() - 2 * 3_600_000).toISOString(),severity: 'WARN', rule_id: '5715',  rule_description: 'PAM: Login session opened for user admin',         rule_level: 5,  agent_name: 'homelab-01', src_ip: '127.0.0.1' },
		{ id: '4', timestamp: new Date(Date.now() - 3 * 3_600_000).toISOString(),severity: 'INFO', rule_id: '31101', rule_description: 'Web server 200 OK — /api/health',                  rule_level: 2,  agent_name: 'nginx',       src_ip: '127.0.0.1' },
		{ id: '5', timestamp: new Date(Date.now() - 4 * 3_600_000).toISOString(),severity: 'HIGH', rule_id: '40101', rule_description: 'Possible port scan from external IP detected',     rule_level: 9,  agent_name: 'homelab-01', src_ip: '45.33.32.156' },
		{ id: '6', timestamp: new Date(Date.now() - 6 * 3_600_000).toISOString(),severity: 'WARN', rule_id: '5501',  rule_description: 'User password changed',                            rule_level: 5,  agent_name: 'homelab-01', src_ip: '192.168.1.50' },
		{ id: '7', timestamp: new Date(Date.now() - 8 * 3_600_000).toISOString(),severity: 'INFO', rule_id: '5502',  rule_description: 'New user account created',                         rule_level: 3,  agent_name: 'homelab-01', src_ip: '192.168.1.50' },
	];

	// ── State ─────────────────────────────────────────────────────
	type Sev = SecurityAlert['severity'];
	type Filter = 'ALL' | Sev;

	let alerts: SecurityAlert[] = [];
	let live    = false;
	let loading = true;
	let refreshing = false;
	let filter: Filter = 'ALL';
	let expandedId: string | null = null;

	async function load(isRefresh = false) {
		if (isRefresh) refreshing = true;
		const res = await securityApi.alerts();
		if (res) { alerts = res.alerts; live = res.live; }
		else      { alerts = MOCK; live = false; }
		loading    = false;
		refreshing = false;
	}

	let timer: ReturnType<typeof setInterval>;
	onMount(() => { load(); timer = setInterval(load, 30_000); });
	onDestroy(() => clearInterval(timer));

	// ── Derived ───────────────────────────────────────────────────
	$: filtered = filter === 'ALL' ? alerts : alerts.filter(a => a.severity === filter);

	$: counts = {
		CRIT: alerts.filter(a => a.severity === 'CRIT').length,
		HIGH: alerts.filter(a => a.severity === 'HIGH').length,
		WARN: alerts.filter(a => a.severity === 'WARN').length,
		INFO: alerts.filter(a => a.severity === 'INFO').length,
	};

	// ── Severity helpers ──────────────────────────────────────────
	const SEV_COLOR: Record<Sev, string> = {
		CRIT: 'var(--red)',
		HIGH: 'var(--red)',
		WARN: 'var(--yellow)',
		INFO: 'var(--accent2)',
	};

	function relTime(iso: string): string {
		const diff = Date.now() - new Date(iso).getTime();
		const m = Math.floor(diff / 60_000);
		if (m < 60)  return `${m}m ago`;
		const h = Math.floor(m / 60);
		if (h < 24)  return `${h}h ago`;
		return `${Math.floor(h / 24)}d ago`;
	}

	function absTime(iso: string): string {
		return new Date(iso).toLocaleString(undefined, {
			year: 'numeric', month: '2-digit', day: '2-digit',
			hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
		});
	}
</script>

<svelte:head><title>Nexus · Security</title></svelte:head>

<!-- ── Page header ─────────────────────────────────────────────── -->
<div class="page-header">
	<div class="header-left">
		<Shield size={18} strokeWidth={1.6} color="var(--red)" />
		<h1 class="page-title">Security</h1>
		<span class="source-badge" class:live class:mock={!live}>
			{live ? 'Wazuh · live' : 'mock data'}
		</span>
	</div>

	<div class="header-right">
		<button
			class="refresh-btn"
			class:spinning={refreshing}
			title="Refresh alerts"
			on:click={() => load(true)}
			disabled={refreshing}
		>
			<RefreshCw size={13} strokeWidth={1.8} />
		</button>
	</div>
</div>

<!-- ── Summary cards ────────────────────────────────────────────── -->
<div class="summary-row">
	{#each (['CRIT', 'HIGH', 'WARN', 'INFO'] as const) as sev}
		<button
			class="summary-card"
			class:active={filter === sev}
			style="--sev: {SEV_COLOR[sev]}"
			on:click={() => { filter = filter === sev ? 'ALL' : sev; }}
		>
			<span class="summary-label">{sev}</span>
			<span class="summary-count">{counts[sev]}</span>
		</button>
	{/each}
	<button
		class="summary-card all"
		class:active={filter === 'ALL'}
		on:click={() => { filter = 'ALL'; }}
	>
		<span class="summary-label">ALL</span>
		<span class="summary-count">{alerts.length}</span>
	</button>
</div>

<!-- ── Alert table ───────────────────────────────────────────────── -->
{#if loading}
	<div class="loading-row">
		<span class="loading-text">Loading alerts…</span>
	</div>
{:else if filtered.length === 0}
	<div class="empty-state">
		<AlertTriangle size={28} strokeWidth={1.4} color="var(--text2)" />
		<p>{filter === 'ALL' ? 'No alerts on record.' : `No ${filter} alerts.`}</p>
	</div>
{:else}
	<div class="table-wrap">
		<table class="alert-table">
			<thead>
				<tr>
					<th>Severity</th>
					<th>Description</th>
					<th>Agent</th>
					<th>Source IP</th>
					<th>Rule</th>
					<th>Time</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
				{#each filtered as alert (alert.id)}
					<tr
						class="alert-row"
						class:expanded={expandedId === alert.id}
						style="--sev: {SEV_COLOR[alert.severity]}"
						on:click={() => { expandedId = expandedId === alert.id ? null : alert.id; }}
					>
						<td>
							<span class="sev-badge" style="color: {SEV_COLOR[alert.severity]}">
								{alert.severity}
							</span>
						</td>
						<td class="desc-cell">{alert.rule_description}</td>
						<td class="mono">{alert.agent_name}</td>
						<td class="mono ip">{alert.src_ip}</td>
						<td class="mono muted">#{alert.rule_id}</td>
						<td class="mono muted nowrap" title={absTime(alert.timestamp)}>
							{relTime(alert.timestamp)}
						</td>
						<td class="chevron-cell">
							<span class="chevron" class:flipped={expandedId === alert.id}>
								<ChevronDown size={12} strokeWidth={2} />
							</span>
						</td>
					</tr>

					{#if expandedId === alert.id}
						<tr class="detail-row">
							<td colspan="7">
								<div class="detail-grid">
									<div class="detail-item">
										<span class="detail-label">Full timestamp</span>
										<span class="detail-val">{absTime(alert.timestamp)}</span>
									</div>
									<div class="detail-item">
										<span class="detail-label">Rule ID</span>
										<span class="detail-val">{alert.rule_id}</span>
									</div>
									<div class="detail-item">
										<span class="detail-label">Rule level</span>
										<span class="detail-val">{alert.rule_level}</span>
									</div>
									<div class="detail-item">
										<span class="detail-label">Agent</span>
										<span class="detail-val">{alert.agent_name}</span>
									</div>
									<div class="detail-item">
										<span class="detail-label">Source IP</span>
										<span class="detail-val">{alert.src_ip}</span>
									</div>
									<div class="detail-item span2">
										<span class="detail-label">Description</span>
										<span class="detail-val">{alert.rule_description}</span>
									</div>
								</div>
							</td>
						</tr>
					{/if}
				{/each}
			</tbody>
		</table>
	</div>

	<p class="footer-note">
		<Info size={10} strokeWidth={2} />
		{filtered.length} of {alerts.length} alerts shown
		{#if !live} · <span class="mock-note">Wazuh not connected — showing mock data</span>{/if}
	</p>
{/if}

<style>
	/* ── Page header ──────────────────────────────────────────── */
	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 1.25rem;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 0.6rem;
	}

	.page-title {
		font-family: var(--font-mono);
		font-size: 1rem;
		font-weight: 600;
		color: var(--text0);
		margin: 0;
	}

	.source-badge {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		padding: 2px 7px;
		border-radius: 10px;
		letter-spacing: 0.04em;
	}
	.source-badge.live {
		background: color-mix(in srgb, var(--accent) 12%, transparent);
		border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent);
		color: var(--accent);
	}
	.source-badge.mock {
		background: color-mix(in srgb, var(--text2) 12%, transparent);
		border: 1px solid var(--border);
		color: var(--text2);
	}

	.refresh-btn {
		display: flex; align-items: center; justify-content: center;
		width: 30px; height: 30px;
		background: none; border: 1px solid var(--border);
		border-radius: 5px; color: var(--text2); cursor: pointer;
		transition: color 0.12s, border-color 0.12s;
	}
	.refresh-btn:hover:not(:disabled) { color: var(--text0); border-color: var(--text1); }
	.refresh-btn:disabled { opacity: 0.5; cursor: default; }

	@keyframes spin { to { transform: rotate(360deg); } }
	.refresh-btn.spinning :global(svg) { animation: spin 0.7s linear infinite; }

	/* ── Summary cards ────────────────────────────────────────── */
	.summary-row {
		display: flex;
		gap: 8px;
		margin-bottom: 1.25rem;
	}

	.summary-card {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 4px;
		padding: 12px 8px;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: 7px;
		cursor: pointer;
		transition: border-color 0.12s, background 0.12s;
	}
	.summary-card:hover { border-color: var(--sev, var(--text2)); }
	.summary-card.active {
		border-color: var(--sev, var(--accent));
		background: color-mix(in srgb, var(--sev, var(--accent)) 8%, var(--bg1));
	}
	.summary-card.all { --sev: var(--text1); }

	.summary-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		letter-spacing: 0.08em;
		color: var(--sev, var(--text1));
		text-transform: uppercase;
	}
	.summary-count {
		font-family: var(--font-mono);
		font-size: 1.5rem;
		font-weight: 700;
		color: var(--sev, var(--text0));
		line-height: 1;
	}
	.summary-card.all .summary-label,
	.summary-card.all .summary-count { color: var(--text1); }
	.summary-card.all.active .summary-label,
	.summary-card.all.active .summary-count { color: var(--text0); }

	/* ── Loading / empty ──────────────────────────────────────── */
	.loading-row {
		padding: 40px 0;
		text-align: center;
	}
	.loading-text {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text2);
	}

	.empty-state {
		display: flex; flex-direction: column; align-items: center;
		gap: 10px; padding: 60px 20px; color: var(--text2);
	}
	.empty-state p {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text2);
		margin: 0;
	}

	/* ── Table ────────────────────────────────────────────────── */
	.table-wrap {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: 8px;
		overflow: hidden;
	}

	.alert-table {
		width: 100%;
		border-collapse: collapse;
		font-family: var(--font-mono);
		font-size: 0.75rem;
	}

	thead tr {
		border-bottom: 1px solid var(--border);
	}

	th {
		padding: 9px 14px;
		text-align: left;
		font-size: 0.62rem;
		font-weight: 600;
		letter-spacing: 0.07em;
		text-transform: uppercase;
		color: var(--text2);
		white-space: nowrap;
	}

	.alert-row {
		cursor: pointer;
		border-left: 3px solid transparent;
		transition: background 0.1s, border-color 0.1s;
	}
	.alert-row:hover { background: var(--bg2); border-left-color: var(--sev); }
	.alert-row.expanded { background: var(--bg2); border-left-color: var(--sev); }

	.alert-row + .alert-row { border-top: 1px solid var(--border); }

	td { padding: 10px 14px; color: var(--text1); vertical-align: middle; }

	.sev-badge {
		font-size: 0.62rem;
		font-weight: 700;
		letter-spacing: 0.06em;
	}

	.desc-cell { color: var(--text0); max-width: 360px; }
	.mono { font-family: var(--font-mono); }
	.ip   { color: var(--accent2); }
	.muted { color: var(--text2); }
	.nowrap { white-space: nowrap; }

	.chevron-cell { width: 24px; padding: 0 8px; }
	.chevron { display: inline-flex; color: var(--text2); transition: transform 0.15s; }
	.chevron.flipped { transform: rotate(180deg); }

	/* ── Expanded detail row ──────────────────────────────────── */
	.detail-row td {
		padding: 0;
		background: color-mix(in srgb, var(--bg2) 60%, var(--bg1));
		border-top: 1px solid var(--border);
	}

	.detail-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0;
		padding: 14px 20px;
	}

	.detail-item {
		display: flex;
		flex-direction: column;
		gap: 3px;
		padding: 8px 12px;
	}
	.detail-item.span2 { grid-column: span 2; }

	.detail-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		letter-spacing: 0.07em;
		text-transform: uppercase;
		color: var(--text2);
	}
	.detail-val {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text0);
	}

	/* ── Footer note ──────────────────────────────────────────── */
	.footer-note {
		display: flex;
		align-items: center;
		gap: 5px;
		margin-top: 10px;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text2);
	}
	.mock-note { color: var(--yellow); }
</style>
