<script lang="ts">
	import { page } from '$app/stores';
	import { onDestroy, onMount } from 'svelte';
	import { ai } from '$lib/api';
	import { LayoutGrid, Bell, Search, Settings2 } from '@lucide/svelte';
	import { editMode, dashConfig, LAYOUT_PRESETS } from '$lib/stores/dashConfig';
	import LayoutPicker from '$lib/components/LayoutPicker.svelte';

	let showLayoutPicker = false;

	// ── Page title ────────────────────────────────────────────────
	const PAGE_TITLES: Record<string, string> = {
		'/':             'Dashboard',
		'/ai':           'AI',
		'/lab':          'Lab',
		'/notes':        'Notes',
		'/learn':        'Learn',
		'/home':         'Services',
		'/settings':     'Settings',
		'/calendar':     'Calendar',
		'/news':         'News',
		'/automations':  'Automations',
		'/logs':         'Logs',
		'/resources':    'Resources',
	};

	$: currentPage =
		PAGE_TITLES[$page.url.pathname] ??
		Object.entries(PAGE_TITLES).find(([k]) => k !== '/' && $page.url.pathname.startsWith(k))?.[1] ??
		'Nexus';

	$: isAI = $page.url.pathname.startsWith('/ai');

	// ── Clock — updates every second ─────────────────────────────
	let now = new Date();
	let clockTimer: ReturnType<typeof setInterval>;

	$: timeStr = now.toLocaleTimeString(undefined, {
		hour:   '2-digit',
		minute: '2-digit',
		second: '2-digit',
		hour12: false,
	});

	// ── Host name ─────────────────────────────────────────────────
	let hostName = 'homelab';

	// ── Ollama health ─────────────────────────────────────────────
	type OllamaStatus = 'checking' | 'ok' | 'error';
	let ollamaStatus: OllamaStatus = 'checking';
	let healthTimer: ReturnType<typeof setInterval>;

	async function checkOllama() {
		const data = await ai.health();
		ollamaStatus = data?.status === 'online' ? 'ok' : 'error';
	}

	onMount(() => {
		hostName    = window.location.hostname;
		clockTimer  = setInterval(() => { now = new Date(); }, 1_000);
		checkOllama();
		healthTimer = setInterval(checkOllama, 30_000);
	});
	onDestroy(() => {
		clearInterval(clockTimer);
		clearInterval(healthTimer);
	});

	// ── Search ────────────────────────────────────────────────────
	let searchEl: HTMLInputElement;

	function handleGlobalKeydown(e: KeyboardEvent) {
		if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
			e.preventDefault();
			searchEl?.focus();
		}
	}

	// ── Notifications ─────────────────────────────────────────────
	const unreadCount = 0; // TODO: wire up notification backend
</script>

<svelte:window on:keydown={handleGlobalKeydown} />

<header class="topbar">

	<!-- Mobile-only logo -->
	<a class="mobile-logo" href="/" aria-label="Dashboard home">N</a>

	<!-- Left: brand / page title + subtitle -->
	<div class="left-group">
		<a href="/" class="brand" title="Go to dashboard">nexus</a>
		<span class="title-sep" aria-hidden="true">/</span>
		<div class="page-info">
			<span class="page-title">{currentPage}</span>
			<span class="page-subtitle">{timeStr} · {hostName}</span>
		</div>
	</div>

	<!-- Right: search + bell + AI dot + edit -->
	<div class="right-group">

		<!-- Search bar -->
		<div class="search-wrap">
			<span class="search-icon-wrap" aria-hidden="true">
				<Search size={13} strokeWidth={1.5} />
			</span>
			<input
				bind:this={searchEl}
				type="text"
				class="search-input"
				placeholder="Search services..."
				aria-label="Search services"
			/>
			<span class="search-kbd" aria-hidden="true">⌘K</span>
		</div>

		<!-- Notification bell -->
		<button class="bell-btn" title="Notifications" aria-label="Notifications">
			<Bell size={15} strokeWidth={1.5} />
			{#if unreadCount > 0}
				<span class="bell-dot" aria-label="{unreadCount} unread notifications"></span>
			{/if}
		</button>

		<!-- AI status dot (text only on /ai page) -->
		<div
			class="ai-status"
			class:online={ollamaStatus === 'ok'}
			class:checking={ollamaStatus === 'checking'}
			class:error={ollamaStatus === 'error'}
			title="Ollama {ollamaStatus === 'ok' ? 'online' : ollamaStatus === 'checking' ? 'checking' : 'offline'}"
		>
			<span class="ai-dot" aria-hidden="true"></span>
			{#if isAI}
				<span class="ai-label">
					{ollamaStatus === 'ok' ? 'online' : ollamaStatus === 'checking' ? 'checking' : 'offline'}
				</span>
			{/if}
		</div>

		<!-- Layout preset picker button -->
		<button
			class="topbar-btn"
			on:click={() => (showLayoutPicker = true)}
			title="Choose layout"
		>
			<LayoutGrid size={14} strokeWidth={1.8} />
			<span class="layout-name">
				{$dashConfig.currentLayoutId
					? (LAYOUT_PRESETS.find((p) => p.id === $dashConfig.currentLayoutId)?.name ?? 'Custom')
					: 'Custom'}
			</span>
		</button>

		<!-- Widget settings toggle -->
		<button
			class="edit-btn"
			class:active={$editMode}
			on:click={() => editMode.update((v) => !v)}
			title="Toggle widget settings"
			aria-pressed={$editMode}
		>
			<Settings2 size={13} strokeWidth={1.5} />
			Settings
		</button>

	</div>
</header>

<LayoutPicker bind:open={showLayoutPicker} on:close={() => (showLayoutPicker = false)} />

<style>
	/* ── Shell ───────────────────────────────────────────────── */
	.topbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 1.25rem;
		height: 57px;
		background: var(--bg1);
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
		gap: 1rem;
		overflow: hidden;
	}

	/* ── Left group ──────────────────────────────────────────── */
	.left-group {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		min-width: 0;
		overflow: hidden;
	}

	.brand {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text2);
		text-decoration: none;
		white-space: nowrap;
		flex-shrink: 0;
		transition: color 0.1s;
	}
	.brand:hover { color: var(--text1); }

	.title-sep {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text2);
		user-select: none;
		flex-shrink: 0;
	}

	.page-info {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.page-title {
		font-family: var(--font-ui);
		font-size: 16px;
		font-weight: 600;
		color: #e6edf3;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		line-height: 1.2;
	}

	.page-subtitle {
		font-family: var(--font-mono);
		font-size: 10px;
		color: #484f58;
		margin-top: 1px;
		white-space: nowrap;
		font-variant-numeric: tabular-nums;
		letter-spacing: 0.01em;
	}

	/* ── Right group ─────────────────────────────────────────── */
	.right-group {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		flex-shrink: 0;
	}

	/* ── Search ──────────────────────────────────────────────── */
	.search-wrap {
		position: relative;
		display: flex;
		align-items: center;
		width: 220px;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
		transition: border-color 0.12s;
	}
	.search-wrap:focus-within {
		border-color: color-mix(in srgb, var(--accent) 60%, var(--border));
	}

	.search-icon-wrap {
		position: absolute;
		left: 8px;
		display: flex;
		align-items: center;
		color: var(--text2);
		pointer-events: none;
	}

	.search-input {
		flex: 1;
		background: none;
		border: none;
		outline: none;
		padding: 0.28rem 2.4rem 0.28rem 1.9rem;
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text0);
		width: 100%;
	}
	.search-input::placeholder { color: var(--text2); }

	.search-kbd {
		position: absolute;
		right: 7px;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--border);
		pointer-events: none;
		white-space: nowrap;
	}

	/* ── Notification bell ───────────────────────────────────── */
	.bell-btn {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 36px;
		height: 36px;
		background: none;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		cursor: pointer;
		transition: color 0.1s, background 0.1s, border-color 0.1s;
		flex-shrink: 0;
	}
	.bell-btn:hover {
		color: var(--text0);
		background: var(--bg2);
	}

	.bell-dot {
		position: absolute;
		top: 7px;
		right: 7px;
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: #f85149;
		border: 1.5px solid var(--bg1);
	}

	/* ── AI status dot ───────────────────────────────────────── */
	.ai-status {
		display: flex;
		align-items: center;
		gap: 5px;
		flex-shrink: 0;
	}

	.ai-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--text2);
		flex-shrink: 0;
		transition: background 0.3s;
	}

	.ai-status.checking .ai-dot { background: var(--yellow); }
	.ai-status.online   .ai-dot { background: var(--green);  }
	.ai-status.error    .ai-dot { background: var(--red);    }

	.ai-label {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text2);
		transition: color 0.2s;
	}
	.ai-status.online .ai-label { color: var(--green); }
	.ai-status.error  .ai-label { color: var(--red);   }

	/* ── Layout preset button ───────────────────────────────── */
	.topbar-btn {
		display: flex;
		align-items: center;
		gap: 5px;
		padding: 6px 10px;
		background: transparent;
		border: 1px solid var(--border);
		border-radius: 5px;
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 11px;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
		white-space: nowrap;
		flex-shrink: 0;
	}
	.topbar-btn:hover { border-color: #484f58; color: #e6edf3; }

	.layout-name {
		font-family: var(--font-mono);
		font-size: 10px;
	}

	/* ── Edit layout button ──────────────────────────────────── */
	.edit-btn {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.28rem 0.65rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-ui);
		font-size: 0.75rem;
		font-weight: 500;
		cursor: pointer;
		transition: color 0.12s, border-color 0.12s, background 0.12s;
		white-space: nowrap;
		flex-shrink: 0;
	}
	.edit-btn:hover { color: var(--text0); border-color: var(--accent3); }
	.edit-btn.active {
		color: var(--accent3);
		border-color: var(--accent3);
		background: color-mix(in srgb, var(--accent3) 12%, var(--bg2));
	}

	/* ── Mobile ──────────────────────────────────────────────── */
	.mobile-logo {
		display: none;
		font-family: var(--font-mono);
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--accent);
		text-decoration: none;
		flex-shrink: 0;
	}

	@media (max-width: 768px) {
		.topbar       { padding: 0 0.75rem; height: 48px; }
		.mobile-logo  { display: flex; align-items: center; }
		.left-group   { display: none; }
		.search-wrap  { display: none; }
		.bell-btn     { display: none; }
		.ai-status    { display: none; }
		.topbar-btn   { display: none; }
		.edit-btn     { display: none; }
	}
</style>
