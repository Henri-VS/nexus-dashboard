<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8088';

	interface LogEntry {
		id:      number;
		ts:      string;
		level:   string;
		source:  string;
		message: string;
	}

	let entries: LogEntry[] = [];
	let loading = true;
	let timer: ReturnType<typeof setInterval> | null = null;

	async function load() {
		try {
			const r = await fetch(`${BASE}/api/logs/history?limit=50`);
			if (r.ok) {
				const data = await r.json();
				entries = (data.entries ?? []).filter((e: LogEntry) =>
					['WARN', 'WARNING', 'ERROR', 'CRITICAL'].includes(e.level.toUpperCase())
				).slice(-5);
			}
		} catch { /* offline */ }
		loading = false;
	}

	function levelColor(lvl: string): string {
		const u = lvl.toUpperCase();
		if (u === 'ERROR' || u === 'CRITICAL') return 'var(--red)';
		return 'var(--yellow)';
	}

	function fmtTs(iso: string): string {
		try {
			return new Date(iso).toLocaleTimeString('en-GB', {
				hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit',
			});
		} catch { return iso; }
	}

	function truncate(s: string, n = 75): string {
		return s.length > n ? s.slice(0, n) + '…' : s;
	}

	onMount(() => {
		load();
		timer = setInterval(load, 30_000);
	});

	onDestroy(() => { if (timer) clearInterval(timer); });
</script>

<div class="widget">
	<div class="accent-bar"></div>
	<div class="body">

		<div class="header">
			<span class="title">logs</span>
			<a href="/logs" class="view-all">view all →</a>
		</div>

		{#if loading && entries.length === 0}
			<div class="skeleton">
				{#each Array(3) as _}<div class="skel-row"></div>{/each}
			</div>
		{:else if entries.length === 0}
			<div class="empty">no warnings or errors</div>
		{:else}
			<div class="log-list">
				{#each entries as e (e.id)}
					<div class="log-row">
						<span class="dot" style="background:{levelColor(e.level)}" title={e.level}></span>
						<span class="ts">{fmtTs(e.ts)}</span>
						<span class="src">{e.source}</span>
						<span class="msg">{truncate(e.message)}</span>
					</div>
				{/each}
			</div>
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
		background: var(--red);
		flex-shrink: 0;
	}

	.body {
		flex: 1;
		padding: 0.7rem 0.85rem;
		min-width: 0;
	}

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

	.view-all {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--red);
		text-decoration: none;
	}
	.view-all:hover { text-decoration: underline; }

	.log-list {
		display: flex;
		flex-direction: column;
		min-height: 280px;
		max-height: 420px;
		overflow-y: auto;
	}

	.log-row {
		display: grid;
		grid-template-columns: 8px 60px 80px 1fr;
		align-items: center;
		gap: 0.4rem;
		padding: 0.22rem 0;
		border-bottom: 1px solid var(--border);
		font-family: var(--font-mono);
		font-size: 0.68rem;
	}
	.log-row:last-child { border-bottom: none; }

	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.ts  { color: var(--text2); font-size: 0.62rem; }
	.src { color: var(--accent3); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
	.msg { color: var(--text1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

	.empty {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--green);
		padding: 0.5rem 0;
	}

	.skeleton { display: flex; flex-direction: column; gap: 0.35rem; }
	.skel-row {
		height: 14px;
		background: var(--bg2);
		border-radius: 3px;
		animation: pulse 1.4s ease-in-out infinite;
	}

	@keyframes pulse {
		0%, 100% { opacity: 1; }
		50%       { opacity: 0.4; }
	}
</style>
