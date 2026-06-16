<script lang="ts">
	import WeatherWidget     from '$lib/components/widgets/WeatherWidget.svelte';
	import SystemWidget      from '$lib/components/widgets/SystemWidget.svelte';
	import SecurityWidget    from '$lib/components/widgets/SecurityWidget.svelte';
	import NotesWidget       from '$lib/components/widgets/NotesWidget.svelte';
	import DockerWidget      from '$lib/components/widgets/DockerWidget.svelte';
	import LearningWidget    from '$lib/components/widgets/LearningWidget.svelte';
	import HomeWidget        from '$lib/components/widgets/HomeWidget.svelte';
	import CalendarWidget    from '$lib/components/widgets/CalendarWidget.svelte';
	import PomodoroWidget    from '$lib/components/widgets/PomodoroWidget.svelte';
	import NewsWidget        from '$lib/components/widgets/NewsWidget.svelte';
	import QuickLinksWidget  from '$lib/components/widgets/QuickLinksWidget.svelte';
	import HeartbeatWidget   from '$lib/components/widgets/HeartbeatWidget.svelte';
	import LogsWidget        from '$lib/components/widgets/LogsWidget.svelte';
	import WidgetTray            from '$lib/components/WidgetTray.svelte';
	import WidgetSettingsPopover from '$lib/components/WidgetSettingsPopover.svelte';
	import LayoutPicker          from '$lib/components/LayoutPicker.svelte';

	import type { Component } from 'svelte';
	import { onDestroy, onMount } from 'svelte';
	import { Settings2 } from '@lucide/svelte';
	import { dashConfig, editMode, activeWidgets } from '$lib/stores/dashConfig';
	import { system, docker, security, ai } from '$lib/api';

	// ── Component map ──────────────────────────────────────────────
	const COMPONENTS: Record<string, Component<any>> = {
		weather:    WeatherWidget,
		system:     SystemWidget,
		security:   SecurityWidget,
		docker:     DockerWidget,
		notes:      NotesWidget,
		learning:   LearningWidget,
		home:       HomeWidget,
		calendar:   CalendarWidget,
		pomodoro:   PomodoroWidget,
		news:       NewsWidget,
		quicklinks: QuickLinksWidget,
		heartbeat:  HeartbeatWidget,
		logs:       LogsWidget,
	};

	// ── Status bar data ────────────────────────────────────────────
	let cpuPercent:       number | null = null;
	let systemOnline      = false;
	let containersRunning = 0;
	let containersTotal   = 0;
	let dockerOnline      = false;
	let alertCount        = 0;
	let securityOk        = true;
	let ollamaOnline      = false;
	let currentTime       = '';
	let showLayoutPicker  = false;

	async function refreshStatus() {
		const sys = await system.stats();
		if (sys) { cpuPercent = Math.round(sys.cpu_percent); systemOnline = true; }
		else      { systemOnline = false; }

		const doc = await docker.containers();
		if (doc && !doc.docker_unavailable) {
			containersRunning = doc.containers.filter((c) => c.status === 'running').length;
			containersTotal   = doc.containers.length;
			dockerOnline      = true;
		} else {
			dockerOnline = false;
		}

		const sec = await security.alerts();
		if (sec) { alertCount = sec.alerts.length; securityOk = alertCount === 0; }

		const health = await ai.health();
		ollamaOnline = health?.status === 'online';
	}

	function tickClock() {
		currentTime = new Date().toLocaleTimeString('en-ZA', {
			hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
		});
	}

	let clockTimer: ReturnType<typeof setInterval>;
	let pollTimer:  ReturnType<typeof setInterval>;

	onMount(() => {
		tickClock();
		clockTimer = setInterval(tickClock, 1_000);
		refreshStatus();
		pollTimer = setInterval(refreshStatus, 30_000);
	});

	onDestroy(() => {
		clearInterval(clockTimer);
		clearInterval(pollTimer);
	});

	// ── Settings popover ───────────────────────────────────────────
	let settingsOpenId: string | null = null;
</script>

<svelte:head>
	<title>Nexus</title>
</svelte:head>

<!-- Tray renders in fixed position, no layout impact -->
<WidgetTray />

<!-- ── Status bar ──────────────────────────────────────────────── -->
<div class="status-bar">
	<div class="status-item">
		<span class="status-dot" class:online={systemOnline}></span>
		<span class="status-label">System</span>
		{#if cpuPercent !== null}
			<span class="status-val">{cpuPercent}% CPU</span>
		{/if}
	</div>
	<div class="status-sep"></div>
	<div class="status-item">
		<span class="status-dot" class:online={dockerOnline}></span>
		<span class="status-label">Containers</span>
		<span class="status-val">{containersRunning}/{containersTotal}</span>
	</div>
	<div class="status-sep"></div>
	<div class="status-item">
		<span class="status-dot" class:online={securityOk}></span>
		<span class="status-label">Security</span>
		<span class="status-val">{alertCount > 0 ? alertCount + ' alerts' : 'clear'}</span>
	</div>
	<div class="status-sep"></div>
	<div class="status-item">
		<span class="status-dot" class:online={ollamaOnline}></span>
		<span class="status-label">AI</span>
		<span class="status-val">{ollamaOnline ? 'online' : 'offline'}</span>
	</div>
	<div class="status-spacer"></div>
	<span class="status-time">{currentTime}</span>
</div>

<!-- ── Widget grid ─────────────────────────────────────────────── -->
{#if $activeWidgets.length === 0}
	<div class="grid-empty">
		<p>No widgets enabled. Choose a layout or enable widgets in <a href="/settings">Settings</a>.</p>
		<button on:click={() => (showLayoutPicker = true)}>Choose a layout →</button>
	</div>
{:else}
	<div
		class="grid"
		style="--grid-cols: {$dashConfig.columns}"
	>
		{#each $activeWidgets as widget (widget.id)}
			{@const comp = COMPONENTS[widget.id]}
			{@const span = Math.min(widget.size ?? 1, $dashConfig.columns)}

			<div
				class="widget-slot"
				style="grid-column: span {span}"
			>
				<!-- Gear overlay — visible on hover, or always when editMode is on -->
				<div
					class="gear-wrap"
					class:always-visible={$editMode || settingsOpenId === widget.id}
				>
					<button
						class="gear-btn"
						class:active={settingsOpenId === widget.id}
						title="Widget settings"
						on:click={() => { settingsOpenId = settingsOpenId === widget.id ? null : widget.id; }}
					>
						<Settings2 size={13} strokeWidth={1.5} />
					</button>

					{#if settingsOpenId === widget.id}
						<WidgetSettingsPopover
							widgetId={widget.id}
							onClose={() => { settingsOpenId = null; }}
						/>
					{/if}
				</div>

				{#if comp}
					<svelte:component this={comp} />
				{/if}
			</div>
		{/each}
	</div>
{/if}

<LayoutPicker bind:open={showLayoutPicker} on:close={() => (showLayoutPicker = false)} />

<style>
	/* ── Status bar ───────────────────────────────────────────────── */
	.status-bar {
		display: flex;
		align-items: center;
		height: 32px;
		padding: 0 20px;
		border-bottom: 1px solid var(--border);
		background: var(--bg1);
		font-family: var(--font-mono);
		font-size: 10px;
		flex-shrink: 0;
		margin: -1rem -1.25rem 1rem;
	}

	.status-item {
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 0 16px;
	}

	.status-dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: #484f58;
		flex-shrink: 0;
		transition: background 0.3s;
	}
	.status-dot.online { background: #3fb950; }

	.status-label {
		color: #484f58;
		text-transform: uppercase;
		letter-spacing: 0.05em;
	}

	.status-val { color: #8b949e; }

	.status-sep {
		width: 1px;
		height: 14px;
		background: #30363d;
		flex-shrink: 0;
	}

	.status-spacer { flex: 1; }

	.status-time {
		color: #484f58;
		letter-spacing: 0.04em;
		font-variant-numeric: tabular-nums;
	}

	/* ── Empty grid state ─────────────────────────────────────────── */
	.grid-empty {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 12px;
		padding: 80px 20px;
		text-align: center;
	}

	.grid-empty p {
		font-size: 13px;
		color: #484f58;
		margin: 0;
	}

	.grid-empty a { color: var(--accent); text-decoration: none; }
	.grid-empty a:hover { text-decoration: underline; }

	.grid-empty button {
		padding: 8px 18px;
		background: none;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 12px;
		cursor: pointer;
		transition: border-color 0.12s, color 0.12s;
	}
	.grid-empty button:hover { border-color: var(--accent); color: var(--accent); }

	/* ── Grid — content-driven heights ───────────────────────────── */
	.grid {
		display: grid;
		grid-template-columns: repeat(var(--grid-cols, 3), 1fr);
		gap: 1rem;
		align-items: start;
	}

	/* ── Widget slot ──────────────────────────────────────────────── */
	.widget-slot {
		position: relative;
		min-width: 0;
	}

	/* ── Gear overlay ─────────────────────────────────────────────── */
	.gear-wrap {
		position: absolute;
		top: 8px;
		right: 8px;
		z-index: 10;
		opacity: 0;
		pointer-events: none;
		transition: opacity 0.15s;
	}

	.widget-slot:hover .gear-wrap,
	.gear-wrap.always-visible {
		opacity: 1;
		pointer-events: auto;
	}

	.gear-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text2);
		cursor: pointer;
		padding: 4px;
		transition: color 0.1s, border-color 0.1s, background 0.1s;
	}

	.gear-btn:hover {
		color: var(--text0);
		border-color: var(--accent);
	}

	.gear-btn.active {
		color: var(--accent);
		border-color: var(--accent);
		background: color-mix(in srgb, var(--accent) 12%, var(--bg2));
	}

	/* ── Responsive ───────────────────────────────────────────────── */
	@media (max-width: 700px) {
		.status-bar { display: none; }
		.grid { grid-template-columns: 1fr !important; }
		.widget-slot { grid-column: span 1 !important; }
	}
</style>
