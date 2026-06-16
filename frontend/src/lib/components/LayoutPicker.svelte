<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { Check } from '@lucide/svelte';
	import { dashConfig, LAYOUT_PRESETS } from '$lib/stores/dashConfig';

	export let open = false;

	const dispatch = createEventDispatcher<{ close: void }>();

	let selected: string | null = null;
	$: if (open) selected = $dashConfig.currentLayoutId;

	function apply() {
		if (!selected) return;
		dashConfig.applyLayoutPreset(selected);
		dispatch('close');
	}

	function enabledCount(preset: (typeof LAYOUT_PRESETS)[0]) {
		return preset.widgets.filter((w) => w.enabled).length;
	}

	function currentName(): string {
		if (!$dashConfig.currentLayoutId) return 'Custom layout';
		return LAYOUT_PRESETS.find((p) => p.id === $dashConfig.currentLayoutId)?.name ?? 'Custom layout';
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') dispatch('close');
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if open}
	<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
	<div class="backdrop" on:click|self={() => dispatch('close')}>
		<div class="picker-card" role="dialog" aria-modal="true" aria-label="Choose a layout">
			<div class="picker-header">
				<div class="header-text">
					<div class="picker-title">Choose a layout</div>
					<div class="picker-subtitle">Pick a starting point. You can still move and resize everything after.</div>
				</div>
				<button class="close-btn" on:click={() => dispatch('close')} aria-label="Close">×</button>
			</div>

			<div class="preset-grid">
				{#each LAYOUT_PRESETS as preset (preset.id)}
					<button
						class="preset-card"
						class:is-selected={selected === preset.id}
						on:click={() => (selected = preset.id)}
					>
						<div class="preset-top">
							<span class="preset-icon">{preset.icon}</span>
							<span class="preset-name">{preset.name}</span>
							{#if $dashConfig.currentLayoutId === preset.id}
								<span class="active-check" aria-label="Currently active">
									<Check size={8} strokeWidth={3} color="white" />
								</span>
							{/if}
						</div>
						<p class="preset-desc">{preset.description}</p>
						<p class="preset-meta">{enabledCount(preset)} widgets · {preset.columns} columns</p>
					</button>
				{/each}
			</div>

			<div class="picker-footer">
				<span class="current-label">Currently: {currentName()}</span>
				<div class="footer-btns">
					<button class="cancel-btn" on:click={() => dispatch('close')}>Cancel</button>
					<button class="apply-btn" disabled={!selected} on:click={apply}>
						Apply layout →
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(13, 17, 23, 0.85);
		z-index: 500;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.picker-card {
		background: #161b22;
		border: 1px solid #30363d;
		border-radius: 10px;
		width: 580px;
		max-width: calc(100vw - 32px);
		max-height: 80vh;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
	}

	/* ── Header ── */
	.picker-header {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		padding: 24px 28px;
		border-bottom: 1px solid #30363d;
		position: relative;
		flex-shrink: 0;
	}

	.header-text { display: flex; flex-direction: column; gap: 4px; }

	.picker-title {
		font-size: 17px;
		font-weight: 600;
		color: #e6edf3;
		line-height: 1.2;
	}

	.picker-subtitle {
		font-size: 12px;
		color: #8b949e;
		line-height: 1.4;
	}

	.close-btn {
		position: absolute;
		top: 16px;
		right: 16px;
		width: 28px;
		height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: none;
		border: none;
		color: #484f58;
		font-size: 18px;
		cursor: pointer;
		border-radius: 5px;
		line-height: 1;
		transition: color 0.1s;
		flex-shrink: 0;
	}
	.close-btn:hover { color: #e6edf3; }

	/* ── Preset grid ── */
	.preset-grid {
		padding: 20px 28px;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 12px;
	}

	.preset-card {
		background: #21262d;
		border: 1px solid #30363d;
		border-radius: 8px;
		padding: 16px;
		cursor: pointer;
		text-align: left;
		transition: border-color 0.12s, background 0.12s;
	}
	.preset-card:hover { border-color: #484f58; }
	.preset-card.is-selected {
		border-color: #3fb950;
		background: color-mix(in srgb, #3fb950 5%, #21262d);
	}

	.preset-top {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.preset-icon {
		width: 32px;
		height: 32px;
		background: #161b22;
		border: 1px solid #30363d;
		border-radius: 6px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-size: 16px;
		flex-shrink: 0;
	}

	.preset-name {
		font-size: 14px;
		font-weight: 600;
		color: #e6edf3;
	}

	.active-check {
		margin-left: auto;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		background: #3fb950;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.preset-desc {
		font-size: 11px;
		color: #8b949e;
		margin: 8px 0 0;
		line-height: 1.45;
	}

	.preset-meta {
		font-family: var(--font-mono);
		font-size: 10px;
		color: #484f58;
		margin: 6px 0 0;
	}

	/* ── Footer ── */
	.picker-footer {
		padding: 16px 28px;
		border-top: 1px solid #30363d;
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
		flex-shrink: 0;
	}

	.current-label {
		font-family: var(--font-mono);
		font-size: 11px;
		color: #484f58;
		white-space: nowrap;
	}

	.footer-btns {
		display: flex;
		gap: 8px;
		flex-shrink: 0;
	}

	.cancel-btn {
		padding: 8px 16px;
		background: none;
		border: 1px solid #30363d;
		border-radius: 5px;
		color: #8b949e;
		font-family: var(--font-mono);
		font-size: 12px;
		cursor: pointer;
		transition: border-color 0.1s, color 0.1s;
	}
	.cancel-btn:hover { border-color: #484f58; color: #e6edf3; }

	.apply-btn {
		padding: 8px 16px;
		background: #3fb950;
		border: 1px solid #3fb950;
		border-radius: 5px;
		color: #0d1117;
		font-family: var(--font-mono);
		font-size: 12px;
		font-weight: 700;
		cursor: pointer;
		transition: opacity 0.12s;
	}
	.apply-btn:hover:not(:disabled) { opacity: 0.88; }
	.apply-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
</style>
