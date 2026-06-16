<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import { weather as weatherApi } from '$lib/api';
	import type { WeatherData } from '$lib/types';
	import Card from '$lib/components/Card.svelte';
	import WidgetSkeleton from '$lib/components/WidgetSkeleton.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	// ── Mock ─────────────────────────────────────────────────────
	const MOCK: WeatherData = {
		temperature: 22,
		apparent_temperature: 20,
		weathercode: 1,
		windspeed: 15,
		humidity: 62,
		location: '',
		forecast: [
			{ day: 'Tue', code: 1,  high: 24, low: 16 },
			{ day: 'Wed', code: 3,  high: 19, low: 14 },
			{ day: 'Thu', code: 63, high: 17, low: 13 },
			{ day: 'Fri', code: 2,  high: 21, low: 15 },
		],
	};

	// ── State ─────────────────────────────────────────────────────
	let data: WeatherData | null = null;
	let loading = true;
	let mocked = false;
	let skeletonMinShown = false;

	async function load() {
		const res = await weatherApi.current();
		if (res) {
			data = res;
			mocked = false;
		} else {
			data = MOCK;
			mocked = true;
		}
		loading = false;
	}

	onMount(() => {
		setTimeout(() => { skeletonMinShown = true; }, 400);
		load();
	});

	// ── Weather code helpers ──────────────────────────────────────
	function weatherIcon(code: number): string {
		if (code === 0)          return '☀';
		if (code <= 2)           return '⛅';
		if (code <= 3)           return '☁';
		if (code <= 48)          return '🌫';
		if (code <= 55)          return '🌦';
		if (code <= 65)          return '🌧';
		if (code <= 77)          return '❄';
		if (code <= 82)          return '🌦';
		if (code <= 99)          return '⛈';
		return '?';
	}

	function weatherLabel(code: number): string {
		if (code === 0)  return 'Clear sky';
		if (code <= 2)   return 'Partly cloudy';
		if (code <= 3)   return 'Overcast';
		if (code <= 48)  return 'Foggy';
		if (code <= 55)  return 'Drizzle';
		if (code <= 65)  return 'Rain';
		if (code <= 77)  return 'Snow';
		if (code <= 82)  return 'Showers';
		if (code <= 99)  return 'Thunderstorm';
		return 'Unknown';
	}

	function relTime(ts: string | number): string {
		const d = new Date(typeof ts === 'number' ? ts * 1000 : ts);
		const diff = Date.now() - d.getTime();
		const h = Math.floor(diff / 3_600_000);
		if (h < 1)  return 'just now';
		if (h < 24) return `${h}h ago`;
		return `${Math.floor(h / 24)}d ago`;
	}
</script>

<Card
	label="weather"
	accentColor="var(--accent2)"
	{loading}
	{mocked}
>
	{#if !skeletonMinShown || loading}
		<WidgetSkeleton variant="cards" />
	{:else if !data || !data.location}
		<EmptyState
			variant="not-configured"
			title="Weather not configured"
			body="Set your location in Settings → Integrations."
			primaryAction="Open Settings"
			primaryHref="/settings"
		/>
	{:else}
		<!-- Main temp + condition -->
		<div class="main-row">
			<span class="wx-icon" aria-hidden="true">{weatherIcon(data.weathercode)}</span>
			<div class="main-info">
				<span class="temp">{Math.round(data.temperature)}<span class="unit">°C</span></span>
				<span class="condition">{weatherLabel(data.weathercode)}</span>
			</div>
			<span class="location">{data.location}</span>
		</div>

		<!-- Stats row -->
		<div class="stats-row">
			<div class="stat">
				<span class="stat-label">FEELS</span>
				<span class="stat-val">{Math.round(data.apparent_temperature)}°</span>
			</div>
			<div class="stat">
				<span class="stat-label">HUM</span>
				<span class="stat-val">{data.humidity}%</span>
			</div>
			<div class="stat">
				<span class="stat-label">WIND</span>
				<span class="stat-val">{Math.round(data.windspeed / 1.852)}<span class="unit-sm">kts</span></span>
			</div>
		</div>

		<!-- 4-day forecast strip -->
		{#if data.forecast?.length}
			<div class="divider"></div>
			<div class="forecast-strip">
				{#each data.forecast as day}
					<div class="forecast-day">
						<span class="fc-day">{day.day}</span>
						<span class="fc-icon">{weatherIcon(day.code)}</span>
						<span class="fc-hi">{day.high}°</span>
						<span class="fc-lo">{day.low}°</span>
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</Card>

<style>
	/* ── Main row ───────────────────────────────────────────── */
	.main-row {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-bottom: 0.75rem;
	}

	.wx-icon {
		font-size: 2.2rem;
		line-height: 1;
		flex-shrink: 0;
	}

	.main-info {
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	.temp {
		font-family: var(--font-mono);
		font-size: 1.8rem;
		font-weight: 700;
		color: var(--text0);
		line-height: 1;
	}

	.unit {
		font-size: 1rem;
		font-weight: 400;
		color: var(--text1);
	}

	.condition {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text1);
		margin-top: 0.15rem;
	}

	.location {
		margin-left: auto;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--text2);
		text-align: right;
		align-self: flex-start;
	}

	/* ── Stats row ──────────────────────────────────────────── */
	.stats-row {
		display: flex;
		gap: 1.25rem;
	}

	.stat {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}

	.stat-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		letter-spacing: 0.08em;
		color: var(--text2);
	}

	.stat-val {
		font-family: var(--font-mono);
		font-size: 0.88rem;
		color: var(--text0);
	}

	.unit-sm {
		font-size: 0.68rem;
		color: var(--text1);
	}

	/* ── Divider ────────────────────────────────────────────── */
	.divider {
		height: 1px;
		background: var(--border);
		margin: 0.75rem 0;
	}

	/* ── Forecast strip ─────────────────────────────────────── */
	.forecast-strip {
		display: flex;
		gap: 0;
		justify-content: space-between;
	}

	.forecast-day {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.2rem;
		flex: 1;
	}

	.fc-day {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text2);
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.fc-icon {
		font-size: 1.1rem;
		line-height: 1;
	}

	.fc-hi {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text0);
	}

	.fc-lo {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text2);
	}
</style>
