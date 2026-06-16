<script lang="ts">
	import { page } from '$app/stores';
	import { onMount, onDestroy } from 'svelte';
	import {
		Home,
		Server,
		Box,
		CalendarDays,
		Shield,
		MessageSquare,
		Newspaper,
		Settings,
		ChevronLeft,
		ChevronRight,
		NotebookText,
		FolderOpen,
		Zap,
		GraduationCap,
		ScrollText,
	} from '@lucide/svelte';
	import { browser } from '$app/environment';
	import { docker as dockerApi, ai as aiApi, security as securityApi } from '$lib/api';

	// ── Sidebar expand/collapse ───────────────────────────────────
	const EXPAND_KEY = 'nexus_sidebar_expanded';
	let expanded = true;

	if (browser) {
		try {
			const stored = localStorage.getItem(EXPAND_KEY);
			if (stored !== null) expanded = stored === 'true';
		} catch { /* ignore */ }
	}

	function toggle() {
		expanded = !expanded;
		if (browser) {
			try { localStorage.setItem(EXPAND_KEY, String(expanded)); } catch { /* ignore */ }
		}
	}

	// ── Live badge data ──────────────────────────────────────────
	let containerRunning = 0;
	let containerTotal   = 0;
	let ollamaOnline       = false;
	let securityAlertCount = 0;
	let securityLive       = false;
	let badgeTimer: ReturnType<typeof setInterval>;

	async function loadBadges() {
		try {
			const res = await dockerApi.containers();
			if (res) {
				containerRunning = res.containers.filter((c) => c.status === 'running').length;
				containerTotal   = res.containers.length;
			}
		} catch { /* ignore */ }
		try {
			const health = await aiApi.health();
			ollamaOnline = health?.status === 'online';
		} catch { /* ignore */ }
		try {
			const sec = await securityApi.alerts();
			if (sec?.live) { securityAlertCount = sec.alerts.length; securityLive = true; }
			else           { securityAlertCount = 0; securityLive = false; }
		} catch { /* ignore */ }
	}

	onMount(() => {
		loadBadges();
		badgeTimer = setInterval(loadBadges, 30_000);
	});
	onDestroy(() => clearInterval(badgeTimer));

	// ── Host info ────────────────────────────────────────────────
	let hostName = 'homelab';
	onMount(() => { hostName = window.location.hostname; });

	// ── Route definitions ────────────────────────────────────────
	type BadgeType = 'containers' | 'security' | 'ai' | null;
	type LucideIcon = typeof Home;

	const NAV_LINKS: Array<{ href: string; label: string; Icon: LucideIcon; badge: BadgeType }> = [
		{ href: '/',             label: 'Dashboard',    Icon: Home,          badge: null         },
		{ href: '/home',         label: 'Services',     Icon: Server,        badge: null         },
		{ href: '/lab',          label: 'Containers',   Icon: Box,           badge: 'containers' },
		{ href: '/calendar',     label: 'Calendar',     Icon: CalendarDays,  badge: null         },
		{ href: '/security',     label: 'Security',     Icon: Shield,        badge: 'security'   },
		{ href: '/ai',           label: 'AI Assistant', Icon: MessageSquare, badge: 'ai'         },
		{ href: '/news',         label: 'News',         Icon: Newspaper,     badge: null         },
		{ href: '/notes',        label: 'Notes',        Icon: NotebookText,  badge: null         },
		{ href: '/resources',    label: 'Resources',    Icon: FolderOpen,    badge: null         },
		{ href: '/automations',  label: 'Automations',  Icon: Zap,           badge: null         },
		{ href: '/learn',        label: 'Learning',     Icon: GraduationCap, badge: null         },
		{ href: '/logs',         label: 'Logs',         Icon: ScrollText,    badge: null         },
	];

	$: isActive = (href: string) =>
		href === '/'
			? $page.url.pathname === '/'
			: $page.url.pathname.startsWith(href);
</script>

<aside class="sidebar" class:expanded aria-label="Primary navigation">

	<!-- ── Logo ──────────────────────────────────────────────── -->
	<a href="/" class="logo" aria-label="Nexus Dashboard" title="Dashboard">
		<span class="logo-mark">N</span>
		{#if expanded}<span class="logo-name">Nexus</span>{/if}
	</a>

	<!-- ── Nav ───────────────────────────────────────────────── -->
	<div class="nav-scroll">
		<ul class="nav-list" role="list">

			{#each NAV_LINKS as { href, label, Icon, badge }}
				{@const active = isActive(href)}
				<li class="nav-item">
					<a
						{href}
						class="nav-link"
						class:active
						title={label}
						aria-current={active ? 'page' : undefined}
					>
						<span class="indicator" class:on={active}></span>
						<svelte:component this={Icon} size={15} strokeWidth={1.8} />
						{#if expanded}
							<span class="nav-label">{label}</span>
							{#if badge === 'containers' && containerTotal > 0}
								<span class="badge badge-green">{containerRunning}/{containerTotal}</span>
							{:else if badge === 'security' && securityLive && securityAlertCount > 0}
								<span class="badge badge-red">{securityAlertCount}</span>
							{:else if badge === 'ai' && !ollamaOnline}
								<span class="badge badge-red">OFF</span>
							{/if}
						{/if}
					</a>
				</li>
			{/each}

			<!-- Divider before Settings -->
			<li class="nav-divider" aria-hidden="true"></li>

			<!-- Settings -->
			<li class="nav-item">
				<a
					href="/settings"
					class="nav-link"
					class:active={isActive('/settings')}
					title="Settings"
					aria-current={isActive('/settings') ? 'page' : undefined}
				>
					<span class="indicator" class:on={isActive('/settings')}></span>
					<Settings size={15} strokeWidth={1.8} />
					{#if expanded}<span class="nav-label">Settings</span>{/if}
				</a>
			</li>

		</ul>
	</div>

	<!-- ── Footer ────────────────────────────────────────────── -->
	<div class="sidebar-footer">
		{#if expanded}
			<div class="avatar" aria-hidden="true">A</div>
			<div class="footer-info">
				<span class="footer-name">admin</span>
				<span class="footer-host">{hostName}</span>
			</div>
		{/if}
		<button
			class="collapse-btn"
			on:click={toggle}
			title={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
			aria-label={expanded ? 'Collapse sidebar' : 'Expand sidebar'}
		>
			{#if expanded}
				<ChevronLeft size={13} strokeWidth={2} />
			{:else}
				<ChevronRight size={13} strokeWidth={2} />
			{/if}
		</button>
	</div>

</aside>

<style>
	/* ── Shell ──────────────────────────────────────────────── */
	.sidebar {
		width: var(--sidebar-w-collapsed);
		background: var(--bg1);
		border-right: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		flex-shrink: 0;
		overflow: hidden;
		transition: width 0.18s ease;
	}

	.sidebar.expanded {
		width: var(--sidebar-w);
	}

	/* ── Logo ───────────────────────────────────────────────── */
	.logo {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		height: 57px;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
		text-decoration: none;
		gap: 0.55rem;
		padding: 0 12px;
		overflow: hidden;
	}

	.sidebar.expanded .logo {
		justify-content: flex-start;
	}

	.logo-mark {
		font-family: var(--font-mono);
		font-size: 1.05rem;
		font-weight: 800;
		color: var(--accent);
		line-height: 1;
		flex-shrink: 0;
	}

	.logo-name {
		font-family: var(--font-ui);
		font-size: 0.9rem;
		font-weight: 600;
		color: var(--text0);
		white-space: nowrap;
	}

	/* ── Nav scroll area ────────────────────────────────────── */
	.nav-scroll {
		flex: 1;
		overflow-y: auto;
		overflow-x: hidden;
		scrollbar-width: none;
		padding: 6px 0;
	}
	.nav-scroll::-webkit-scrollbar { display: none; }

	/* ── Nav list ───────────────────────────────────────────── */
	.nav-list {
		list-style: none;
		padding: 0 6px;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.nav-item { width: 100%; }

	/* ── Nav link ───────────────────────────────────────────── */
	.nav-link {
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		padding: 8px 0;
		border-radius: 5px;
		gap: 9px;
		color: #8b949e;
		text-decoration: none;
		overflow: hidden;
		transition: background 0.1s, color 0.1s;
	}

	.sidebar.expanded .nav-link {
		justify-content: flex-start;
		padding: 8px 10px;
	}

	.nav-link:hover {
		background: #21262d;
		color: #e6edf3;
	}

	.nav-link.active {
		background: #21262d;
		color: #e6edf3;
	}

	/* ── Active indicator bar ───────────────────────────────── */
	.indicator {
		position: absolute;
		left: 0;
		top: 6px;
		bottom: 6px;
		width: 2.5px;
		border-radius: 0 2px 2px 0;
		background: transparent;
		transition: background 0.1s;
		flex-shrink: 0;
	}

	.indicator.on {
		background: #3fb950;
	}

	/* ── Nav label ──────────────────────────────────────────── */
	.nav-label {
		font-family: var(--font-ui);
		font-size: 13px;
		font-weight: 500;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		flex: 1;
	}

	/* ── Badges ─────────────────────────────────────────────── */
	.badge {
		padding: 1px 6px;
		border-radius: 8px;
		flex-shrink: 0;
		font-family: var(--font-mono);
		font-size: 9px;
		letter-spacing: 0.03em;
	}

	.badge-green {
		background: #0d2010;
		border: 1px solid #1d4a25;
		color: #3fb950;
	}

	.badge-red {
		background: #1d0808;
		border: 1px solid #4d1515;
		color: #f85149;
	}

	/* ── Divider before Settings ────────────────────────────── */
	.nav-divider {
		height: 1px;
		background: #30363d;
		margin: 6px 4px;
	}

	/* ── Footer ─────────────────────────────────────────────── */
	.sidebar-footer {
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 10px 0;
		border-top: 1px solid #30363d;
		flex-shrink: 0;
		min-height: 48px;
	}

	.sidebar.expanded .sidebar-footer {
		justify-content: flex-start;
		gap: 8px;
		padding: 10px 14px;
	}

	.avatar {
		width: 28px;
		height: 28px;
		border-radius: 50%;
		background: linear-gradient(135deg, #3fb950, #58a6ff);
		color: #0d1117;
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 700;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.footer-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.footer-name {
		font-family: var(--font-ui);
		font-size: 12px;
		font-weight: 600;
		color: #e6edf3;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.footer-host {
		font-family: var(--font-mono);
		font-size: 10px;
		color: #484f58;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.collapse-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 22px;
		height: 22px;
		background: none;
		border: none;
		color: #484f58;
		cursor: pointer;
		border-radius: 4px;
		flex-shrink: 0;
		transition: color 0.1s, background 0.1s;
	}

	.sidebar.expanded .collapse-btn {
		margin-left: auto;
	}

	.collapse-btn:hover {
		color: #8b949e;
		background: #21262d;
	}

	/* ── Mobile: fixed bottom bar ───────────────────────────── */
	@media (max-width: 768px) {
		.sidebar {
			position: fixed;
			bottom: 0;
			left: 0;
			right: 0;
			width: 100% !important;
			height: 56px;
			flex-direction: row;
			border-right: none;
			border-top: 1px solid var(--border);
			z-index: 200;
			overflow: visible;
		}

		.logo          { display: none; }
		.sidebar-footer { display: none; }
		.nav-divider   { display: none; }

		.nav-scroll {
			flex: 1;
			overflow-x: auto;
			overflow-y: hidden;
			padding: 0;
			scrollbar-width: none;
		}
		.nav-scroll::-webkit-scrollbar { display: none; }

		.nav-list {
			flex-direction: row;
			padding: 0;
			gap: 0;
			justify-content: space-around;
			align-items: center;
			height: 56px;
		}

		.nav-item { width: auto; flex-shrink: 0; }

		.nav-link {
			height: 56px;
			width: 48px;
			padding: 0 !important;
			justify-content: center !important;
			border-radius: 0;
		}

		.indicator {
			top: 0;
			bottom: auto;
			left: 0;
			right: 0;
			width: 100%;
			height: 2.5px;
			border-radius: 0 0 2px 2px;
		}

		.nav-label { display: none; }
		.badge     { display: none; }
	}
</style>
