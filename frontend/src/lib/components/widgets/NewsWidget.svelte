<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { news as newsApi } from '$lib/api';
	import type { NewsArticle } from '$lib/api';
	import { Newspaper, ExternalLink } from '@lucide/svelte';

	let articles: NewsArticle[] = [];
	let loading  = true;
	let skeletonMinShown = false;
	let timer:   ReturnType<typeof setInterval> | null = null;

	const LIMIT = 5;

	async function load() {
		const res = await newsApi.feed();
		if (res?.articles?.length) {
			articles = res.articles.slice(0, LIMIT);
		}
		loading = false;
	}

	function catColor(cat: string): string {
		if (cat === 'cybersecurity') return 'var(--red)';
		if (cat === 'ai')            return 'var(--accent4)';
		return 'var(--accent)';
	}

	function timeAgo(iso: string): string {
		const diff = Date.now() - new Date(iso).getTime();
		const m    = Math.floor(diff / 60_000);
		if (m <  1)  return 'just now';
		if (m < 60)  return `${m}m ago`;
		const h = Math.floor(m / 60);
		if (h < 24)  return `${h}h ago`;
		return `${Math.floor(h / 24)}d ago`;
	}

	onMount(() => {
		setTimeout(() => { skeletonMinShown = true; }, 400);
		load();
		timer = setInterval(load, 60 * 60 * 1000);
	});

	onDestroy(() => { if (timer) clearInterval(timer); });
</script>

<div class="card">
	<!-- Header -->
	<div class="card-header">
		<div class="header-left">
			<span class="accent-bar"></span>
			<Newspaper size={13} strokeWidth={1.5} />
			<span class="card-title">tech news</span>
		</div>
		<a href="/news" class="view-all">View all →</a>
	</div>

	<!-- Body -->
	<div class="card-body">
		{#if !skeletonMinShown || loading}
			<div class="skeleton-list">
				{#each Array(LIMIT) as _, i (i)}
					<div class="skeleton-row">
						<div class="sk-dot"></div>
						<div class="sk-lines">
							<div class="sk-line sk-title"></div>
							<div class="sk-line sk-meta"></div>
						</div>
					</div>
				{/each}
			</div>

		{:else if articles.length === 0}
			<p class="empty-text">No articles loaded.</p>

		{:else}
			<ul class="news-list" role="list">
				{#each articles as article (article.link)}
					<li class="news-item">
						<span
							class="cat-dot"
							style="background:{catColor(article.category)}"
							title={article.category}
						></span>
						<div class="item-body">
							<a
								href={article.link}
								target="_blank"
								rel="noopener noreferrer"
								class="item-title"
							>
								{article.title}
								<ExternalLink size={10} strokeWidth={1.5} class="ext-icon" />
							</a>
							<div class="item-meta">
								<span class="item-source">{article.source}</span>
								<span class="item-time">{timeAgo(article.published)}</span>
							</div>
						</div>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
</div>

<style>
	.card {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
	}

	/* ── Header ──────────────────────────────────────────────── */
	.card-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.6rem 0.85rem;
		border-bottom: 1px solid var(--border);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		color: var(--text2);
	}

	.accent-bar {
		width: 3px;
		height: 0.85rem;
		background: var(--accent3);
		border-radius: 2px;
		flex-shrink: 0;
	}

	.card-title {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text1);
	}

	.view-all {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--accent3);
		text-decoration: none;
		transition: opacity 0.1s;
	}
	.view-all:hover { opacity: 0.75; }

	/* ── Body ────────────────────────────────────────────────── */
	.card-body {
		padding: 0.35rem 0;
	}

	/* ── News list ───────────────────────────────────────────── */
	.news-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-direction: column;
	}

	.news-item {
		display: flex;
		align-items: flex-start;
		gap: 0.55rem;
		padding: 0.45rem 0.85rem;
		border-bottom: 1px solid color-mix(in srgb, var(--border) 50%, transparent);
		transition: background 0.08s;
	}
	.news-item:last-child { border-bottom: none; }
	.news-item:hover { background: var(--bg2); }

	.cat-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		flex-shrink: 0;
		margin-top: 5px;
	}

	.item-body {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.18rem;
	}

	.item-title {
		font-family: var(--font-mono);
		font-size: 0.76rem;
		color: var(--text0);
		text-decoration: none;
		line-height: 1.4;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
		transition: color 0.1s;
	}
	.item-title:hover { color: var(--accent3); }

	:global(.ext-icon) {
		display: inline;
		vertical-align: middle;
		margin-left: 2px;
		opacity: 0.5;
	}

	.item-meta {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.item-source {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text2);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		max-width: 120px;
	}

	.item-time {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text2);
		flex-shrink: 0;
	}

	.empty-text {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text2);
		padding: 0.75rem 0.85rem;
	}

	/* ── Skeleton ────────────────────────────────────────────── */
	.skeleton-list {
		display: flex;
		flex-direction: column;
	}

	.skeleton-row {
		display: flex;
		align-items: flex-start;
		gap: 0.55rem;
		padding: 0.5rem 0.85rem;
		border-bottom: 1px solid color-mix(in srgb, var(--border) 50%, transparent);
	}
	.skeleton-row:last-child { border-bottom: none; }

	.sk-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: linear-gradient(90deg, #21262d 25%, #2c3440 50%, #21262d 75%);
		background-size: 500px 100%;
		flex-shrink: 0;
		margin-top: 5px;
		animation: shimmer 1.4s infinite;
	}

	.sk-lines {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}

	.sk-line {
		height: 8px;
		border-radius: 4px;
		background: linear-gradient(90deg, #21262d 25%, #2c3440 50%, #21262d 75%);
		background-size: 500px 100%;
		animation: shimmer 1.4s infinite;
	}
	.sk-title { width: 85%; }
	.sk-meta  { width: 45%; }
</style>
