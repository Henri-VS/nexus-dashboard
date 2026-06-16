<script lang="ts">
	import { overlayOpen, overlayPrefill, overlayAutoSend, selectedModel } from '$lib/stores';
	import { MessageSquare } from '@lucide/svelte';

	let input = '';
	let inputEl: HTMLInputElement;

	// ── Global Ctrl+Space shortcut ───────────────────────────────
	// Placed here because AiQuickBar is always mounted in the layout.
	function handleGlobalKeydown(e: KeyboardEvent) {
		if (e.ctrlKey && e.code === 'Space') {
			e.preventDefault();
			// If user has typed something, pass it to the overlay
			if (input.trim()) {
				overlayPrefill.set(input.trim());
				input = '';
			}
			overlayOpen.update((v) => !v);
		}
	}

	// ── Submit: open overlay with prefill and auto-send ─────────
	function submit() {
		const q = input.trim();
		if (!q) {
			// No text — just open the overlay so user can type there
			overlayOpen.set(true);
			return;
		}
		overlayPrefill.set(q);
		overlayAutoSend.set(true);
		input = '';
		overlayOpen.set(true);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') {
			e.preventDefault();
			submit();
		}
	}

</script>

<svelte:window on:keydown={handleGlobalKeydown} />

<div class="quickbar" role="search" aria-label="AI quick input">

	<!-- Icon -->
	<span class="qb-icon" aria-hidden="true">
		<MessageSquare size={15} strokeWidth={1.5} />
	</span>

	<!-- Text input -->
	<input
		bind:this={inputEl}
		bind:value={input}
		type="text"
		class="qb-input"
		placeholder="Ask your homelab anything..."
		autocomplete="off"
		spellcheck="false"
		aria-label="Ask AI"
		on:keydown={handleKeydown}
	/>

	<!-- Active model name (read-only display) -->
	<span class="model-badge pill" title="Active model  ·  change in overlay">
		{$selectedModel}
	</span>

	<!-- Ask button -->
	<button
		class="ask-btn"
		type="button"
		on:click|stopPropagation={submit}
		aria-label="Send to AI overlay"
		title="Ask  (Enter)"
	>
		Ask
	</button>

	<!-- Keyboard hint -->
	<span class="hint" aria-hidden="true">
		<kbd>ctrl</kbd>+<kbd>space</kbd>
	</span>

</div>

<style>
	.quickbar {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0 1rem;
		height: 44px;
		background: var(--bg1);
		border-top: 1px solid var(--border);
		flex-shrink: 0;
		cursor: text;
	}

	/* ── Icon ───────────────────────────────── */
	.qb-icon {
		color: var(--accent3);
		flex-shrink: 0;
		display: flex;
		align-items: center;
	}

	/* ── Input ──────────────────────────────── */
	.qb-input {
		flex: 1;
		min-width: 0;
		background: transparent;
		border: none;
		outline: none;
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.82rem;
		caret-color: var(--accent);
		cursor: text;
	}

	.qb-input::placeholder {
		color: var(--text2);
	}

	/* ── Model badge ────────────────────────── */
	.model-badge {
		color: var(--accent3);
		border-color: color-mix(in srgb, var(--accent3) 25%, var(--border));
		flex-shrink: 0;
		max-width: 110px;
		overflow: hidden;
		text-overflow: ellipsis;
		cursor: default;
	}

	/* ── Ask button ─────────────────────────── */
	.ask-btn {
		background: var(--accent);
		border: none;
		border-radius: var(--radius);
		color: var(--bg0);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		font-weight: 700;
		padding: 0.25rem 0.65rem;
		flex-shrink: 0;
		transition: opacity 0.12s;
		letter-spacing: 0.03em;
	}

	.ask-btn:hover {
		opacity: 0.85;
	}

	/* ── Keyboard hint ──────────────────────── */
	.hint {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
		white-space: nowrap;
		flex-shrink: 0;
		user-select: none;
		display: flex;
		align-items: center;
		gap: 0.1rem;
	}

	@media (max-width: 600px) {
		.hint   { display: none; }
		.model-badge { display: none; }
	}
</style>
