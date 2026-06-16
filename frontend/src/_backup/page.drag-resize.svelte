// BACKUP — drag-and-resize layout system, removed in favour of static grid.
// Re-enable by restoring this file to its original path.
<script lang="ts">
	import WeatherWidget   from '$lib/components/widgets/WeatherWidget.svelte';
	import SystemWidget    from '$lib/components/widgets/SystemWidget.svelte';
	import SecurityWidget  from '$lib/components/widgets/SecurityWidget.svelte';
	import NotesWidget     from '$lib/components/widgets/NotesWidget.svelte';
	import DockerWidget    from '$lib/components/widgets/DockerWidget.svelte';
	import LearningWidget  from '$lib/components/widgets/LearningWidget.svelte';
	import HomeWidget      from '$lib/components/widgets/HomeWidget.svelte';
	import CalendarWidget  from '$lib/components/widgets/CalendarWidget.svelte';
	import PomodoroWidget    from '$lib/components/widgets/PomodoroWidget.svelte';
	import NewsWidget        from '$lib/components/widgets/NewsWidget.svelte';
	import QuickLinksWidget  from '$lib/components/widgets/QuickLinksWidget.svelte';
	import HeartbeatWidget   from '$lib/components/widgets/HeartbeatWidget.svelte';
	import LogsWidget        from '$lib/components/widgets/LogsWidget.svelte';
	import WidgetTray     from '$lib/components/WidgetTray.svelte';
	import WidgetSettingsPopover from '$lib/components/WidgetSettingsPopover.svelte';
	import LayoutPicker from '$lib/components/LayoutPicker.svelte';

	import type { Component } from 'svelte';
	import { onDestroy, onMount } from 'svelte';
	import { GripVertical, Settings } from '@lucide/svelte';
	import { dashConfig, editMode, activeWidgets, WIDGET_DEFS } from '$lib/stores/dashConfig';
	import { system, docker, security, ai } from '$lib/api';
	import { browser } from '$app/environment';

	// ── Component map ──────────────────────────────────────────────
	const COMPONENTS: Record<string, Component<any>> = {
		weather:  WeatherWidget,
		system:   SystemWidget,
		security: SecurityWidget,
		docker:   DockerWidget,
		notes:    NotesWidget,
		learning: LearningWidget,
		home:     HomeWidget,
		calendar: CalendarWidget,
		pomodoro:    PomodoroWidget,
		news:        NewsWidget,
		quicklinks:  QuickLinksWidget,
		heartbeat:   HeartbeatWidget,
		logs:        LogsWidget,
	};

	// ── Status bar data ────────────────────────────────────────────
	let cpuPercent:        number | null = null;
	let systemOnline     = false;
	let containersRunning = 0;
	let containersTotal   = 0;
	let dockerOnline     = false;
	let alertCount       = 0;
	let securityOk       = true;
	let ollamaOnline     = false;
	let currentTime      = '';
	let showLayoutPicker = false;

	async function refreshStatus() {
		// System
		const sys = await system.stats();
		if (sys) {
			cpuPercent  = Math.round(sys.cpu_percent);
			systemOnline = true;
		} else {
			systemOnline = false;
		}

		// Docker
		const doc = await docker.containers();
		if (doc && !doc.docker_unavailable) {
			const running = doc.containers.filter((c) => c.status === 'running');
			containersRunning = running.length;
			containersTotal   = doc.containers.length;
			dockerOnline      = true;
		} else {
			dockerOnline = false;
		}

		// Security
		const sec = await security.alerts();
		if (sec) {
			alertCount  = sec.alerts.length;
			securityOk  = alertCount === 0;
		}

		// AI
		const health = await ai.health();
		ollamaOnline = health?.status === 'online';
	}

	function tickClock() {
		currentTime = new Date().toLocaleTimeString('en-ZA', {
			hour:   '2-digit',
			minute: '2-digit',
			second: '2-digit',
			hour12: false,
		});
	}

	let clockTimer:  ReturnType<typeof setInterval>;
	let pollTimer:   ReturnType<typeof setInterval>;

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

	// ── Drag & drop ────────────────────────────────────────────────
	let draggedId: string | null = null;
	let dropTargetId: string | null = null;
	let gridEl: HTMLElement;

	function startDrag(e: DragEvent, id: string) {
		if (resizingId) return;
		draggedId = id;
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = 'move';
			e.dataTransfer.setData('text/plain', id);
		}
	}

	function onDragOver(e: DragEvent, id: string) {
		e.preventDefault();
		if (e.dataTransfer) e.dataTransfer.dropEffect = 'move';
		dropTargetId = id;
	}

	function onDrop(e: DragEvent, targetId: string) {
		e.preventDefault();
		if (!draggedId || draggedId === targetId) { reset(); return; }
		const all = $dashConfig.widgets;
		const fromIdx = all.findIndex((w) => w.id === draggedId);
		const toIdx   = all.findIndex((w) => w.id === targetId);
		if (fromIdx >= 0 && toIdx >= 0) dashConfig.reorderWidgets(fromIdx, toIdx);
		reset();
	}

	function onDragEnd() { reset(); }

	function reset() { draggedId = null; dropTargetId = null; }

	// ── Widget resize ─────────────────────────────────────────────
	let resizingId:     string | null = null;
	let resizeStartX    = 0;
	let resizeStartY    = 0;
	let resizeStartSpan = 1;
	let resizeStartH    = 340;
	let liveSpan        = 1;
	let liveH           = 340;

	function startWidgetResize(e: MouseEvent | TouchEvent, id: string, span: number, h: number) {
		const clientX = 'touches' in e ? e.touches[0].clientX : (e as MouseEvent).clientX;
		const clientY = 'touches' in e ? e.touches[0].clientY : (e as MouseEvent).clientY;
		resizingId        = id;
		resizeStartX      = clientX;
		resizeStartY      = clientY;
		resizeStartSpan   = span;
		resizeStartH      = h;
		liveSpan          = span;
		liveH             = h;
		e.preventDefault();
		(e as Event).stopPropagation();
	}

	function onWidgetResizeMove(e: MouseEvent | TouchEvent) {
		if (!resizingId) return;
		const clientX = 'touches' in e ? e.touches[0].clientX : (e as MouseEvent).clientX;
		const clientY = 'touches' in e ? e.touches[0].clientY : (e as MouseEvent).clientY;
		const dx      = clientX - resizeStartX;
		const dy      = clientY - resizeStartY;
		const cols    = $dashConfig.columns;
		liveSpan = Math.max(1, Math.min(cols, resizeStartSpan + Math.round(dx / 100)));
		liveH    = Math.max(150, resizeStartH + Math.round(dy / 50) * 50);
	}

	function stopWidgetResize() {
		if (!resizingId) return;
		dashConfig.updateWidget(resizingId, { size: liveSpan as 1 | 2 | 3, height: liveH });
		resizingId = null;
	}

	// ── Settings popover ───────────────────────────────────────────
	let settingsOpenId: string | null = null;
</script>

<svelte:head>
	<title>Nexus</title>
</svelte:head>

<svelte:window
	on:mousemove={onWidgetResizeMove}
	on:mouseup={stopWidgetResize}
	on:touchmove|passive={false}
	on:touchend={stopWidgetResize}
/>

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
		class:edit={$editMode}
		style="--grid-cols: {$dashConfig.columns}"
		bind:this={gridEl}
	>
		{#each $activeWidgets as widget (widget.id)}
			{@const comp         = COMPONENTS[widget.id]}
			{@const cols         = $dashConfig.columns}
			{@const span         = Math.min(resizingId === widget.id ? liveSpan : (widget.size ?? 1), cols)}
			{@const wh           = resizingId === widget.id ? liveH : (widget.height ?? 340)}
			{@const isDragging   = draggedId    === widget.id}
			{@const isDropTarget = dropTargetId === widget.id}
			{@const widgetDef    = WIDGET_DEFS.find((d) => d.id === widget.id)}

			<!-- svelte-ignore a11y-no-static-element-interactions -->
			<div
				class="widget-slot"
				class:dragging={isDragging}
				class:drop-target={isDropTarget && !isDragging}
				class:is-resizing={resizingId === widget.id}
				style="grid-column: span {span}; height: {wh}px; overflow: hidden;"
				draggable={$editMode && !resizingId ? 'true' : 'false'}
				on:dragstart={(e) => $editMode && !resizingId && startDrag(e, widget.id)}
				on:dragover={(e) => $editMode && onDragOver(e, widget.id)}
				on:drop={(e) => $editMode && onDrop(e, widget.id)}
				on:dragend={() => $editMode && onDragEnd()}
			>
				<!-- Edit bar overlay -->
				{#if $editMode}
					<div class="edit-bar">
						<!-- Drag handle -->
						<span class="drag-handle" title="Drag to reorder" aria-hidden="true">
							<GripVertical size={14} strokeWidth={1.5} />
						</span>

						<!-- Preset label during resize -->
						{#if resizingId === widget.id}
							<span class="resize-label">{liveSpan} col · {liveH}px</span>
						{/if}

						<!-- Gear button -->
						<span class="gear-wrap" style="margin-left: auto">
							<button
								class="gear-btn"
								class:active={settingsOpenId === widget.id}
								title="Widget settings"
								on:click={() => { settingsOpenId = settingsOpenId === widget.id ? null : widget.id; }}
							>
								<Settings size={13} strokeWidth={1.5} />
							</button>

							{#if settingsOpenId === widget.id}
								<WidgetSettingsPopover
									widgetId={widget.id}
									onClose={() => { settingsOpenId = null; }}
								/>
							{/if}
						</span>
					</div>

					<!-- Widget name label -->
					<div class="slot-label">{widgetDef?.label ?? widget.id}</div>

					<!-- Resize grip (bottom-right) -->
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<div
						class="resize-grip"
						title="Drag to resize (width snaps to columns, height in 50px steps)"
						role="button"
						tabindex="-1"
						on:mousedown|stopPropagation={(e) => startWidgetResize(e, widget.id, widget.size ?? 1, widget.height ?? 340)}
						on:touchstart|stopPropagation={(e) => startWidgetResize(e, widget.id, widget.size ?? 1, widget.height ?? 340)}
					>⌟</div>
				{/if}

				<!-- The widget itself -->
				<div class="widget-inner" class:edit-padding={$editMode}>
					{#if comp}
						<svelte:component this={comp} />
					{/if}
				</div>
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
		/* Negative margin pulls it edge-to-edge past the page's own padding */
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

	.grid-empty a {
		color: var(--accent);
		text-decoration: none;
	}
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

	/* ── Grid ─────────────────────────────────────────────────── */
	.grid {
		display: grid;
		grid-template-columns: repeat(var(--grid-cols, 3), 1fr);
		gap: 1rem;
		grid-auto-flow: dense;
	}

	/* ── Widget slot ──────────────────────────────────────────── */
	.widget-slot {
		position: relative;
		min-width: 0;
		border-radius: var(--radius);
		transition: opacity 0.15s, box-shadow 0.15s;
	}

	.widget-slot.dragging {
		opacity: 0.4;
	}

	.widget-slot.drop-target {
		box-shadow: 0 0 0 2px var(--accent);
	}

	.widget-inner {
		min-width: 0;
	}

	.widget-inner.edit-padding {
		padding-top: 2rem;
	}

	/* ── Edit bar ─────────────────────────────────────────────── */
	.edit-bar {
		position: absolute;
		top: 0;
		left: 0;
		right: 0;
		height: 2rem;
		display: flex;
		align-items: center;
		padding: 0 0.5rem;
		gap: 0.35rem;
		background: color-mix(in srgb, var(--accent) 8%, var(--bg1));
		border: 1px solid color-mix(in srgb, var(--accent) 25%, var(--border));
		border-radius: var(--radius) var(--radius) 0 0;
		z-index: 10;
	}

	.drag-handle {
		display: flex;
		align-items: center;
		color: var(--text2);
		cursor: grab;
		flex-shrink: 0;
	}

	.drag-handle:active { cursor: grabbing; }

	/* ── Slot label (edit mode) ────────────────────────────────── */
	.slot-label {
		position: absolute;
		top: 4px;
		left: 50%;
		transform: translateX(-50%);
		font-family: var(--font-mono);
		font-size: 9px;
		color: var(--text2);
		pointer-events: none;
		z-index: 5;
		white-space: nowrap;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		/* sit between the edit-bar (z:10) and the bar overlay — use edit-bar top space */
		top: 8px;
	}

	/* ── Resize label ──────────────────────────────────────────── */
	.resize-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--accent);
		flex: 1;
		padding-left: 0.25rem;
	}

	/* ── Resize grip ───────────────────────────────────────────── */
	.resize-grip {
		position: absolute;
		bottom: 2px;
		right: 2px;
		width: 18px;
		height: 18px;
		cursor: se-resize;
		color: var(--text2);
		font-size: 1.05rem;
		line-height: 18px;
		text-align: center;
		z-index: 20;
		opacity: 0;
		transition: opacity 0.15s, color 0.15s;
		user-select: none;
		touch-action: none;
	}

	.widget-slot:hover .resize-grip,
	.resize-grip:hover,
	.widget-slot.is-resizing .resize-grip {
		opacity: 1;
		color: var(--accent);
	}

	/* ── Gear button & popover wrapper ─────────────────────────── */
	.gear-wrap {
		position: relative;
		flex-shrink: 0;
	}

	.gear-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		background: none;
		border: 1px solid transparent;
		border-radius: 4px;
		color: var(--text2);
		cursor: pointer;
		padding: 3px;
		transition: color 0.1s, border-color 0.1s, background 0.1s;
	}

	.gear-btn:hover { color: var(--text0); border-color: var(--border); background: var(--bg2); }

	.gear-btn.active {
		color: var(--accent);
		border-color: var(--accent);
		background: color-mix(in srgb, var(--accent) 12%, var(--bg2));
	}

	/* ── Responsive fallback ────────────────────────────────────── */
	@media (max-width: 700px) {
		.status-bar {
			display: none;
		}

		.grid {
			grid-template-columns: 1fr !important;
		}

		.widget-slot {
			grid-column: span 1 !important;
		}
	}
</style>
