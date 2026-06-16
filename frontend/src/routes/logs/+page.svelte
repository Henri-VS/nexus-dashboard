<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { ScrollText, X, Download, Trash2, ChevronDown, ChevronUp } from '@lucide/svelte';

	const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8088';

	interface LogEntry {
		id:          number;
		ts:          string;
		level:       string;
		source:      string;
		message:     string;
		logger_name: string;
	}

	// ── State ────────────────────────────────────────────────────
	let entries: LogEntry[] = [];
	let live         = false;
	let filterSource = '';
	let filterLevel  = '';
	let search       = '';
	let autoScroll   = true;
	let es: EventSource | null = null;
	let listEl: HTMLElement;
	let selectedEntry: LogEntry | null = null;
	let clientH = 0;

	// ── Virtual list constants ─────────────────────────────────────
	const ROW_H = 22;
	let scrollTop = 0;

	// ── Derived ──────────────────────────────────────────────────
	$: filtered = entries.filter((e) => {
		if (filterSource && !e.source.includes(filterSource)) return false;
		if (filterLevel) {
			const u = e.level.toUpperCase();
			const fl = filterLevel.toUpperCase();
			if (fl === 'WARN') {
				if (u !== 'WARN' && u !== 'WARNING') return false;
			} else if (u !== fl) return false;
		}
		if (search) {
			const lc = search.toLowerCase();
			if (!e.message.toLowerCase().includes(lc) && !e.source.toLowerCase().includes(lc)) return false;
		}
		return true;
	});

	$: totalH   = filtered.length * ROW_H;
	$: startIdx = Math.max(0, Math.floor(scrollTop / ROW_H) - 5);
	$: endIdx   = Math.min(filtered.length, Math.ceil((scrollTop + clientH) / ROW_H) + 5);
	$: visible  = filtered.slice(startIdx, endIdx);
	$: sources  = [...new Set(entries.map((e) => e.source))].sort();

	// ── SSE ──────────────────────────────────────────────────────
	function connectSSE() {
		if (es) { es.close(); es = null; }
		es = new EventSource(`${BASE}/api/logs/stream`);
		es.addEventListener('log', (ev: MessageEvent) => {
			const entry = JSON.parse(ev.data) as LogEntry;
			if (!entry.id) (entry as any).id = Date.now() + Math.random();
			entries = [...entries.slice(-4999), entry];
			if (autoScroll) scrollToBottom();
		});
		es.onerror = () => { live = false; };
		live = true;
	}

	function disconnectSSE() {
		if (es) { es.close(); es = null; }
		live = false;
	}

	// ── History ──────────────────────────────────────────────────
	async function loadHistory() {
		try {
			const r = await fetch(`${BASE}/api/logs/history?limit=500`);
			if (r.ok) {
				const data = await r.json();
				entries = data.entries ?? [];
			}
		} catch { /* offline */ }
	}

	// ── Scroll ───────────────────────────────────────────────────
	async function scrollToBottom() {
		await tick();
		if (listEl) listEl.scrollTop = listEl.scrollHeight;
	}

	function onScroll() {
		if (!listEl) return;
		scrollTop = listEl.scrollTop;
		autoScroll = (listEl.scrollHeight - listEl.scrollTop - listEl.clientHeight) < 60;
	}

	// ── Export / clear ─────────────────────────────────────────────
	function clearLogs() { entries = []; selectedEntry = null; }

	function exportLogs() {
		const text = filtered
			.map((e) => `[${e.ts}] [${e.level.padEnd(8)}] [${e.source}] ${e.message}`)
			.join('\n');
		const blob = new Blob([text], { type: 'text/plain' });
		const url  = URL.createObjectURL(blob);
		const a    = document.createElement('a');
		a.href = url;
		a.download = `nexus-logs-${new Date().toISOString().slice(0, 10)}.txt`;
		a.click();
		URL.revokeObjectURL(url);
	}

	// ── Highlight ─────────────────────────────────────────────────
	function escHtml(s: string): string {
		return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
	}

	function highlight(text: string, term: string): string {
		if (!term) return escHtml(text);
		const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
		return escHtml(text).replace(new RegExp(`(${escaped})`, 'gi'), '<mark>$1</mark>');
	}

	// ── Helpers ───────────────────────────────────────────────────
	function levelColor(lvl: string): string {
		switch (lvl.toUpperCase()) {
			case 'ERROR':
			case 'CRITICAL': return 'var(--red)';
			case 'WARN':
			case 'WARNING':  return 'var(--yellow)';
			case 'INFO':     return 'var(--green)';
			default:         return 'var(--text2)';
		}
	}

	function fmtTs(iso: string): string {
		try {
			return new Date(iso).toLocaleTimeString('en-GB', {
				hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit',
			});
		} catch { return iso; }
	}

	onMount(async () => {
		await loadHistory();
		connectSSE();
		clientH = listEl?.clientHeight ?? 0;
		window.addEventListener('resize', () => { clientH = listEl?.clientHeight ?? 0; });
		await scrollToBottom();
	});

	onDestroy(() => { disconnectSSE(); });
</script>

<svelte:head>
	<title>Nexus — Logs</title>
</svelte:head>

<div class="logs-page">

	<!-- ── Toolbar ───────────────────────────────────────────── -->
	<div class="toolbar">
		<div class="tl-left">
			<ScrollText size={14} strokeWidth={1.5} />
			<span class="page-title">logs</span>
			<span class="live-dot" class:live title={live ? 'streaming' : 'disconnected'}></span>
			<span class="entry-count">{filtered.length.toLocaleString()} entries</span>
		</div>

		<div class="tl-filters">
			<select class="filter-sel" bind:value={filterSource}>
				<option value="">all sources</option>
				{#each sources as src}
					<option value={src}>{src}</option>
				{/each}
			</select>

			<select class="filter-sel" bind:value={filterLevel}>
				<option value="">all levels</option>
				{#each ['DEBUG','INFO','WARN','ERROR','CRITICAL'] as lvl}
					<option value={lvl}>{lvl}</option>
				{/each}
			</select>

			<div class="search-wrap">
				<input class="search-inp" type="text" placeholder="search…" bind:value={search} />
				{#if search}
					<button class="clear-search" on:click={() => (search = '')} title="Clear">
						<X size={10} />
					</button>
				{/if}
			</div>
		</div>

		<div class="tl-actions">
			<button
				class="tb-btn"
				class:active={autoScroll}
				title={autoScroll ? 'Auto-scroll on' : 'Auto-scroll off'}
				on:click={() => { autoScroll = !autoScroll; if (autoScroll) scrollToBottom(); }}
			>
				{#if autoScroll}<ChevronDown size={13} />{:else}<ChevronUp size={13} />{/if}
			</button>
			<button class="tb-btn" on:click={exportLogs} title="Export logs">
				<Download size={13} />
			</button>
			<button class="tb-btn tb-warn" on:click={clearLogs} title="Clear display">
				<Trash2 size={13} />
			</button>
			{#if live}
				<button class="tb-btn" on:click={disconnectSSE}>pause</button>
			{:else}
				<button class="tb-btn active" on:click={connectSSE}>resume</button>
			{/if}
		</div>
	</div>

	<!-- ── Virtual log list ────────────────────────────────────── -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div
		class="log-list"
		role="log"
		bind:this={listEl}
		bind:clientHeight={clientH}
		on:scroll={onScroll}
	>
		<div style="height:{totalH}px;position:relative;">
			<div style="position:absolute;top:{startIdx * ROW_H}px;left:0;right:0;">
				{#each visible as entry, i (entry.id ?? startIdx + i)}
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<div
						class="log-row"
						class:selected={selectedEntry?.id === entry.id}
						class:row-error={entry.level.toUpperCase() === 'ERROR' || entry.level.toUpperCase() === 'CRITICAL'}
						class:row-warn={entry.level.toUpperCase() === 'WARN' || entry.level.toUpperCase() === 'WARNING'}
						style="height:{ROW_H}px;"
						on:click={() => { selectedEntry = selectedEntry?.id === entry.id ? null : entry; }}
					>
						<span class="col-ts">{fmtTs(entry.ts)}</span>
						<span class="col-lvl" style="color:{levelColor(entry.level)}">{entry.level.slice(0,4)}</span>
						<span class="col-src">{entry.source}</span>
						<span class="col-msg">{@html highlight(entry.message, search)}</span>
					</div>
				{/each}
			</div>
		</div>
	</div>

	<!-- ── Detail panel ─────────────────────────────────────────── -->
	{#if selectedEntry}
		<div class="detail-panel">
			<div class="detail-hdr">
				<span class="detail-label">detail</span>
				<button class="close-btn" on:click={() => (selectedEntry = null)}>
					<X size={12} />
				</button>
			</div>
			<div class="detail-row"><span class="dk">time</span><span class="dv">{selectedEntry.ts}</span></div>
			<div class="detail-row">
				<span class="dk">level</span>
				<span class="dv" style="color:{levelColor(selectedEntry.level)}">{selectedEntry.level}</span>
			</div>
			<div class="detail-row"><span class="dk">source</span><span class="dv">{selectedEntry.source}</span></div>
			{#if selectedEntry.logger_name}
				<div class="detail-row"><span class="dk">logger</span><span class="dv">{selectedEntry.logger_name}</span></div>
			{/if}
			<pre class="detail-msg">{selectedEntry.message}</pre>
		</div>
	{/if}

</div>

<style>
	/* Full-bleed: negate the layout's 1.5rem padding */
	.logs-page {
		display: flex;
		flex-direction: column;
		height: calc(100vh - 40px); /* subtract topbar height */
		margin: -1.5rem;
		overflow: hidden;
		background: var(--bg0);
	}

	/* ── Toolbar ────────────────────────────────────────────── */
	.toolbar {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.35rem 0.75rem;
		background: var(--bg1);
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
		flex-wrap: wrap;
		min-height: 36px;
	}

	.tl-left {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		color: var(--text2);
	}

	.page-title {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text0);
	}

	.live-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: var(--text2);
		flex-shrink: 0;
		transition: background 0.3s;
	}
	.live-dot.live {
		background: var(--green);
		box-shadow: 0 0 4px var(--green);
	}

	.entry-count {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text2);
	}

	.tl-filters {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		flex: 1;
	}

	.filter-sel {
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		padding: 0.18rem 0.35rem;
		cursor: pointer;
	}
	.filter-sel:focus { outline: none; border-color: var(--accent); }

	.search-wrap {
		position: relative;
		flex: 1;
		max-width: 180px;
	}

	.search-inp {
		width: 100%;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		padding: 0.18rem 1.4rem 0.18rem 0.35rem;
		box-sizing: border-box;
	}
	.search-inp:focus { outline: none; border-color: var(--accent); }

	.clear-search {
		position: absolute;
		right: 4px;
		top: 50%;
		transform: translateY(-50%);
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		display: flex;
		align-items: center;
		padding: 0;
	}
	.clear-search:hover { color: var(--text0); }

	.tl-actions {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.tb-btn {
		display: flex;
		align-items: center;
		gap: 0.2rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.65rem;
		padding: 0.18rem 0.4rem;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}
	.tb-btn:hover { color: var(--text0); border-color: var(--accent); }
	.tb-btn.active { color: var(--accent); border-color: var(--accent); }
	.tb-btn.tb-warn:hover { color: var(--red); border-color: var(--red); }

	/* ── Virtual log list ──────────────────────────────────────── */
	.log-list {
		flex: 1;
		overflow-y: auto;
		overflow-x: hidden;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		min-height: 0;
		scrollbar-width: thin;
		scrollbar-color: var(--border) transparent;
	}

	.log-row {
		display: grid;
		grid-template-columns: 68px 38px 130px 1fr;
		align-items: center;
		gap: 0.6rem;
		padding: 0 0.75rem;
		cursor: pointer;
		white-space: nowrap;
		overflow: hidden;
		box-sizing: border-box;
		border-bottom: 1px solid transparent;
		transition: background 0.08s;
	}
	.log-row:hover    { background: var(--bg2); }
	.log-row.selected { background: color-mix(in srgb, var(--accent) 10%, var(--bg1)); border-bottom-color: color-mix(in srgb, var(--accent) 40%, transparent); }
	.log-row.row-error { background: color-mix(in srgb, var(--red) 4%, transparent); }
	.log-row.row-warn  { background: color-mix(in srgb, var(--yellow) 3%, transparent); }

	.col-ts  { color: var(--text2); font-size: 0.65rem; flex-shrink: 0; }
	.col-lvl { font-weight: 700; font-size: 0.63rem; flex-shrink: 0; }
	.col-src { color: var(--accent3); overflow: hidden; text-overflow: ellipsis; flex-shrink: 0; }
	.col-msg { color: var(--text1); overflow: hidden; text-overflow: ellipsis; }

	:global(.log-row mark) {
		background: color-mix(in srgb, var(--yellow) 40%, transparent);
		color: inherit;
		border-radius: 2px;
		padding: 0 1px;
	}

	/* ── Detail panel ────────────────────────────────────────── */
	.detail-panel {
		flex-shrink: 0;
		background: var(--bg1);
		border-top: 1px solid var(--border);
		padding: 0.5rem 0.75rem;
		max-height: 160px;
		overflow-y: auto;
	}

	.detail-hdr {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.3rem;
	}

	.detail-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text2);
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		display: flex;
		align-items: center;
		padding: 0;
	}
	.close-btn:hover { color: var(--text0); }

	.detail-row {
		display: grid;
		grid-template-columns: 52px 1fr;
		gap: 0.5rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		line-height: 1.6;
	}
	.dk { color: var(--text2); }
	.dv { color: var(--text1); }

	.detail-msg {
		margin: 0.35rem 0 0;
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text0);
		white-space: pre-wrap;
		word-break: break-all;
		padding: 0.4rem 0.6rem;
		background: var(--bg2);
		border-radius: 4px;
		border: 1px solid var(--border);
		max-height: 80px;
		overflow-y: auto;
	}

	/* ── Mobile ─────────────────────────────────────────────── */
	@media (max-width: 768px) {
		.logs-page { margin: -1rem -0.75rem; height: calc(100vh - 40px - 56px); }
		.log-row   { grid-template-columns: 60px 34px 1fr; }
		.col-src   { display: none; }
		.tl-filters { flex-wrap: wrap; }
	}
</style>
