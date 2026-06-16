<script lang="ts">
	export let label: string;
	export let accentColor: string;
	export let loading = false;
	export let error: string | null = null;
	/** When true, data is coming from offline mock — shows a subtle dim dot */
	export let mocked = false;
</script>

<div class="card" style="--card-accent: {accentColor}">
	<div class="card-header">
		<span class="label">{label}</span>
		<div class="header-right">
			{#if mocked}
				<span class="mocked-badge" title="Using offline mock data">offline</span>
			{/if}
			{#if loading}
				<span class="spinner" aria-hidden="true" aria-label="Loading"></span>
			{/if}
		</div>
	</div>

	<div class="card-body">
		{#if error}
			<p class="error-msg">⚠ {error}</p>
		{:else}
			<slot />
		{/if}
	</div>
</div>

<style>
	/* ── Shell ──────────────────────────────────────────────── */
	.card {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		border-left: 3px solid var(--card-accent); /* category accent bar */
		overflow: hidden;
		display: flex;
		flex-direction: column;
	}

	/* ── Header ─────────────────────────────────────────────── */
	.card-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.45rem 0.85rem;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.label {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--card-accent);
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.mocked-badge {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text2);
		border: 1px solid var(--border);
		border-radius: 3px;
		padding: 0.05rem 0.3rem;
	}

	/* Pulsing dot while loading */
	@keyframes spin {
		to { transform: rotate(360deg); }
	}
	.spinner {
		display: inline-block;
		width: 10px;
		height: 10px;
		border: 1.5px solid var(--border);
		border-top-color: var(--card-accent);
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}

	/* ── Body ───────────────────────────────────────────────── */
	.card-body {
		padding: 0.85rem;
		flex: 1;
	}

	/* ── Error ──────────────────────────────────────────────── */
	.error-msg {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--red);
	}

</style>
