<script lang="ts">
	import { onMount } from 'svelte';
	import { CircleMinus, CircleAlert, Plus, WifiOff } from '@lucide/svelte';

	export let variant: 'default' | 'error' | 'not-configured' | 'unreachable' = 'default';
	export let title: string;
	export let body: string = '';
	export let errorCode: string | null = null;
	export let primaryAction: string | null = null;
	export let primaryHref: string | null = null;
	export let primaryOnClick: (() => void) | null = null;
	export let secondaryAction: string | null = null;
	export let secondaryHref: string | null = null;
	export let size: 'compact' | 'default' | 'large' = 'default';

	const ICONS = {
		'default':        CircleMinus,
		'error':          CircleAlert,
		'not-configured': Plus,
		'unreachable':    WifiOff,
	} as const;

	$: Icon      = ICONS[variant];
	$: isLarge   = size === 'large';
	$: isCompact = size === 'compact';

	// 1-second delay prevents flash on fast connections.
	// Timer starts when this component mounts (= when the empty condition becomes true).
	let visible = false;
	onMount(() => {
		const t = setTimeout(() => { visible = true; }, 1000);
		return () => clearTimeout(t);
	});
</script>

{#if visible}
<div
	class="empty-state"
	class:large={isLarge}
	class:compact={isCompact}
	data-variant={variant}
	role="status"
>
	<!-- Icon box -->
	<div
		class="icon-box"
		class:icon-box--error={variant === 'error'}
		class:icon-box--dashed={variant === 'not-configured'}
		class:icon-box--large={isLarge}
	>
		<svelte:component this={Icon} size={isLarge ? 24 : 22} strokeWidth={1.6} />
	</div>

	<!-- Text -->
	<div class="text-block">
		<p class="es-title">{title}</p>
		{#if errorCode}
			<p class="es-error-code">{errorCode}</p>
		{/if}
		{#if body}
			<p class="es-body">{body}</p>
		{/if}
	</div>

	<!-- Buttons -->
	{#if primaryAction || secondaryAction}
		<div class="actions">
			{#if primaryAction}
				{#if primaryHref}
					<a href={primaryHref} class="btn-primary" class:btn-large={isLarge}>{primaryAction}</a>
				{:else if primaryOnClick}
					<button class="btn-primary" class:btn-large={isLarge} on:click={primaryOnClick}>{primaryAction}</button>
				{:else}
					<span class="btn-primary" class:btn-large={isLarge}>{primaryAction}</span>
				{/if}
			{/if}

			{#if secondaryAction}
				{#if secondaryHref}
					<a href={secondaryHref} class="btn-secondary" class:btn-large={isLarge}>{secondaryAction}</a>
				{:else}
					<button class="btn-secondary" class:btn-large={isLarge}>{secondaryAction}</button>
				{/if}
			{/if}
		</div>
	{/if}

	<!-- Extra content (e.g. "Last successful: Xh ago") -->
	<slot />
</div>
{/if}

<style>
	/* ── Shell ─────────────────────────────────────────────────── */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 14px;
		padding: 36px 24px;
		text-align: center;
	}

	.empty-state.large {
		gap: 18px;
		padding: 48px 32px;
	}

	.empty-state.compact {
		gap: 12px;
		padding: 24px 16px;
	}

	/* ── Icon box ──────────────────────────────────────────────── */
	.icon-box {
		width: 48px;
		height: 48px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: #21262d;
		border: 1px solid #30363d;
		border-radius: 12px;
		color: #484f58;
		flex-shrink: 0;
	}

	.icon-box--dashed {
		border-style: dashed;
	}

	.icon-box--error {
		background: #110808;
		border-color: #3d1515;
		border-radius: 12px;
		color: #f85149;
	}

	.icon-box--large {
		width: 56px;
		height: 56px;
		border-radius: 14px;
	}

	/* ── Text ──────────────────────────────────────────────────── */
	.text-block {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 6px;
	}

	.es-title {
		font-family: var(--font-ui);
		font-size: 0.875rem;
		font-weight: 600;
		color: #8b949e;
		line-height: 1.3;
	}

	.large .es-title {
		font-size: 1.0625rem;
		color: #e6edf3;
	}

	[data-variant="error"] .es-title {
		color: #e6edf3;
	}

	.es-error-code {
		font-family: var(--font-mono);
		font-size: 0.6875rem;
		color: #f85149;
		letter-spacing: 0.03em;
	}

	.es-body {
		font-family: var(--font-ui);
		font-size: 0.8125rem;
		color: #484f58;
		line-height: 1.55;
		max-width: 320px;
	}

	.large .es-body {
		font-size: 0.875rem;
		max-width: 360px;
	}

	/* ── Buttons ───────────────────────────────────────────────── */
	.actions {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
		justify-content: center;
	}

	.btn-primary,
	.btn-secondary {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		padding: 6px 16px;
		border-radius: 5px;
		font-family: var(--font-ui);
		font-size: 0.8125rem;
		text-decoration: none;
		cursor: pointer;
		white-space: nowrap;
		transition: opacity 0.12s, background 0.12s, border-color 0.12s, color 0.12s;
		border: 1px solid transparent;
	}

	.btn-primary.btn-large,
	.btn-secondary.btn-large {
		padding: 9px 22px;
		font-size: 0.875rem;
	}

	.btn-primary {
		background: #3fb950;
		color: #0d1117;
		font-weight: 700;
	}

	.btn-primary:hover {
		opacity: 0.88;
		text-decoration: none;
	}

	.btn-secondary {
		background: transparent;
		border-color: #30363d;
		color: #8b949e;
		font-weight: 500;
	}

	.btn-secondary:hover {
		border-color: #484f58;
		color: #e6edf3;
		text-decoration: none;
	}
</style>
