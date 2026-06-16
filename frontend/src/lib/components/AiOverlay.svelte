<script lang="ts">
	import { tick } from 'svelte';
	import { MessageSquare } from '@lucide/svelte';
	import { marked } from 'marked';
	import { ai as aiApi } from '$lib/api';
	import { overlayOpen, overlayPrefill, overlayAutoSend, selectedModel } from '$lib/stores';
	import { generateId } from '$lib/utils';

	marked.setOptions({ gfm: true, breaks: true });

	// ── Types ────────────────────────────────────────────────────
	interface Msg {
		role: 'user' | 'assistant';
		content: string;
		streaming: boolean;
		error: boolean;
	}

	// ── State ────────────────────────────────────────────────────
	let input = '';
	let messages: Msg[] = [];
	let streaming = false;
	let conversationId: string = generateId();

	let inputEl:  HTMLTextAreaElement;
	let threadEl: HTMLDivElement;

	// ── React to overlay opening ─────────────────────────────────
	$: if ($overlayOpen) {
		const prefill = $overlayPrefill;
		const autoSend = $overlayAutoSend;

		if (prefill) {
			input = prefill;
			overlayPrefill.set('');
		}

		if (autoSend) {
			overlayAutoSend.set(false);
			// Send after DOM settles
			tick().then(() => send());
		} else {
			tick().then(() => inputEl?.focus());
		}
	}

	// ── Close ────────────────────────────────────────────────────
	function close() {
		overlayOpen.set(false);
	}

	// Only Escape is handled here — Ctrl+Space lives in AiQuickBar
	function handleWindowKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape' && $overlayOpen) close();
	}

	function handleInputKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			send();
		}
	}

	// ── SSE reader (same pattern as /ai page) ────────────────────
	async function* readSSE(res: Response): AsyncGenerator<{ event: string; data: string }> {
		const reader  = res.body!.getReader();
		const decoder = new TextDecoder();
		let buf = '';
		try {
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				buf += decoder.decode(value, { stream: true });
				const blocks = buf.split('\n\n');
				buf = blocks.pop() ?? '';
				for (const block of blocks) {
					let event = 'message';
					let data  = '';
					for (const line of block.split('\n')) {
						if (line.startsWith('event: ')) event = line.slice(7).trim();
						if (line.startsWith('data: '))  data  = line.slice(6).trim();
					}
					if (data) yield { event, data };
				}
			}
		} finally {
			reader.releaseLock();
		}
	}

	// ── Send ─────────────────────────────────────────────────────
	async function send() {
		const text = input.trim();
		if (!text || streaming) return;

		input = '';
		await tick();
		inputEl?.focus();

		const userMsg: Msg = { role: 'user', content: text, streaming: false, error: false };
		let asstMsg:   Msg = { role: 'assistant', content: '', streaming: true, error: false };

		messages = [...messages, userMsg, asstMsg];
		streaming = true;
		await tick();
		scrollBottom();

		try {
			const res = await aiApi.chat({
				model:           $selectedModel,
				message:         text,
				conversation_id: conversationId,
			});

			if (!res.ok) {
				asstMsg = { ...asstMsg, content: `Error ${res.status}: ${res.statusText}`, streaming: false, error: true };
				messages = [...messages.slice(0, -1), asstMsg];
				streaming = false;
				return;
			}

			for await (const { event, data } of readSSE(res)) {
				if (event === 'chunk') {
					try {
						const token = (JSON.parse(data) as { content: string }).content;
						asstMsg = { ...asstMsg, content: asstMsg.content + token };
					} catch { /* skip malformed */ }
					messages = [...messages.slice(0, -1), asstMsg];
					await tick();
					scrollBottom();
				} else if (event === 'done') {
					try {
						const d = JSON.parse(data) as { conversation_id?: string };
						if (d.conversation_id) conversationId = d.conversation_id;
					} catch { /* ok */ }
				} else if (event === 'error') {
					try {
						const d = JSON.parse(data) as { detail?: string };
						asstMsg = { ...asstMsg, content: d.detail ?? 'Unknown error', error: true };
						messages = [...messages.slice(0, -1), asstMsg];
					} catch { /* ok */ }
				}
			}
		} catch (err) {
			asstMsg = { ...asstMsg, content: `Network error: ${String(err)}`, streaming: false, error: true };
			messages = [...messages.slice(0, -1), asstMsg];
		} finally {
			asstMsg = { ...asstMsg, streaming: false };
			messages = [...messages.slice(0, -1), asstMsg];
			streaming = false;
			await tick();
			scrollBottom();
		}
	}

	function scrollBottom() {
		if (threadEl) threadEl.scrollTop = threadEl.scrollHeight;
	}

	function newChat() {
		messages = [];
		conversationId = generateId();
		input = '';
		tick().then(() => inputEl?.focus());
	}

	function autoResize(e: Event) {
		const ta = e.currentTarget as HTMLTextAreaElement;
		ta.style.height = 'auto';
		ta.style.height = Math.min(ta.scrollHeight, 160) + 'px';
	}
</script>

<svelte:window on:keydown={handleWindowKeydown} />

{#if $overlayOpen}
	<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
	<div class="backdrop" on:click={close} aria-hidden="true"></div>

	<div class="overlay" role="dialog" aria-modal="true" aria-label="AI assistant">

		<!-- ── Header ──────────────────────────────────────────── -->
		<div class="overlay-header">
			<div class="header-left">
				<span class="header-icon" aria-hidden="true">
					<MessageSquare size={15} strokeWidth={2} />
				</span>
				<span class="header-title">ollama</span>
				<span class="header-model">/{$selectedModel}</span>
			</div>
			<div class="header-right">
				{#if messages.length > 0}
					<button class="new-btn" on:click={newChat} title="New conversation">new chat</button>
				{/if}
				<span class="header-hint"><kbd>esc</kbd> to close</span>
				<button class="close-btn" on:click={close} aria-label="Close">✕</button>
			</div>
		</div>

		<!-- ── Messages ────────────────────────────────────────── -->
		<div class="messages" bind:this={threadEl} aria-live="polite">
			{#if messages.length === 0}
				<p class="empty-state">No messages yet. Ask something below.</p>
			{:else}
				{#each messages as msg}
					<div class="msg" class:user={msg.role === 'user'} class:assistant={msg.role === 'assistant'} class:error={msg.error}>
						<span class="msg-role">{msg.role === 'user' ? '❯' : 'AI'}</span>
						<div class="msg-body">
							{#if msg.role === 'assistant'}
								{#if msg.content}
									{@html marked.parse(msg.content)}
								{/if}
								{#if msg.streaming}
									<span class="cursor" aria-hidden="true">▋</span>
								{/if}
							{:else}
								{msg.content}
							{/if}
						</div>
					</div>
				{/each}
			{/if}
		</div>

		<!-- ── Input area ──────────────────────────────────────── -->
		<div class="input-area">
			<span class="input-prompt" aria-hidden="true">❯</span>
			<textarea
				bind:this={inputEl}
				bind:value={input}
				class="overlay-input"
				placeholder="ask anything…  (shift+enter for newline)"
				rows="1"
				autocomplete="off"
				spellcheck="false"
				on:keydown={handleInputKeydown}
				on:input={autoResize}
				aria-label="Message input"
			></textarea>
			<button
				class="send-btn"
				type="button"
				on:click={send}
				disabled={!input.trim() || streaming}
				aria-label="Send message"
				title="Send (Enter)"
			>↵</button>
		</div>

	</div>
{/if}

<style>
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(1, 4, 9, 0.72);
		backdrop-filter: blur(2px);
		z-index: 200;
	}

	.overlay {
		position: fixed;
		top: 8vh;
		left: 50%;
		transform: translateX(-50%);
		width: min(720px, 92vw);
		max-height: 76vh;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-top: 2px solid var(--accent3);
		border-radius: var(--radius);
		z-index: 201;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		box-shadow:
			0 0 0 1px color-mix(in srgb, var(--accent3) 12%, transparent),
			0 24px 64px rgba(0, 0, 0, 0.6);
	}

	/* ── Header ──────────────────────────────────────── */
	.overlay-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.55rem 1rem;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-family: var(--font-mono);
		font-size: 0.8rem;
	}

	.header-icon { color: var(--accent3); display: flex; align-items: center; }
	.header-title { color: var(--text0); font-weight: 600; }
	.header-model { color: var(--text2); }

	.header-right {
		display: flex;
		align-items: center;
		gap: 0.6rem;
	}

	.header-hint {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
	}

	.new-btn {
		background: none;
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.65rem;
		padding: 0.15rem 0.45rem;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}
	.new-btn:hover { color: var(--text0); border-color: var(--accent); }

	.close-btn {
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		font-family: var(--font-mono);
		font-size: 0.85rem;
		padding: 0.15rem 0.3rem;
		border-radius: 3px;
		line-height: 1;
		transition: color 0.1s;
	}
	.close-btn:hover { color: var(--text0); }

	/* ── Messages ─────────────────────────────────────── */
	.messages {
		flex: 1;
		overflow-y: auto;
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
		min-height: 140px;
	}

	.empty-state {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text2);
		text-align: center;
		margin: auto;
	}

	.msg {
		display: flex;
		gap: 0.65rem;
		align-items: flex-start;
	}

	.msg-role {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		font-weight: 700;
		flex-shrink: 0;
		padding-top: 0.1rem;
		width: 1.6rem;
	}

	.msg.user .msg-role     { color: var(--accent); }
	.msg.assistant .msg-role { color: var(--accent3); }
	.msg.error .msg-role    { color: var(--red); }

	.msg-body {
		flex: 1;
		min-width: 0;
		font-family: var(--font-mono);
		font-size: 0.82rem;
		line-height: 1.6;
		color: var(--text0);
		word-break: break-word;
	}

	.msg.user .msg-body     { color: var(--text1); }
	.msg.error .msg-body    { color: var(--red); }

	/* Markdown output from marked */
	.msg.assistant .msg-body :global(p)  { margin: 0 0 0.5em; }
	.msg.assistant .msg-body :global(p:last-child) { margin-bottom: 0; }
	.msg.assistant .msg-body :global(code) {
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 3px;
		padding: 0.05em 0.3em;
		font-size: 0.88em;
	}
	.msg.assistant .msg-body :global(pre) {
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 0.65rem;
		overflow-x: auto;
		margin: 0.5em 0;
	}
	.msg.assistant .msg-body :global(pre code) {
		background: none;
		border: none;
		padding: 0;
	}
	.msg.assistant .msg-body :global(ul),
	.msg.assistant .msg-body :global(ol) {
		padding-left: 1.2em;
		margin: 0.3em 0;
	}
	.msg.assistant .msg-body :global(li) { margin: 0.15em 0; }

	/* Streaming cursor */
	@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0; } }
	.cursor {
		display: inline-block;
		color: var(--accent3);
		animation: blink 0.9s step-start infinite;
		font-size: 0.75em;
		vertical-align: middle;
	}

	/* ── Input area ───────────────────────────────────── */
	.input-area {
		display: flex;
		align-items: flex-end;
		gap: 0.5rem;
		padding: 0.65rem 1rem;
		border-top: 1px solid var(--border);
		background: var(--bg2);
		flex-shrink: 0;
	}

	.input-prompt {
		color: var(--accent);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		padding-bottom: 0.45rem;
		flex-shrink: 0;
	}

	.overlay-input {
		flex: 1;
		background: transparent;
		border: none;
		outline: none;
		resize: none;
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.85rem;
		line-height: 1.5;
		caret-color: var(--accent);
		min-height: 1.5em;
		max-height: 10em;
		overflow-y: auto;
	}
	.overlay-input::placeholder { color: var(--text2); }

	.send-btn {
		background: var(--accent3);
		border: none;
		border-radius: 4px;
		color: var(--bg0);
		cursor: pointer;
		font-family: var(--font-mono);
		font-size: 0.95rem;
		font-weight: 700;
		width: 28px; height: 28px;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
		transition: opacity 0.12s;
	}
	.send-btn:disabled             { opacity: 0.25; cursor: not-allowed; }
	.send-btn:not(:disabled):hover { opacity: 0.82; }
</style>
