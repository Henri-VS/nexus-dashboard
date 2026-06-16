<script lang="ts">
	import { X } from '@lucide/svelte';
	import { dashConfig, editMode, WIDGET_DEFS } from '$lib/stores/dashConfig';

	function toggle(id: string, enabled: boolean) {
		dashConfig.updateWidget(id, { enabled });
	}
</script>

<aside class="tray" class:open={$editMode} aria-label="Widget tray">
	<div class="tray-header">
		<span class="tray-title">Widgets</span>
		<button class="close-btn" on:click={() => editMode.set(false)} title="Close">
			<X size={14} strokeWidth={2} />
		</button>
	</div>

	<div class="tray-list">
		{#each WIDGET_DEFS as def}
			{@const widget = $dashConfig.widgets.find((w) => w.id === def.id)}
			{@const enabled = widget?.enabled ?? def.defaultEnabled}
			<label class="tray-item" title={enabled ? 'Hide widget' : 'Show widget'}>
				<span class="tray-icon" aria-hidden="true">{def.icon}</span>
				<span class="tray-label">{def.label}</span>
				<span class="tray-toggle" class:on={enabled}>
					<input
						type="checkbox"
						class="sr-only"
						checked={enabled}
						on:change={(e) => toggle(def.id, (e.currentTarget as HTMLInputElement).checked)}
					/>
					<span class="toggle-track">
						<span class="toggle-thumb"></span>
					</span>
				</span>
			</label>
		{/each}
	</div>

	<div class="tray-hint">Drag widgets in the grid to reorder</div>
</aside>

<style>
	.tray {
		position: fixed;
		top: 0;
		right: 0;
		bottom: 0;
		width: 220px;
		background: var(--bg1);
		border-left: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		z-index: 60;
		transform: translateX(100%);
		transition: transform 0.22s ease;
		box-shadow: -8px 0 32px rgba(0, 0, 0, 0.4);
	}

	.tray.open {
		transform: translateX(0);
	}

	/* ── Header ──────────────────────────────────────────────── */
	.tray-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.65rem 0.85rem;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.tray-title {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text2);
	}

	.close-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		padding: 3px;
		border-radius: 4px;
		transition: color 0.1s, background 0.1s;
	}

	.close-btn:hover { color: var(--text0); background: var(--bg2); }

	/* ── List ────────────────────────────────────────────────── */
	.tray-list {
		flex: 1;
		overflow-y: auto;
		padding: 0.4rem;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.tray-item {
		display: flex;
		align-items: center;
		gap: 0.55rem;
		padding: 0.45rem 0.5rem;
		border-radius: var(--radius);
		cursor: pointer;
		transition: background 0.1s;
		user-select: none;
	}

	.tray-item:hover { background: var(--bg2); }

	.tray-icon {
		font-size: 0.95rem;
		flex-shrink: 0;
		width: 1.4rem;
		text-align: center;
	}

	.tray-label {
		flex: 1;
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text0);
	}

	/* ── Toggle switch ───────────────────────────────────────── */
	.sr-only {
		position: absolute;
		width: 1px; height: 1px;
		overflow: hidden;
		clip: rect(0,0,0,0);
		white-space: nowrap;
	}

	.toggle-track {
		display: flex;
		align-items: center;
		width: 28px;
		height: 16px;
		background: var(--bg3);
		border: 1px solid var(--border);
		border-radius: 999px;
		padding: 2px;
		transition: background 0.15s, border-color 0.15s;
		flex-shrink: 0;
		cursor: pointer;
	}

	.tray-toggle.on .toggle-track {
		background: color-mix(in srgb, var(--accent) 30%, var(--bg3));
		border-color: var(--accent);
	}

	.toggle-thumb {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		background: var(--text2);
		transition: transform 0.15s, background 0.15s;
	}

	.tray-toggle.on .toggle-thumb {
		transform: translateX(12px);
		background: var(--accent);
	}

	/* ── Hint ────────────────────────────────────────────────── */
	.tray-hint {
		padding: 0.65rem 0.85rem;
		border-top: 1px solid var(--border);
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		line-height: 1.5;
		flex-shrink: 0;
	}
</style>
