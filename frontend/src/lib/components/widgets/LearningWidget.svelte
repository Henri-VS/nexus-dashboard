<script lang="ts">
	import { onMount } from 'svelte';
	import { learn as learnApi } from '$lib/api';
	import type { LearningData } from '$lib/types';
	import Card from '$lib/components/Card.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import WidgetSkeleton from '$lib/components/WidgetSkeleton.svelte';

	// ── Mock — shown only when the API itself is unreachable ─────
	const MOCK: LearningData = {
		thm_rank:            'Hacker',
		thm_points:          12_450,
		thm_completed_rooms: 44,
		badge_name:          '',
		streak:              0,
		certs: [
			{
				name:           'CompTIA Security+',
				exam_date:      '2026-08-15',
				days_remaining: 69,
				status:         'scheduled',
			},
			{
				name:           'eJPT',
				exam_date:      null,
				days_remaining: null,
				status:         'studying',
			},
		],
	};

	// ── State ─────────────────────────────────────────────────────
	let data: LearningData | null = null;
	let loading = true;
	let mocked = false;
	let skeletonMinShown = false;

	async function load() {
		const res = await learnApi.progress();
		if (res) {
			data   = res;
			mocked = false;
		} else {
			data   = MOCK;
			mocked = true;
		}
		loading = false;
	}

	onMount(() => {
		setTimeout(() => { skeletonMinShown = true; }, 400);
		load();
	});

	// ── Helpers ───────────────────────────────────────────────────
	function certBarPct(cert: LearningData['certs'][number]): number {
		if (cert.status === 'passed') return 100;
		if (!cert.days_remaining)     return 15;   // studying, no date
		// Assume ~180-day study window as 100%
		return Math.min(95, Math.round(((180 - cert.days_remaining) / 180) * 100));
	}

	function certBarColor(cert: LearningData['certs'][number]): string {
		if (cert.status === 'passed')                          return 'var(--green)';
		if (cert.days_remaining !== null && cert.days_remaining < 30) return 'var(--red)';
		if (cert.days_remaining !== null && cert.days_remaining < 60) return 'var(--yellow)';
		return 'var(--accent3)';
	}

	function certLabel(cert: LearningData['certs'][number]): string {
		if (cert.status === 'passed')    return 'passed';
		if (cert.days_remaining !== null) return `${cert.days_remaining}d`;
		return 'studying';
	}
</script>

<Card
	label="learning"
	accentColor="var(--yellow)"
	{loading}
	{mocked}
>
	{#if !skeletonMinShown || loading}
		<WidgetSkeleton variant="bars" />
	{:else if mocked}
		<EmptyState
			variant="unreachable"
			size="compact"
			title="THM unavailable"
			body="Set THM_USERNAME in .env"
		/>
	{:else if data}
		<!-- THM stats -->
		<div class="thm-section">
			<div class="thm-header">
				<span class="section-label">TryHackMe</span>
				<div class="thm-rank-group">
					{#if data.badge_name}
						<span class="badge-pill">{data.badge_name}</span>
					{/if}
					<span class="thm-rank">{data.thm_rank}</span>
				</div>
			</div>
			<div class="thm-stats">
				<div class="mini-stat">
					<span class="mini-val">{data.thm_points.toLocaleString()}</span>
					<span class="mini-key">points</span>
				</div>
				<div class="mini-stat">
					<span class="mini-val">{data.thm_completed_rooms}</span>
					<span class="mini-key">rooms</span>
				</div>
				{#if data.streak}
					<div class="mini-stat">
						<span class="mini-val streak-val">{data.streak}</span>
						<span class="mini-key">day streak</span>
					</div>
				{/if}
			</div>
		</div>

		<!-- Divider -->
		<div class="divider"></div>

		<!-- Cert trackers -->
		<div class="certs-section">
			<span class="section-label">Certifications</span>
			<div class="cert-list">
				{#each data.certs as cert}
					<div class="cert-row">
						<div class="cert-meta">
							<span class="cert-name">{cert.name}</span>
							<span
								class="cert-status"
								style="color: {certBarColor(cert)}"
							>{certLabel(cert)}</span>
						</div>
						<div class="bar-track">
							<div
								class="bar-fill"
								style="width: {certBarPct(cert)}%; background: {certBarColor(cert)}"
							></div>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
</Card>

<style>
	/* ── THM section ────────────────────────────────────────── */
	.thm-section { margin-bottom: 0.1rem; }

	.thm-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.5rem;
	}

	.thm-rank-group {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.thm-rank {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--yellow);
		font-weight: 700;
	}

	.badge-pill {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--accent4);
		border: 1px solid color-mix(in srgb, var(--accent4) 35%, var(--border));
		border-radius: 999px;
		padding: 0.05rem 0.4rem;
		letter-spacing: 0.04em;
	}

	.streak-val {
		color: var(--accent4);
	}

	.thm-stats {
		display: flex;
		gap: 1.5rem;
	}

	.mini-stat {
		display: flex;
		flex-direction: column;
		gap: 0.05rem;
	}

	.mini-val {
		font-family: var(--font-mono);
		font-size: 1rem;
		font-weight: 700;
		color: var(--text0);
	}

	.mini-key {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}

	/* ── Divider ────────────────────────────────────────────── */
	.divider {
		height: 1px;
		background: var(--border);
		margin: 0.75rem 0;
	}

	/* ── Shared label ───────────────────────────────────────── */
	.section-label {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text2);
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}

	/* ── Cert list ──────────────────────────────────────────── */
	.certs-section {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.cert-list {
		display: flex;
		flex-direction: column;
		gap: 0.55rem;
		margin-top: 0.25rem;
	}

	.cert-row {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}

	.cert-meta {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.cert-name {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text0);
	}

	.cert-status {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		font-weight: 700;
		flex-shrink: 0;
	}

	/* ── Progress bar ───────────────────────────────────────── */
	.bar-track {
		height: 4px;
		background: var(--bg2);
		border-radius: 2px;
		overflow: hidden;
	}

	.bar-fill {
		height: 100%;
		border-radius: 2px;
		transition: width 0.4s ease;
	}
</style>
