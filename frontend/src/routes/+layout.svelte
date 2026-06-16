<script lang="ts">
	import '../app.css';
	import Nav from '$lib/components/Nav.svelte';
	import Topbar from '$lib/components/Topbar.svelte';
	import AiQuickBar from '$lib/components/AiQuickBar.svelte';
	import AiOverlay from '$lib/components/AiOverlay.svelte';
	import Onboarding from '$lib/components/Onboarding.svelte';
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { theme } from '$lib/theme';
	import { dashConfig } from '$lib/stores/dashConfig';
	import { nexusSettings } from '$lib/stores';
	import { BASE } from '$lib/api';
	import { loadSnippets } from '$lib/snippets';

	// Re-stamp accent override whenever theme switches
	$: if (browser && $theme && $dashConfig.accentOverride) {
		document.documentElement.style.setProperty('--accent', $dashConfig.accentOverride);
	}

	// Compact mode: shrink --card-pad so Card.svelte benefits
	$: if (browser) {
		document.documentElement.style.setProperty(
			'--card-pad',
			$nexusSettings.compactMode ? '0.6rem' : '1rem',
		);
	}

	$: sidebarRight = $nexusSettings.sidebarPosition === 'right';
	$: compact = $nexusSettings.compactMode;

	onMount(async () => {
		if (window.location.pathname === '/setup') return;
		const key = localStorage.getItem('nexus_api_key');
		if (!key) {
			try {
				const res = await fetch(`${BASE}/healthz`);
				const data = await res.json();
				if (data?.auth_enabled) goto('/setup');
			} catch {
				// backend unreachable — stay on page, widgets will show mock data
			}
		}
		// Load user CSS snippets from .nexus/snippets/ — non-blocking.
		loadSnippets();
	});
</script>

<!--
  Shell grid:

  ┌──────┬───────────────────────────────────────┐
  │      │  Topbar (40px)                        │
  │ Nav  ├───────────────────────────────────────┤
  │ 52px │  Content (scrollable, flex: 1)        │
  │      ├───────────────────────────────────────┤
  │      │  AI Quick-bar (44px)                  │
  └──────┴───────────────────────────────────────┘
-->
<div class="shell" class:sidebar-right={sidebarRight}>
	<Nav />

	<div class="main">
		<Topbar />
		<main class="content" class:compact id="main-content">
			<slot />
		</main>
		<AiQuickBar />
	</div>
</div>

<!-- Overlays live outside the grid so they can cover the full viewport -->
<AiOverlay />
<Onboarding />

<style>
	.shell {
		display: flex;
		height: 100vh;
		overflow: hidden;
		background: var(--bg-base);
	}

	.shell.sidebar-right {
		flex-direction: row-reverse;
	}

	.main {
		flex: 1;
		min-width: 0; /* prevent flex blowout */
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.content {
		flex: 1;
		overflow-y: auto;
		padding: 1.5rem;
	}

	.content.compact {
		padding: 0.75rem;
	}

	/* Subtle page-change fade — only opacity, no layout shift */
	:global(.content > *) {
		animation: page-in 0.12s ease;
	}

	@keyframes page-in {
		from { opacity: 0; transform: translateY(4px); }
		to   { opacity: 1; transform: translateY(0);   }
	}

	@media (max-width: 768px) {
		/* Nav becomes fixed bottom bar; push content up to avoid overlap */
		.content {
			padding-bottom: calc(56px + 1rem);
		}
	}
</style>
