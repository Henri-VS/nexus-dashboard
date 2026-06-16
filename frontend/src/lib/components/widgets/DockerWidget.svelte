<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { docker as dockerApi } from '$lib/api';
	import type { ContainerStatus } from '$lib/types';
	import Card from '$lib/components/Card.svelte';
	import WidgetSkeleton from '$lib/components/WidgetSkeleton.svelte';

	// ── Mock ─────────────────────────────────────────────────────
	const MOCK: ContainerStatus[] = [
		{ id: 'a1b2c3', name: 'dashboard-backend',  image: 'dashboard/backend:latest',                          status: 'running',    health: 'healthy'   },
		{ id: 'd4e5f6', name: 'dashboard-frontend', image: 'dashboard/frontend:latest',                         status: 'running',    health: 'healthy'   },
		{ id: 'g7h8i9', name: 'ollama',             image: 'ollama/ollama:latest',                              status: 'running',    health: 'none'      },
		{ id: 'j0k1l2', name: 'wazuh-manager',      image: 'wazuh/wazuh-manager:4.7',                          status: 'running',    health: 'healthy'   },
		{ id: 'm3n4o5', name: 'mosquitto',          image: 'eclipse-mosquitto:2',                               status: 'running',    health: 'none'      },
		{ id: 'p6q7r8', name: 'crafty',             image: 'registry.gitlab.com/crafty-controller/crafty-4',   status: 'exited',     health: 'none'      },
	];

	// ── State ─────────────────────────────────────────────────────
	let data: ContainerStatus[] | null = null;
	let loading = true;
	let mocked = false;
	let dockerUnavailable = false;
	let skeletonMinShown = false;

	async function load() {
		const res = await dockerApi.containers();
		if (res) {
			dockerUnavailable = res.docker_unavailable;
			data   = res.containers;
			mocked = false;
		} else {
			// Network/backend error — fall back to mock
			data              = MOCK;
			mocked            = true;
			dockerUnavailable = false;
		}
		loading = false;
	}

	let timer: ReturnType<typeof setInterval>;
	onMount(() => {
		setTimeout(() => { skeletonMinShown = true; }, 400);
		load();
		timer = setInterval(load, 15_000);
	});
	onDestroy(() => clearInterval(timer));

	// ── Status helpers ────────────────────────────────────────────
	type Status = ContainerStatus['status'];

	const STATUS_COLOR: Record<Status, string> = {
		running:    'var(--green)',
		restarting: 'var(--yellow)',
		paused:     'var(--text2)',
		exited:     'var(--red)',
	};

	$: running   = data?.filter((c) => c.status === 'running').length ?? 0;
	$: total     = data?.length ?? 0;
</script>

<Card
	label="docker"
	accentColor="var(--teal)"
	{loading}
	{mocked}
>
	{#if !skeletonMinShown || loading}
		<WidgetSkeleton variant="list" />
	{:else if dockerUnavailable}
		<div class="unavailable">
			<span class="unavail-icon" aria-hidden="true">⚠</span>
			<span class="unavail-text">Docker socket unavailable</span>
		</div>
	{:else if data}
		<!-- summary + container list -->
		<div class="summary">
			<span class="summary-num" style="color: var(--green)">{running}</span>
			<span class="summary-sep">/</span>
			<span class="summary-num">{total}</span>
			<span class="summary-label">containers running</span>
		</div>

		<!-- Container list -->
		<ul class="container-list">
			{#each data as container (container.id)}
				<li class="container-row">
					<!-- Status dot -->
					<span
						class="status-dot"
						style="background: {STATUS_COLOR[container.status]}"
						title={container.status}
					></span>

					<!-- Name -->
					<span class="container-name" title={container.image}>
						{container.name}
					</span>

					<!-- Status / uptime -->
					<span
						class="status-badge"
						style="color: {STATUS_COLOR[container.status]}; border-color: color-mix(in srgb, {STATUS_COLOR[container.status]} 30%, var(--border))"
						title={container.restart_count ? `${container.restart_count} restart${container.restart_count !== 1 ? 's' : ''}` : undefined}
					>
						{container.uptime && container.status === 'running' ? container.uptime : container.status}
					</span>

					<!-- Health indicator (only when meaningful) -->
					{#if container.health !== 'none' && container.health !== 'starting'}
						<span
							class="health-dot"
							style="background: {container.health === 'healthy' ? 'var(--green)' : 'var(--red)'}"
							title="health: {container.health}"
						></span>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</Card>

<style>
	/* ── Unavailable banner ─────────────────────────────────── */
	.unavailable {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.6rem 0.5rem;
		background: color-mix(in srgb, var(--yellow) 8%, var(--bg2));
		border: 1px solid color-mix(in srgb, var(--yellow) 25%, var(--border));
		border-left: 3px solid var(--yellow);
		border-radius: var(--radius);
	}

	.unavail-icon {
		color: var(--yellow);
		font-size: 0.9rem;
		flex-shrink: 0;
	}

	.unavail-text {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text1);
	}

	/* ── Summary ────────────────────────────────────────────── */
	.summary {
		display: flex;
		align-items: baseline;
		gap: 0.2rem;
		margin-bottom: 0.65rem;
		font-family: var(--font-mono);
	}

	.summary-num {
		font-size: 1rem;
		font-weight: 700;
		color: var(--text0);
	}

	.summary-sep {
		font-size: 0.85rem;
		color: var(--text2);
	}

	.summary-label {
		font-size: 0.72rem;
		color: var(--text2);
		margin-left: 0.3rem;
	}

	/* ── Container list ─────────────────────────────────────── */
	.container-list {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 2px;
		max-height: 300px;
		overflow-y: auto;
	}

	.container-row {
		display: grid;
		grid-template-columns: 8px 1fr auto auto;
		align-items: center;
		gap: 0.5rem;
		padding: 0.3rem 0.4rem;
		border-radius: 3px;
		transition: background 0.1s;
	}

	.container-row:hover {
		background: var(--bg2);
	}

	.status-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.container-name {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text0);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.status-badge {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		border: 1px solid;
		border-radius: 3px;
		padding: 0.05rem 0.3rem;
		flex-shrink: 0;
	}

	.health-dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		flex-shrink: 0;
	}
</style>
