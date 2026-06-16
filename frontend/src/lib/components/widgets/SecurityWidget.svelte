<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { security as securityApi } from '$lib/api';
	import type { SecurityAlert } from '$lib/types';
	import Card from '$lib/components/Card.svelte';
	import WidgetSkeleton from '$lib/components/WidgetSkeleton.svelte';

	// ── Mock ─────────────────────────────────────────────────────
	const MOCK: SecurityAlert[] = [
		{
			id: '1',
			timestamp: new Date(Date.now() - 12 * 60_000).toISOString(),
			severity: 'CRIT',
			rule_id: '5712',
			rule_description: 'SSHD brute-force attempt detected',
			rule_level: 12,
			agent_name: 'homelab-01',
			src_ip: '203.0.113.42',
		},
		{
			id: '2',
			timestamp: new Date(Date.now() - 47 * 60_000).toISOString(),
			severity: 'HIGH',
			rule_id: '550',
			rule_description: 'Multiple authentication failures (root)',
			rule_level: 10,
			agent_name: 'homelab-01',
			src_ip: '198.51.100.9',
		},
		{
			id: '3',
			timestamp: new Date(Date.now() - 2 * 3_600_000).toISOString(),
			severity: 'WARN',
			rule_id: '5715',
			rule_description: 'PAM: Login session opened for user admin',
			rule_level: 5,
			agent_name: 'homelab-01',
			src_ip: '127.0.0.1',
		},
		{
			id: '4',
			timestamp: new Date(Date.now() - 3 * 3_600_000).toISOString(),
			severity: 'INFO',
			rule_id: '31101',
			rule_description: 'Web server 200 OK — /api/health',
			rule_level: 2,
			agent_name: 'nginx',
			src_ip: '127.0.0.1',
		},
	];

	// ── State ─────────────────────────────────────────────────────
	let data: SecurityAlert[] | null = null;
	let loading = true;
	let mocked = false;
	let skeletonMinShown = false;

	async function load() {
		const res = await securityApi.alerts();
		if (res) { data = res.alerts; mocked = !res.live; }
		else      { data = MOCK; mocked = true; }
		loading = false;
	}

	let timer: ReturnType<typeof setInterval>;
	onMount(() => {
		setTimeout(() => { skeletonMinShown = true; }, 400);
		load();
		timer = setInterval(load, 30_000);
	});
	onDestroy(() => clearInterval(timer));

	// ── Severity helpers ──────────────────────────────────────────
	type Sev = SecurityAlert['severity'];

	const SEV_COLOR: Record<Sev, string> = {
		CRIT: 'var(--red)',
		HIGH: 'var(--red)',
		WARN: 'var(--yellow)',
		INFO: 'var(--accent2)',
	};

	const SEV_LABEL: Record<Sev, string> = {
		CRIT: 'CRIT',
		HIGH: 'HIGH',
		WARN: 'WARN',
		INFO: 'INFO',
	};

	function relTime(iso: string): string {
		const diff = Date.now() - new Date(iso).getTime();
		const m = Math.floor(diff / 60_000);
		if (m < 60)  return `${m}m ago`;
		const h = Math.floor(m / 60);
		if (h < 24)  return `${h}h ago`;
		return `${Math.floor(h / 24)}d ago`;
	}
</script>

<Card
	label="security"
	accentColor="var(--red)"
	{loading}
	{mocked}
>
	{#if !skeletonMinShown || loading}
		<WidgetSkeleton variant="list" />
	{:else if data}
		{#if data.length === 0}
			<p class="empty">No recent alerts</p>
		{:else}
			<ul class="alert-list">
				{#each data as alert (alert.id)}
					<li
						class="alert-item"
						style="--sev-color: {SEV_COLOR[alert.severity]}"
					>
						<span class="sev-badge" style="color: {SEV_COLOR[alert.severity]}">
							{SEV_LABEL[alert.severity]}
						</span>
						<span class="alert-desc" title={alert.rule_description}>
							{alert.rule_description}
						</span>
						<span class="alert-meta">
							<span class="alert-agent">{alert.agent_name}</span>
							<span class="alert-time">{relTime(alert.timestamp)}</span>
						</span>
					</li>
				{/each}
			</ul>
		{/if}
	{/if}
</Card>

<style>
	.empty {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text2);
	}

	.alert-list {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 1px;
		max-height: 360px;
		overflow-y: auto;
	}

	.alert-item {
		display: grid;
		grid-template-columns: 3rem 1fr auto;
		align-items: baseline;
		gap: 0.5rem;
		padding: 0.45rem 0.5rem;
		border-left: 3px solid var(--sev-color);
		border-radius: 0 3px 3px 0;
		background: color-mix(in srgb, var(--sev-color) 5%, transparent);
		font-family: var(--font-mono);
	}

	.alert-item + .alert-item {
		margin-top: 3px;
	}

	.sev-badge {
		font-size: 0.65rem;
		font-weight: 700;
		letter-spacing: 0.06em;
	}

	.alert-desc {
		font-size: 0.78rem;
		color: var(--text0);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.alert-meta {
		display: flex;
		flex-direction: column;
		align-items: flex-end;
		gap: 0;
		flex-shrink: 0;
	}

	.alert-agent {
		font-size: 0.65rem;
		color: var(--text2);
	}

	.alert-time {
		font-size: 0.65rem;
		color: var(--text2);
	}
</style>
