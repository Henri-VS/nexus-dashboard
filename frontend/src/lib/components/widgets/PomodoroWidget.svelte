<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { nexusSettings } from '$lib/stores';

	type Mode  = 'short' | 'long';
	type Phase = 'work'  | 'break';

	const CONFIGS: Record<Mode, { work: number; rest: number }> = {
		short: { work: 25 * 60, rest:  5 * 60 },
		long:  { work: 50 * 60, rest: 10 * 60 },
	};

	let mode:     Mode  = 'short';
	let phase:    Phase = 'work';
	let timeLeft        = CONFIGS.short.work;
	let running         = false;
	let sessions        = 0;
	let interval: ReturnType<typeof setInterval> | null = null;

	$: cfg         = CONFIGS[mode];
	$: totalTime   = phase === 'work' ? cfg.work : cfg.rest;
	$: progress    = timeLeft / totalTime;
	$: circumf     = 2 * Math.PI * 20; // r=20 → 125.664
	$: dashOffset  = circumf * progress; // remaining arc
	$: displayTime = `${String(Math.floor(timeLeft / 60)).padStart(2, '0')}:${String(timeLeft % 60).padStart(2, '0')}`;

	function tick() {
		if (timeLeft > 0) {
			timeLeft--;
		} else if (phase === 'work') {
			sessions++;
			logSession();
			sendNtfy(`🍅 Work session complete — take a ${mode === 'short' ? '5' : '10'} min break!`);
			phase    = 'break';
			timeLeft = cfg.rest;
		} else {
			sendNtfy('⏰ Break over — back to work!');
			phase    = 'work';
			timeLeft = cfg.work;
		}
	}

	function toggle() {
		if (running) {
			if (interval) { clearInterval(interval); interval = null; }
			running = false;
		} else {
			interval = setInterval(tick, 1000);
			running  = true;
		}
	}

	function reset() {
		if (interval) { clearInterval(interval); interval = null; }
		running  = false;
		phase    = 'work';
		timeLeft = cfg.work;
	}

	function setMode(m: Mode) {
		if (running) { if (interval) { clearInterval(interval); interval = null; } running = false; }
		mode     = m;
		phase    = 'work';
		timeLeft = CONFIGS[m].work;
	}

	async function sendNtfy(msg: string) {
		const { ntfy } = $nexusSettings;
		if (!ntfy.topic) return;
		try { await fetch(`${ntfy.server}/${ntfy.topic}`, { method: 'POST', body: msg }); }
		catch { /* ignore */ }
	}

	function logSession() {
		try {
			const key  = 'nexus_study_sessions';
			const list = JSON.parse(localStorage.getItem(key) ?? '[]');
			list.push({ subject: 'Pomodoro', minutes: mode === 'short' ? 25 : 50, date: Date.now() });
			localStorage.setItem(key, JSON.stringify(list));
		} catch { /* ignore */ }
	}

	function loadTodaySessions(): number {
		try {
			const list = JSON.parse(localStorage.getItem('nexus_study_sessions') ?? '[]');
			const today = new Date().toDateString();
			return list.filter((s: { date: number }) => new Date(s.date).toDateString() === today).length;
		} catch { return 0; }
	}

	onMount(() => { sessions = loadTodaySessions(); });
	onDestroy(() => { if (interval) clearInterval(interval); });
</script>

<div class="card pomo-card">
	<!-- Header -->
	<div class="pomo-head">
		<span class="pomo-title">pomodoro</span>
		<div class="mode-tabs">
			<button class="mode-tab" class:active={mode === 'short'} on:click={() => setMode('short')}>25/5</button>
			<button class="mode-tab" class:active={mode === 'long'}  on:click={() => setMode('long')}>50/10</button>
		</div>
		<span class="sessions-count">{sessions} today</span>
	</div>

	<!-- Ring + time -->
	<div class="ring-row">
		<svg class="ring" viewBox="0 0 48 48" aria-hidden="true">
			<!-- Track -->
			<circle class="ring-track" cx="24" cy="24" r="20" />
			<!-- Progress (remaining) -->
			<circle
				class="ring-fill"
				class:ring-break={phase === 'break'}
				cx="24" cy="24" r="20"
				stroke-dasharray={circumf}
				stroke-dashoffset={dashOffset}
			/>
		</svg>

		<div class="time-col">
			<span class="time-display">{displayTime}</span>
			<span class="phase-label" class:phase-break={phase === 'break'}>
				{phase === 'work' ? 'WORK' : 'BREAK'}
			</span>
		</div>
	</div>

	<!-- Controls -->
	<div class="controls">
		<button class="ctrl-btn ctrl-main" class:running on:click={toggle}>
			{running ? '⏸' : '▶'}
		</button>
		<button class="ctrl-btn ctrl-reset" on:click={reset} title="Reset">↺</button>
	</div>
</div>

<style>
	.pomo-card {
		display: flex;
		flex-direction: column;
		gap: 0.65rem;
		padding: 0.85rem 1rem;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
	}

	/* ── Header ─────────────────────────────────────────────────── */
	.pomo-head {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.pomo-title {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text2);
		flex: 1;
	}

	.mode-tabs {
		display: flex;
		gap: 2px;
	}

	.mode-tab {
		padding: 0.12rem 0.45rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 3px;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.62rem;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s, background 0.1s;
	}

	.mode-tab.active {
		color: var(--accent2);
		border-color: color-mix(in srgb, var(--accent2) 45%, var(--border));
		background: color-mix(in srgb, var(--accent2) 12%, var(--bg2));
	}

	.sessions-count {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--accent);
	}

	/* ── Ring ────────────────────────────────────────────────────── */
	.ring-row {
		display: flex;
		align-items: center;
		gap: 0.85rem;
		justify-content: center;
	}

	.ring {
		width: 72px;
		height: 72px;
		flex-shrink: 0;
		transform: rotate(-90deg); /* start at 12 o'clock */
	}

	.ring-track {
		fill: none;
		stroke: var(--bg2);
		stroke-width: 3.5;
	}

	.ring-fill {
		fill: none;
		stroke: var(--accent2);
		stroke-width: 3.5;
		stroke-linecap: round;
		transition: stroke-dashoffset 0.85s linear, stroke 0.3s;
	}

	.ring-fill.ring-break { stroke: var(--accent); }

	/* ── Time ────────────────────────────────────────────────────── */
	.time-col {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
	}

	.time-display {
		font-family: var(--font-mono);
		font-size: 1.65rem;
		font-weight: 700;
		color: var(--text0);
		line-height: 1;
		letter-spacing: 0.03em;
	}

	.phase-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.14em;
		color: var(--accent2);
		transition: color 0.3s;
	}

	.phase-label.phase-break { color: var(--accent); }

	/* ── Controls ────────────────────────────────────────────────── */
	.controls {
		display: flex;
		gap: 0.4rem;
		justify-content: center;
	}

	.ctrl-btn {
		height: 32px;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-size: 0.9rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: color 0.1s, border-color 0.1s, background 0.1s;
	}

	.ctrl-main {
		flex: 1;
		font-size: 1rem;
		border-color: color-mix(in srgb, var(--accent2) 30%, var(--border));
		color: var(--accent2);
	}

	.ctrl-main.running {
		color: var(--yellow);
		border-color: color-mix(in srgb, var(--yellow) 30%, var(--border));
	}

	.ctrl-main:hover { background: color-mix(in srgb, var(--accent2) 8%, var(--bg2)); }
	.ctrl-main.running:hover { background: color-mix(in srgb, var(--yellow) 8%, var(--bg2)); }

	.ctrl-reset {
		width: 32px;
		font-size: 1.1rem;
		color: var(--text2);
	}
	.ctrl-reset:hover { color: var(--red); border-color: color-mix(in srgb, var(--red) 30%, var(--border)); }
</style>
