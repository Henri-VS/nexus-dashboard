<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { news as newsApi } from '$lib/api';
	import type { NewsArticle } from '$lib/api';
	import { Rss, RefreshCw, Search, ExternalLink, CircleAlert, Newspaper } from '@lucide/svelte';

	// ── State ─────────────────────────────────────────────────────────────────

	type Category = 'all' | 'cybersecurity' | 'tech' | 'ai' | 'robotics';

	let articles:    NewsArticle[] = [];
	let loading      = true;
	let fetchedAt:   string | null = null;
	let failedFeeds  = 0;
	let activeFilter: Category = 'all';
	let searchQuery  = '';
	let refreshTimer: ReturnType<typeof setInterval> | null = null;
	let loadTimeout:  ReturnType<typeof setTimeout>  | null = null;

	// ── State derivation ──────────────────────────────────────────────────────

	// System mock is the sentinel value the backend returns when all feeds fail.
	$: isSystemMock  = articles.length === 1 && articles[0]?.source === 'System';
	// Has real (non-mock) content cached
	$: hasRealContent = articles.some(a => a.source !== 'System');
	// Full-page loading skeletons: only when there's nothing real to show yet
	$: showSkeletons    = loading && !hasRealContent;
	// Inline refresh bar: when re-fetching but real content is already on screen
	$: showInlineRefresh = loading && hasRealContent;
	// Error / empty gates — only meaningful when not loading
	$: isError  = !loading && isSystemMock;
	$: isEmpty  = !loading && articles.length === 0;
	$: isLoaded = !loading && !isError && articles.length > 0;

	// ── Data ──────────────────────────────────────────────────────────────────

	function _systemArticle(): NewsArticle {
		return {
			title:     'News feeds unavailable',
			link:      '',
			summary:   '',
			source:    'System',
			published: new Date().toISOString(),
			category:  'tech',
		};
	}

	async function load(forceRefresh = false) {
		loading = true;

		// Clear any lingering abort timer from a previous call.
		if (loadTimeout) { clearTimeout(loadTimeout); loadTimeout = null; }

		// Frontend 20-second hard abort.
		loadTimeout = setTimeout(() => {
			loadTimeout = null;
			loading = false;
			if (!hasRealContent) articles = [_systemArticle()];
		}, 20_000);

		const res = await newsApi.feed(forceRefresh);

		// Guard: the timeout may have already fired.
		if (!loadTimeout) return;
		clearTimeout(loadTimeout);
		loadTimeout = null;
		loading = false;

		if (res) {
			articles    = res.articles;
			fetchedAt   = res.fetched_at;
			failedFeeds = res.failed_feeds ?? 0;
		} else {
			// Network-level failure — force error state.
			if (!hasRealContent) articles = [_systemArticle()];
		}
	}

	// ── Source sidebar ────────────────────────────────────────────────────────

	const NEWS_CFG_KEY = 'dashboard_config.news';
	const SRC_MIN      = 150;
	const SRC_MAX      = 350;

	let sourceSidebarW   = 200;
	let disabledSources  = new Set<string>();
	let sidebarResizing  = false;
	let sidebarResStartX = 0;
	let sidebarResStartW = 200;

	$: sources = [...new Set(articles.filter(a => a.source !== 'System').map(a => a.source))].sort();

	function startSidebarResize(e: MouseEvent | TouchEvent) {
		const cx = 'touches' in e ? (e as TouchEvent).touches[0].clientX : (e as MouseEvent).clientX;
		sidebarResizing  = true;
		sidebarResStartX = cx;
		sidebarResStartW = sourceSidebarW;
		e.preventDefault();
	}

	function onSidebarResizeMove(e: MouseEvent | TouchEvent) {
		if (!sidebarResizing) return;
		const cx = 'touches' in e ? (e as TouchEvent).touches[0].clientX : (e as MouseEvent).clientX;
		sourceSidebarW = Math.max(SRC_MIN, Math.min(SRC_MAX, sidebarResStartW + (cx - sidebarResStartX)));
	}

	function stopSidebarResize() {
		if (!sidebarResizing) return;
		sidebarResizing = false;
		try { localStorage.setItem(NEWS_CFG_KEY, JSON.stringify({ sidebarW: sourceSidebarW, disabled: [...disabledSources] })); } catch { /* ignore */ }
	}

	function toggleSource(src: string) {
		const s = new Set(disabledSources);
		if (s.has(src)) s.delete(src); else s.add(src);
		disabledSources = s;
		try { localStorage.setItem(NEWS_CFG_KEY, JSON.stringify({ sidebarW: sourceSidebarW, disabled: [...disabledSources] })); } catch { /* ignore */ }
	}

	// ── Filtering ─────────────────────────────────────────────────────────────

	$: filtered = articles.filter((a) => {
		if (a.source === 'System') return false;  // never surface mock articles
		if (disabledSources.has(a.source)) return false;
		if (activeFilter !== 'all' && a.category?.toLowerCase() !== activeFilter) return false;
		if (searchQuery.trim()) {
			const q = searchQuery.toLowerCase();
			return a.title.toLowerCase().includes(q) || a.source.toLowerCase().includes(q);
		}
		return true;
	});

	// ── Helpers ───────────────────────────────────────────────────────────────

	function timeAgo(iso: string): string {
		const diff = Date.now() - new Date(iso).getTime();
		const m    = Math.floor(diff / 60_000);
		if (m <  1)  return 'just now';
		if (m < 60)  return `${m}m ago`;
		const h = Math.floor(m / 60);
		if (h < 24)  return `${h}h ago`;
		return `${Math.floor(h / 24)}d ago`;
	}

	function minutesAgo(iso: string | null): string {
		if (!iso) return '—';
		const m = Math.floor((Date.now() - new Date(iso).getTime()) / 60_000);
		if (m < 1)   return 'just now';
		if (m === 1) return '1 minute ago';
		if (m < 60)  return `${m} minutes ago`;
		const h = Math.floor(m / 60);
		return h === 1 ? '1 hour ago' : `${h} hours ago`;
	}

	function catColor(cat: string): string {
		if (cat === 'cybersecurity') return 'var(--red)';
		if (cat === 'ai')            return 'var(--accent4)';
		if (cat === 'robotics')      return 'var(--teal)';
		return 'var(--accent)';
	}

	function catLabel(cat: string): string {
		if (cat === 'cybersecurity') return 'CYBER';
		if (cat === 'ai')            return 'AI';
		if (cat === 'robotics')      return 'ROBOT';
		return 'TECH';
	}

	// ── Lifecycle ─────────────────────────────────────────────────────────────

	onMount(() => {
		try {
			const raw = localStorage.getItem(NEWS_CFG_KEY);
			if (raw) {
				const cfg = JSON.parse(raw);
				if (typeof cfg.sidebarW === 'number') sourceSidebarW = cfg.sidebarW;
				if (Array.isArray(cfg.disabled)) disabledSources = new Set(cfg.disabled);
			}
		} catch { /* ignore */ }
		load();
		refreshTimer = setInterval(() => load(), 60 * 60 * 1000);
	});

	onDestroy(() => {
		if (refreshTimer) clearInterval(refreshTimer);
		if (loadTimeout)  clearTimeout(loadTimeout);
	});
</script>

<svelte:head>
	<title>Nexus — News</title>
</svelte:head>

<svelte:window
	on:mousemove={onSidebarResizeMove}
	on:mouseup={stopSidebarResize}
	on:touchmove={onSidebarResizeMove}
	on:touchend={stopSidebarResize}
/>

<div class="news-page">

	<!-- ── Header ──────────────────────────────────────────────── -->
	<div class="page-header">
		<div class="header-left">
			<Rss size={16} strokeWidth={1.5} />
			<h1 class="page-title">tech news</h1>
		</div>

		<div class="header-right">
			<!-- Search -->
			<div class="search-wrap">
				<Search size={13} strokeWidth={1.5} class="search-icon" />
				<input
					class="search-input"
					type="search"
					placeholder="Search headlines…"
					bind:value={searchQuery}
					aria-label="Search news"
				/>
			</div>

			<!-- Refresh -->
			<button
				class="refresh-btn"
				class:spinning={loading}
				on:click={() => load(true)}
				disabled={loading}
				title="Refresh feed"
				aria-label="Refresh feed"
			>
				<RefreshCw size={14} strokeWidth={1.5} />
			</button>
		</div>
	</div>

	<!-- ── Filter bar ───────────────────────────────────────────── -->
	<div class="filter-bar" role="tablist" aria-label="Filter by category">
		{#each (['all', 'cybersecurity', 'tech', 'ai', 'robotics'] as Category[]) as cat}
			<button
				class="filter-btn"
				class:active={activeFilter === cat}
				style="--fc: {cat === 'all' ? 'var(--accent3)' : catColor(cat)}"
				on:click={() => activeFilter = cat}
				role="tab"
				aria-selected={activeFilter === cat}
			>
				{cat === 'all' ? 'ALL' : catLabel(cat)}
				{#if cat !== 'all'}
					<span class="filter-count">
						{articles.filter((a) => a.source !== 'System' && a.category?.toLowerCase() === cat).length}
					</span>
				{/if}
			</button>
		{/each}
		<span class="filter-total">{filtered.length} articles</span>
	</div>

	<!-- ── Status bar (last updated + feed warn) ────────────────── -->
	{#if isLoaded || showInlineRefresh}
		<div class="status-bar">
			{#if showInlineRefresh}
				<div class="refresh-inline">
					<div class="mini-spinner" aria-hidden="true"></div>
					<span>Refreshing…</span>
				</div>
			{:else}
				<span class="last-updated">Last updated: {minutesAgo(fetchedAt)}</span>
				{#if failedFeeds > 0}
					<span class="feeds-warn">{failedFeeds} feed{failedFeeds > 1 ? 's' : ''} unavailable</span>
				{/if}
			{/if}
		</div>
	{/if}

	<!-- ── Main layout (sidebar + content) ─────────────────────── -->
	<div class="news-layout" class:sidebar-resizing={sidebarResizing}>

		<!-- Source filter sidebar -->
		<div class="source-sidebar" style="width: {sourceSidebarW}px">
			<div class="source-header">Sources</div>
			<div class="source-list">
				{#if sources.length === 0}
					<span class="source-empty">{loading ? 'Loading…' : 'No sources'}</span>
				{:else}
					{#each sources as src}
						<label class="source-item">
							<input
								type="checkbox"
								checked={!disabledSources.has(src)}
								on:change={() => toggleSource(src)}
							/>
							<span class="source-name" title={src}>{src}</span>
						</label>
					{/each}
				{/if}
			</div>
		</div>

		<!-- Resize handle -->
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div
			class="source-resize"
			on:mousedown={startSidebarResize}
			on:touchstart={startSidebarResize}
		></div>

		<!-- Content area -->
		<div class="news-main">

			<!-- ── STATE 1: Loading ────────────────────────────── -->
			{#if showSkeletons}
				<div class="load-header" aria-live="polite">
					<div class="mini-spinner" aria-hidden="true"></div>
					<span class="load-text">Fetching feed...</span>
				</div>

				<div class="skeleton-list">
					<!-- Card 1: 3 bars at 55% / 100% / 75% -->
					<div class="skeleton-card">
						<div class="shimmer-bar" style="width:55%;height:10px"></div>
						<div class="shimmer-bar" style="width:100%;height:10px"></div>
						<div class="shimmer-bar" style="width:75%;height:10px"></div>
					</div>
					<!-- Card 2: 2 bars at 40% / 85% -->
					<div class="skeleton-card">
						<div class="shimmer-bar" style="width:40%;height:10px"></div>
						<div class="shimmer-bar" style="width:85%;height:10px"></div>
					</div>
					<!-- Card 3: 2 bars at 65% / 50% -->
					<div class="skeleton-card">
						<div class="shimmer-bar" style="width:65%;height:10px"></div>
						<div class="shimmer-bar" style="width:50%;height:10px"></div>
					</div>
				</div>

			<!-- ── STATE 2: Error (all feeds returned System mock) ── -->
			{:else if isError}
				<div class="full-state">
					<div class="state-icon-box state-icon-box--error">
						<CircleAlert size={26} strokeWidth={1.8} />
					</div>
					<div class="state-text-block">
						<p class="state-title">Failed to load feed</p>
						<p class="state-error-code">ERR_CONNECTION_REFUSED</p>
						<p class="state-body">Unable to reach feed sources. They may be temporarily down or URLs may be incorrect.</p>
					</div>
					<div class="state-actions">
						<button class="btn-primary" on:click={() => load(true)}>Retry</button>
						<a href="/settings" class="btn-secondary">Configure feeds</a>
					</div>
					{#if fetchedAt}
						<p class="last-success">Last successful: {timeAgo(fetchedAt)}</p>
					{/if}
				</div>

			<!-- ── STATE 3: Empty (feeds loaded but 0 articles) ─── -->
			{:else if isEmpty || (!loading && filtered.length === 0 && !isLoaded)}
				<div class="full-state">
					<div class="state-icon-box">
						<Newspaper size={26} strokeWidth={1.8} />
					</div>
					<div class="state-text-block">
						<p class="state-title">No articles found</p>
						<p class="state-body">Your feeds are connected but returned no results. Try adjusting your filters or adding more sources.</p>
					</div>
					<div class="state-actions">
						<a href="/settings" class="btn-secondary btn-accent">Add feed sources</a>
						<button class="btn-secondary" on:click={() => { activeFilter = 'all'; searchQuery = ''; disabledSources = new Set(); }}>Clear filters</button>
					</div>
				</div>

			<!-- ── STATE 4: No filter match ──────────────────────── -->
			{:else if isLoaded && filtered.length === 0}
				<div class="full-state">
					<div class="state-icon-box">
						<Search size={26} strokeWidth={1.8} />
					</div>
					<div class="state-text-block">
						<p class="state-title">No articles match your filter</p>
						<p class="state-body">Try a different category or clear your search.</p>
					</div>
					<div class="state-actions">
						<button class="btn-secondary" on:click={() => { activeFilter = 'all'; searchQuery = ''; }}>Clear filters</button>
					</div>
				</div>

			<!-- ── STATE 4: Loaded ────────────────────────────────── -->
			{:else if isLoaded}
				<div class="card-grid">
					{#each filtered as article (article.link)}
						<article
							class="news-card"
							style="--border-color: {catColor(article.category)}"
						>
							<div class="card-meta">
								<span class="cat-badge" style="color:{catColor(article.category)};border-color:color-mix(in srgb,{catColor(article.category)} 30%,var(--border))">
									{catLabel(article.category)}
								</span>
								<span class="card-source">{article.source}</span>
								<span class="card-time">{timeAgo(article.published)}</span>
							</div>

							<h2 class="card-title">
								<a
									href={article.link}
									target="_blank"
									rel="noopener noreferrer"
									class="card-title-link"
								>{article.title}</a>
							</h2>

							{#if article.summary}
								<p class="card-summary">{article.summary}</p>
							{/if}

							<div class="card-footer">
								<a
									href={article.link}
									target="_blank"
									rel="noopener noreferrer"
									class="read-more"
								>
									Read more <ExternalLink size={11} strokeWidth={1.5} />
								</a>
							</div>
						</article>
					{/each}
				</div>
			{/if}

		</div><!-- /.news-main -->
	</div><!-- /.news-layout -->

</div>

<style>
	.news-page {
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	/* ── Header ──────────────────────────────────────────────── */
	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
		flex-wrap: wrap;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		color: var(--text2);
	}

	.page-title {
		font-family: var(--font-mono);
		font-size: 1rem;
		font-weight: 700;
		color: var(--text0);
		margin: 0;
		text-transform: lowercase;
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.search-wrap {
		position: relative;
		display: flex;
		align-items: center;
	}

	:global(.search-icon) {
		position: absolute;
		left: 0.5rem;
		color: var(--text2);
		pointer-events: none;
	}

	.search-input {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.78rem;
		padding: 0.3rem 0.7rem 0.3rem 1.85rem;
		outline: none;
		width: 200px;
		transition: border-color 0.12s;
	}
	.search-input:focus { border-color: var(--accent3); }
	.search-input::placeholder { color: var(--text2); }

	.refresh-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text2);
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}
	.refresh-btn:hover:not(:disabled) { color: var(--accent3); border-color: var(--accent3); }
	.refresh-btn:disabled { opacity: 0.4; cursor: not-allowed; }
	.refresh-btn.spinning :global(svg) { animation: spin 0.8s linear infinite; }

	/* ── Filter bar ──────────────────────────────────────────── */
	.filter-bar {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		flex-wrap: wrap;
	}

	.filter-btn {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		padding: 0.22rem 0.65rem;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: 20px;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		font-weight: 700;
		letter-spacing: 0.06em;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s, background 0.1s;
	}
	.filter-btn:hover { color: var(--fc); border-color: color-mix(in srgb, var(--fc) 40%, var(--border)); }
	.filter-btn.active {
		color: var(--fc);
		border-color: color-mix(in srgb, var(--fc) 50%, var(--border));
		background: color-mix(in srgb, var(--fc) 10%, var(--bg1));
	}

	.filter-count {
		font-size: 0.6rem;
		color: inherit;
		opacity: 0.7;
	}

	.filter-total {
		margin-left: auto;
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
	}

	/* ── Status bar ──────────────────────────────────────────── */
	.status-bar {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-top: -0.25rem;
	}

	.last-updated {
		font-family: var(--font-mono);
		font-size: 0.625rem;
		color: #484f58;
	}

	.feeds-warn {
		font-family: var(--font-mono);
		font-size: 0.625rem;
		color: var(--yellow);
		opacity: 0.8;
	}

	.refresh-inline {
		display: flex;
		align-items: center;
		gap: 6px;
		font-family: var(--font-mono);
		font-size: 0.625rem;
		color: #484f58;
	}

	/* ── Mini spinner (12px, for load-header + refresh-inline) ── */
	.mini-spinner {
		width: 12px;
		height: 12px;
		border: 2px solid #484f58;
		border-top-color: #3fb950;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
		flex-shrink: 0;
	}

	/* ── Loading state ───────────────────────────────────────── */
	.load-header {
		display: flex;
		align-items: center;
		gap: 8px;
		margin-bottom: 4px;
	}

	.load-text {
		font-family: var(--font-mono);
		font-size: 0.6875rem;
		color: #484f58;
	}

	.skeleton-list {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}

	.skeleton-card {
		background: #161b22;
		border: 1px solid #30363d;
		border-radius: 8px;
		padding: 14px 16px;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}

	.shimmer-bar {
		border-radius: 3px;
		background: linear-gradient(90deg, #21262d 25%, #2c3440 50%, #21262d 75%);
		background-size: 500px 100%;
		animation: shimmer 1.4s infinite;
	}

	/* ── Full-page centered states (error / empty) ───────────── */
	.full-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 18px;
		min-height: 340px;
		text-align: center;
		padding: 48px 32px;
	}

	.state-icon-box {
		width: 56px;
		height: 56px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: #21262d;
		border: 1px solid #30363d;
		border-radius: 14px;
		color: #484f58;
		flex-shrink: 0;
	}

	.state-icon-box--error {
		background: #110808;
		border-color: #3d1515;
		color: #f85149;
	}

	.state-text-block {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
	}

	.state-title {
		font-family: var(--font-ui);
		font-size: 1.0625rem;
		font-weight: 600;
		color: #e6edf3;
		margin-bottom: 6px;
	}

	.state-error-code {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: #f85149;
		margin-bottom: 10px;
	}

	.state-body {
		font-family: var(--font-ui);
		font-size: 0.8125rem;
		color: #8b949e;
		line-height: 1.6;
		max-width: 360px;
	}

	.state-actions {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
		justify-content: center;
	}

	.btn-primary {
		padding: 9px 22px;
		background: #3fb950;
		color: #0d1117;
		font-family: var(--font-ui);
		font-size: 0.875rem;
		font-weight: 700;
		border: none;
		border-radius: 5px;
		cursor: pointer;
		text-decoration: none;
		display: inline-flex;
		align-items: center;
		transition: opacity 0.12s;
	}
	.btn-primary:hover { opacity: 0.88; }

	.btn-secondary {
		padding: 9px 16px;
		background: transparent;
		color: #8b949e;
		font-family: var(--font-ui);
		font-size: 0.875rem;
		font-weight: 500;
		border: 1px solid #30363d;
		border-radius: 5px;
		cursor: pointer;
		text-decoration: none;
		display: inline-flex;
		align-items: center;
		transition: border-color 0.12s, color 0.12s;
	}
	.btn-secondary:hover { border-color: #484f58; color: #e6edf3; text-decoration: none; }
	.btn-secondary.btn-accent { color: #58a6ff; }

	.last-success {
		font-family: var(--font-mono);
		font-size: 0.6875rem;
		color: #484f58;
	}

	@keyframes spin    { to { transform: rotate(360deg); } }
	@keyframes shimmer { 0% { background-position: -500px 0; } 100% { background-position: 500px 0; } }

	/* ── Main layout ─────────────────────────────────────────── */
	.news-layout {
		display: flex;
		align-items: stretch;
		gap: 0;
		min-height: 300px;
	}
	.news-layout.sidebar-resizing { user-select: none; }

	.source-sidebar {
		flex-shrink: 0;
		min-width: 150px;
		max-width: 350px;
		border: 1px solid var(--border);
		border-radius: var(--radius) 0 0 var(--radius);
		background: var(--bg1);
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.source-header {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text2);
		padding: 0.55rem 0.75rem;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.source-list {
		overflow-y: auto;
		flex: 1;
		padding: 0.35rem 0;
		scrollbar-width: thin;
		scrollbar-color: var(--border) transparent;
	}

	.source-empty {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
		padding: 0.75rem;
		display: block;
	}

	.source-item {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.22rem 0.75rem;
		cursor: pointer;
		transition: background 0.1s;
	}
	.source-item:hover { background: var(--bg2); }

	.source-item input[type="checkbox"] {
		flex-shrink: 0;
		accent-color: var(--accent3);
		cursor: pointer;
	}

	.source-name {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text1);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.source-resize {
		width: 4px;
		flex-shrink: 0;
		background: var(--border);
		cursor: col-resize;
		transition: background 0.12s;
		touch-action: none;
	}
	.source-resize:hover,
	.news-layout.sidebar-resizing .source-resize { background: var(--accent3); }

	.news-main {
		flex: 1;
		min-width: 0;
		padding-left: 1rem;
	}

	/* ── Card grid ───────────────────────────────────────────── */
	.card-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.85rem;
		align-items: start;
	}
	@media (max-width: 860px) { .card-grid { grid-template-columns: 1fr; } }

	/* ── News card ───────────────────────────────────────────── */
	.news-card {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-left: 3px solid var(--border-color);
		border-radius: var(--radius);
		padding: 0.75rem 0.9rem;
		display: flex;
		flex-direction: column;
		gap: 0.45rem;
		transition: border-color 0.12s, background 0.12s;
	}
	.news-card:hover {
		background: var(--bg2);
		border-color: color-mix(in srgb, var(--border-color) 40%, var(--border));
	}

	.card-meta {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		flex-wrap: wrap;
	}

	.cat-badge {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		font-weight: 700;
		letter-spacing: 0.1em;
		border: 1px solid;
		border-radius: 3px;
		padding: 0.05rem 0.35rem;
		flex-shrink: 0;
	}

	.card-source {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text2);
		flex: 1;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.card-time {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		flex-shrink: 0;
	}

	.card-title {
		font-family: var(--font-mono);
		font-size: 0.84rem;
		font-weight: 700;
		line-height: 1.45;
		margin: 0;
		color: var(--text0);
	}

	.card-title-link {
		color: inherit;
		text-decoration: none;
		transition: color 0.1s;
	}
	.card-title-link:hover { color: var(--border-color); }

	.card-summary {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text1);
		line-height: 1.6;
		margin: 0;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.card-footer {
		display: flex;
		align-items: center;
		margin-top: 0.1rem;
	}

	.read-more {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text2);
		text-decoration: none;
		transition: color 0.1s;
	}
	.read-more:hover { color: var(--border-color); }

	@media (max-width: 700px) {
		.source-sidebar { display: none; }
		.source-resize  { display: none; }
		.news-main      { padding-left: 0; }
	}
</style>
