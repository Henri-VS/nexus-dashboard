<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { system as systemApi } from '$lib/api';
	import type { SystemData } from '$lib/types';
	import Card from '$lib/components/Card.svelte';
	import WidgetSkeleton from '$lib/components/WidgetSkeleton.svelte';

	// ── Mock ─────────────────────────────────────────────────────
	const MOCK: SystemData = {
		cpu_percent:  23,
		ram_percent:  61,
		ram_used_gb:  9.8,
		ram_total_gb: 16,
		disk_percent: 54,
		disk_used_gb: 270,
		disk_total_gb: 500,
		temps: { coretemp: 52, nvidia: 38 },
		battery_percent: null,
	};

	// ── State ─────────────────────────────────────────────────────
	let data: SystemData | null = null;
	let loading = true;
	let mocked = false;
	let skeletonMinShown = false;

	async function load() {
		const res = await systemApi.stats();
		if (res) { data = res; mocked = false; }
		else      { data = MOCK; mocked = true; }
		loading = false;
	}

	let timer: ReturnType<typeof setInterval>;
	onMount(() => {
		setTimeout(() => { skeletonMinShown = true; }, 400);
		load();
		timer = setInterval(load, 10_000);
	});
	onDestroy(() => clearInterval(timer));

	// ── Gauge geometry ────────────────────────────────────────────
	// Half-circle arc: rotate(180°) shifts the stroke start to 9-o'clock,
	// progressing counterclockwise through 12-o'clock to 3-o'clock (∩ arch).
	const R     = 38;
	const CIRC  = +(2 * Math.PI * R).toFixed(2);   // ≈ 238.76
	const HALF  = +(CIRC / 2).toFixed(2);           // ≈ 119.38
	const TRACK = `${HALF} ${CIRC}`;

	function gaugeDash(pct: number): string {
		const filled = +((HALF * Math.min(pct, 100) / 100)).toFixed(2);
		return `${filled} ${CIRC}`;
	}

	// ── Helpers ───────────────────────────────────────────────────
	function barColor(pct: number): string {
		if (pct >= 90) return 'var(--red)';
		if (pct >= 70) return 'var(--yellow)';
		return 'var(--accent)';
	}

	function cpuTemp(temps: Record<string, number>): number | null {
		const key = Object.keys(temps).find((k) => /cpu|core|k10|acpi/i.test(k));
		return key ? temps[key] : null;
	}

	function gpuTemp(temps: Record<string, number>): number | null {
		const key = Object.keys(temps).find((k) => /gpu|nvidia|amd|radeon/i.test(k));
		return key ? temps[key] : null;
	}

	$: ct = data
		? ((data as Record<string, unknown>).cpu_temp as number | null | undefined) ?? cpuTemp(data.temps)
		: null;
	$: gt = data
		? ((data as Record<string, unknown>).gpu_temp as number | null | undefined) ?? gpuTemp(data.temps)
		: null;

	$: diskColor = (data?.disk_percent ?? 0) > 70 ? 'var(--yellow)' : 'var(--accent2)';
</script>

<Card
	label="system"
	accentColor="var(--accent)"
	{loading}
	{mocked}
>
	{#if !skeletonMinShown || loading}
		<WidgetSkeleton variant="bars" />
	{:else if data}
		<div class="rows">

			<!-- ── Gauge grid: CPU · RAM · Disk ──────────────────── -->
			<div class="gauges">

				<!-- CPU -->
				<div class="gauge-wrap">
					<svg viewBox="0 0 100 58" class="gauge-svg" aria-hidden="true">
						<circle cx="50" cy="52" r="38"
							fill="none" stroke="var(--bg2)" stroke-width="7"
							stroke-dasharray={TRACK}
							transform="rotate(180 50 52)"
						/>
						<circle cx="50" cy="52" r="38"
							fill="none" stroke="var(--accent)" stroke-width="7"
							stroke-linecap="round"
							stroke-dasharray={gaugeDash(data.cpu_percent)}
							transform="rotate(180 50 52)"
						/>
						<text x="50" y="39"
							text-anchor="middle" dominant-baseline="middle"
							font-family="'JetBrains Mono', monospace"
							font-weight="600" font-size="17"
							fill="var(--text0)"
						>{data.cpu_percent.toFixed(0)}%</text>
						<text x="50" y="51"
							text-anchor="middle" dominant-baseline="middle"
							font-family="'JetBrains Mono', monospace"
							font-size="8" letter-spacing="1"
							fill="var(--text2)"
						>CPU</text>
					</svg>
				</div>

				<!-- RAM -->
				<div class="gauge-wrap">
					<svg viewBox="0 0 100 58" class="gauge-svg" aria-hidden="true">
						<circle cx="50" cy="52" r="38"
							fill="none" stroke="var(--bg2)" stroke-width="7"
							stroke-dasharray={TRACK}
							transform="rotate(180 50 52)"
						/>
						<circle cx="50" cy="52" r="38"
							fill="none" stroke="var(--accent2)" stroke-width="7"
							stroke-linecap="round"
							stroke-dasharray={gaugeDash(data.ram_percent)}
							transform="rotate(180 50 52)"
						/>
						<text x="50" y="39"
							text-anchor="middle" dominant-baseline="middle"
							font-family="'JetBrains Mono', monospace"
							font-weight="600" font-size="17"
							fill="var(--text0)"
						>{data.ram_percent.toFixed(0)}%</text>
						<text x="50" y="51"
							text-anchor="middle" dominant-baseline="middle"
							font-family="'JetBrains Mono', monospace"
							font-size="8" letter-spacing="1"
							fill="var(--text2)"
						>RAM</text>
					</svg>
				</div>

				<!-- Disk -->
				<div class="gauge-wrap">
					<svg viewBox="0 0 100 58" class="gauge-svg" aria-hidden="true">
						<circle cx="50" cy="52" r="38"
							fill="none" stroke="var(--bg2)" stroke-width="7"
							stroke-dasharray={TRACK}
							transform="rotate(180 50 52)"
						/>
						<circle cx="50" cy="52" r="38"
							fill="none" stroke={diskColor} stroke-width="7"
							stroke-linecap="round"
							stroke-dasharray={gaugeDash(data.disk_percent)}
							transform="rotate(180 50 52)"
						/>
						<text x="50" y="39"
							text-anchor="middle" dominant-baseline="middle"
							font-family="'JetBrains Mono', monospace"
							font-weight="600" font-size="17"
							fill="var(--text0)"
						>{data.disk_percent.toFixed(0)}%</text>
						<text x="50" y="51"
							text-anchor="middle" dominant-baseline="middle"
							font-family="'JetBrains Mono', monospace"
							font-size="8" letter-spacing="1"
							fill="var(--text2)"
						>DISK</text>
					</svg>
				</div>

			</div>

			<!-- Battery (only when present) — bar preserved -->
			{#if data.battery_percent !== null}
				<div class="row">
					<div class="row-meta">
						<span class="row-label">BAT</span>
						<span class="row-val">{data.battery_percent.toFixed(0)}<span class="unit">%</span></span>
					</div>
					<div class="bar-track">
						<div
							class="bar-fill"
							style="width:{data.battery_percent}%; background:{barColor(100 - data.battery_percent)}"
						></div>
					</div>
				</div>
			{/if}

			<!-- Temp stat boxes — always shown; N/A when sensor unavailable -->
			<div class="stat-boxes">
				<div class="stat-box" class:hot={ct !== null && ct > 80}>
					<span class="stat-key">CPU temp</span>
					<span class="stat-num" class:na={ct === null}>
						{ct !== null ? `${ct.toFixed(0)}°C` : 'N/A'}
					</span>
				</div>
				<div class="stat-box" class:hot={gt !== null && gt > 85}>
					<span class="stat-key">GPU temp</span>
					<span class="stat-num" class:na={gt === null}>
						{gt !== null ? `${gt.toFixed(0)}°C` : 'N/A'}
					</span>
				</div>
			</div>

		</div>
	{/if}
</Card>


<style>
	.rows { display: flex; flex-direction: column; gap: 0.5rem; }

	/* ── Gauge grid ──────────────────────────────────────────── */
	.gauges {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.25rem;
	}

	.gauge-wrap {
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.gauge-svg {
		width: 100%;
		height: auto;
		overflow: visible;
	}

	/* ── Battery bar (preserved for when sensor present) ─────── */
	.row { display: flex; flex-direction: column; gap: 0.25rem; }

	.row-meta {
		display: flex;
		align-items: baseline;
		gap: 0.4rem;
	}

	.row-label {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		letter-spacing: 0.08em;
		color: var(--text2);
		width: 2.8rem;
		flex-shrink: 0;
	}

	.row-val {
		font-family: var(--font-mono);
		font-size: 0.82rem;
		color: var(--text0);
	}

	.unit {
		font-size: 0.68rem;
		color: var(--text1);
	}

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

	/* ── Stat boxes ──────────────────────────────────────────── */
	.stat-boxes {
		display: flex;
		gap: 0.5rem;
		margin-top: 0.1rem;
	}

	.stat-box {
		flex: 1;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 0.4rem 0.6rem;
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}

	.stat-box.hot { border-color: var(--red); }

	.stat-key {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text2);
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}

	.stat-num {
		font-family: var(--font-mono);
		font-size: 0.9rem;
		color: var(--text0);
	}

	.stat-box.hot .stat-num { color: var(--red); }
	.stat-num.na { color: var(--text2); font-size: 0.78rem; }
</style>
