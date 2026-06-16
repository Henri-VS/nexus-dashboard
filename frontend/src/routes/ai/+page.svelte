<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { get } from 'svelte/store';
	import { page } from '$app/stores';
	import { marked } from 'marked';
	import { selectedModel, nexusSettings, pendingAiContext } from '$lib/stores';
	import { ai as aiApi, resources as resourcesApi } from '$lib/api';
	import EmptyState from '$lib/components/EmptyState.svelte';

	// ── Types ─────────────────────────────────────────────────────

	interface Message {
		id: string;
		role: 'user' | 'assistant';
		content: string;
		streaming: boolean;
		error: boolean;
		timestamp: number;
		ragSources?: string[];
	}

	interface Conversation {
		id: string;
		title: string;
		model: string;
		messages: Message[];
		created_at: number;
	}

	// ── marked setup ──────────────────────────────────────────────
	// gfm + breaks so newlines in assistant output behave naturally.
	marked.setOptions({ gfm: true, breaks: true });

	// ── Constants ─────────────────────────────────────────────────
	const STORAGE_KEY  = 'dashboard-ai-conversations';
	const MAX_STORED   = 50;
	const AI_PAGE_KEY  = 'dashboard_config.ai';
	const LEFT_MIN     = 180;
	const LEFT_MAX     = 480;
	const LEFT_DEFAULT = 260;

	// ── State ─────────────────────────────────────────────────────
	let conversations: Conversation[] = [];
	let activeId:      string | null  = null;
	let models:        string[]       = [];
	let streaming      = false;
	let inputText      = '';
	let ollamaOnline   = false;
	let checking         = true;
	let statsOpen        = false;
	let lastRespMs:       number | null = null;
	let lastTokensPerSec: number | null = null;

	// ── Study mode ────────────────────────────────────────────────
	let studyMode     = false;
	let studySubject  = '';
	let studyModeType = 'context'; // 'context' | 'resources-only'

	// ── Pomodoro ──────────────────────────────────────────────────
	const POMO_WORK  = 1500;
	const POMO_BREAK = 300;
	let pomoPhase    = 0;
	let pomoTimeLeft = POMO_WORK;
	let pomoRunning  = false;
	let pomoInterval: ReturnType<typeof setInterval> | null = null;
	let pomoSessions = 0;

	$: pomoProgress = 1 - (pomoTimeLeft / (pomoPhase === 0 ? POMO_WORK : POMO_BREAK));
	$: pomoDash     = 125.66 * (1 - pomoProgress);
	$: pomoDisplay  = `${String(Math.floor(pomoTimeLeft / 60)).padStart(2, '0')}:${String(pomoTimeLeft % 60).padStart(2, '0')}`;

	$: studySubjects = (() => {
		try {
			const raw = localStorage.getItem('nexus_resources');
			if (!raw) return [];
			const { folders } = JSON.parse(raw) as { folders: Array<{ id: string; name: string; parentId: string | null }> };
			return [...new Set(folders.filter((f) => f.parentId !== null).map((f) => f.name))];
		} catch { return []; }
	})();

	let threadEl: HTMLDivElement;
	let inputEl:  HTMLTextAreaElement;

	// ── Left panel resize ─────────────────────────────────────────
	let leftWidth    = LEFT_DEFAULT;
	let isResizing   = false;
	let resizeStartX = 0;
	let resizeStartW = 0;

	function startResize(e: MouseEvent) {
		isResizing   = true;
		resizeStartX = e.clientX;
		resizeStartW = leftWidth;
		e.preventDefault();
	}

	function onResizeMove(e: MouseEvent) {
		if (!isResizing) return;
		const delta = e.clientX - resizeStartX;
		leftWidth = Math.min(LEFT_MAX, Math.max(LEFT_MIN, resizeStartW + delta));
	}

	function stopResize() {
		if (!isResizing) return;
		isResizing = false;
		saveAiLayout();
	}

	function saveAiLayout() {
		try {
			localStorage.setItem(AI_PAGE_KEY, JSON.stringify({ leftWidth, statsOpen }));
		} catch { /* ignore */ }
	}

	// ── Pomodoro functions ────────────────────────────────────────

	function pomoTick() {
		if (pomoTimeLeft > 0) {
			pomoTimeLeft--;
		} else {
			pomoPhase    = pomoPhase === 0 ? 1 : 0;
			pomoTimeLeft = pomoPhase === 0 ? POMO_WORK : POMO_BREAK;
			if (pomoPhase === 1) {
				pomoSessions++;
				logStudySession();
				sendNtfy('🍅 Pomodoro complete! Take a 5 min break.');
			} else {
				sendNtfy('⏰ Break over! Time to study.');
			}
		}
	}

	function pomoToggle() {
		if (pomoRunning) {
			if (pomoInterval) { clearInterval(pomoInterval); pomoInterval = null; }
			pomoRunning = false;
		} else {
			pomoInterval = setInterval(pomoTick, 1000);
			pomoRunning  = true;
		}
	}

	function pomoReset() {
		if (pomoInterval) { clearInterval(pomoInterval); pomoInterval = null; }
		pomoRunning  = false;
		pomoPhase    = 0;
		pomoTimeLeft = POMO_WORK;
	}

	async function sendNtfy(msg: string) {
		const { ntfy } = $nexusSettings;
		if (!ntfy.topic) return;
		try { await fetch(`${ntfy.server}/${ntfy.topic}`, { method: 'POST', body: msg }); }
		catch { /* ignore */ }
	}

	function logStudySession() {
		try {
			const key      = 'nexus_study_sessions';
			const sessions: Array<{ subject: string; minutes: number; date: number }> =
				JSON.parse(localStorage.getItem(key) ?? '[]');
			sessions.push({ subject: studySubject || 'General', minutes: 25, date: Date.now() });
			localStorage.setItem(key, JSON.stringify(sessions));
		} catch { /* ignore */ }
	}

	onDestroy(() => {
		if (typeof window !== 'undefined') {
			window.removeEventListener('mousemove', onResizeMove);
			window.removeEventListener('mouseup',   stopResize);
		}
		if (pomoInterval) clearInterval(pomoInterval);
	});

	$: active        = conversations.find((c) => c.id === activeId) ?? null;
	$: messages      = active?.messages ?? [];
	$: totalMessages = conversations.reduce((sum, c) => sum + c.messages.length, 0);

	// ── localStorage ─────────────────────────────────────────────

	function loadConvs(): Conversation[] {
		try { return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]'); }
		catch { return []; }
	}

	function saveConvs() {
		localStorage.setItem(
			STORAGE_KEY,
			JSON.stringify(conversations.slice(0, MAX_STORED)),
		);
	}

	// ── Conversation management ───────────────────────────────────

	function newConvObj(): Conversation {
		return {
			id:         crypto.randomUUID(),
			title:      'New conversation',
			model:      $selectedModel,
			messages:   [],
			created_at: Date.now(),
		};
	}

	function createNewChat() {
		// Reuse active conversation if it has no messages yet
		if (active && active.messages.length === 0) {
			tick().then(() => inputEl?.focus());
			return;
		}
		const conv = newConvObj();
		conversations = [conv, ...conversations];
		activeId = conv.id;
		saveConvs();
		tick().then(() => inputEl?.focus());
	}

	function selectConv(id: string) {
		activeId = id;
		tick().then(scrollToBottom);
	}

	function deleteConv(id: string, e: MouseEvent) {
		e.stopPropagation();
		conversations = conversations.filter((c) => c.id !== id);
		if (activeId === id) activeId = conversations[0]?.id ?? null;
		saveConvs();
	}

	// ── SSE stream reader ─────────────────────────────────────────
	// The backend sends:
	//   event: chunk\ndata: {"content":"token"}\n\n
	//   event: done\ndata: {"conversation_id":"..."}\n\n
	//   event: error\ndata: {"detail":"..."}\n\n

	async function* readSSE(
		res: Response,
	): AsyncGenerator<{ event: string; data: string }> {
		const reader  = res.body!.getReader();
		const decoder = new TextDecoder();
		let buf = '';

		try {
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				buf += decoder.decode(value, { stream: true });

				// SSE blocks are double-newline delimited
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

	// ── Send ──────────────────────────────────────────────────────

	async function send() {
		const text = inputText.trim();
		if (!text || streaming) return;

		inputText = '';
		await tick();
		if (inputEl) {
			inputEl.style.height = 'auto';
			inputEl.focus();
		}

		// Ensure there's an active conversation
		if (!activeId) createNewChat();
		const conv = conversations.find((c) => c.id === activeId)!;

		// Auto-title from first message
		if (conv.messages.length === 0) {
			conv.title = text.length > 60 ? text.slice(0, 60) + '…' : text;
		}

		const model = $selectedModel;
		conv.model  = model;

		// Append user message + assistant placeholder in one reactive update
		const userMsg: Message = {
			id: crypto.randomUUID(), role: 'user',
			content: text, streaming: false, error: false, timestamp: Date.now(),
		};
		let asstMsg: Message = {
			id: crypto.randomUUID(), role: 'assistant',
			content: '', streaming: true, error: false, timestamp: Date.now(),
		};
		conv.messages = [...conv.messages, userMsg, asstMsg];
		conversations = [...conversations];
		streaming = true;

		await tick();
		scrollToBottom();

		let streamStart    = 0;   // wall-clock before for-await → total response ms
		let firstChunkTime = 0;   // wall-clock on first token → rate denominator
		let tokenCount     = 0;

		// Inject study context from ChromaDB when study mode is active
		let messageToSend = text;
		if (studyMode && studySubject) {
			try {
				const result = await resourcesApi.search(text, studySubject, 3);
				if (result?.chunks?.length) {
					const ctx = result.chunks.map((c) => c.content).join('\n---\n');
					messageToSend = `Study context (${studySubject}):\n${ctx}\n\n---\n${studyModeType === 'resources-only' ? '[Answer only using the context above]\n' : ''}Question: ${text}`;
				}
			} catch { /* fallback to original text */ }
		}

		try {
			const res = await aiApi.chat({
				model,
				message:         messageToSend,
				conversation_id: conv.id,
			});

			if (!res.ok) {
				asstMsg.content   = `Backend error ${res.status}: ${res.statusText}`;
				asstMsg.error     = true;
				asstMsg.streaming = false;
				conversations = [...conversations];
				saveConvs();
				return;
			}

			streamStart    = Date.now();
			firstChunkTime = 0;
			tokenCount     = 0;

			for await (const { event, data } of readSSE(res)) {
				if (event === 'chunk') {
					try {
						const token = (JSON.parse(data) as { content: string }).content;
						asstMsg = { ...asstMsg, content: asstMsg.content + token };
						if (firstChunkTime === 0) firstChunkTime = Date.now();
						tokenCount++;
					} catch { /* skip malformed chunk */ }
					conv.messages = [...conv.messages.slice(0, -1), asstMsg];
					conversations = [...conversations];
					scrollToBottom();

				} else if (event === 'done') {
					const endTime     = Date.now();
					const tokenWindow = endTime - firstChunkTime;
					lastRespMs        = endTime - streamStart;
					lastTokensPerSec  = tokenWindow > 0 && firstChunkTime > 0
						? Math.round((tokenCount / (tokenWindow / 1000)) * 10) / 10
						: null;
					let ragSources: string[] = [];
					try {
						const doneData = JSON.parse(data) as { rag_sources?: string[] };
						ragSources = doneData.rag_sources ?? [];
					} catch { /* ignore */ }
					asstMsg = {
						...asstMsg,
						streaming: false,
						...(ragSources.length ? { ragSources } : {}),
					};
					conv.messages = [...conv.messages.slice(0, -1), asstMsg];
					conversations = [...conversations];
					saveConvs();

				} else if (event === 'error') {
					try { asstMsg = { ...asstMsg, content: (JSON.parse(data) as { detail: string }).detail, error: true, streaming: false }; }
					catch { asstMsg = { ...asstMsg, content: data, error: true, streaming: false }; }
					conv.messages = [...conv.messages.slice(0, -1), asstMsg];
					conversations = [...conversations];
					saveConvs();
				}
			}

		} catch {
			asstMsg = { ...asstMsg, content: 'Could not reach the backend. Is the API server running?', error: true, streaming: false };
			conv.messages = [...conv.messages.slice(0, -1), asstMsg];
			ollamaOnline  = false;
			conversations = [...conversations];
			saveConvs();

		} finally {
			streaming = false;
			if (asstMsg.streaming) {
				asstMsg = { ...asstMsg, streaming: false };
				conv.messages = [...conv.messages.slice(0, -1), asstMsg];
				conversations = [...conversations];
			}
		}
	}

	// ── Input helpers ─────────────────────────────────────────────

	function handleKeydown(e: KeyboardEvent) {
		if (e.ctrlKey && e.key === 'Enter') {
			e.preventDefault();
			send();
		}
	}

	function autoGrow(el: HTMLTextAreaElement) {
		el.style.height = 'auto';
		// Cap at ~5 lines (120px)
		el.style.height = Math.min(el.scrollHeight, 120) + 'px';
	}

	function scrollToBottom() {
		if (threadEl) threadEl.scrollTop = threadEl.scrollHeight;
	}

	// ── Markdown ──────────────────────────────────────────────────

	function renderMd(content: string): string {
		if (!content) return '';
		return marked.parse(content) as string;
	}

	// ── Time ──────────────────────────────────────────────────────

	function relTime(ts: number): string {
		const d = Date.now() - ts;
		const m = Math.floor(d / 60_000);
		if (m <  1)  return 'just now';
		if (m < 60)  return `${m}m ago`;
		const h = Math.floor(m / 60);
		if (h < 24)  return `${h}h ago`;
		return `${Math.floor(h / 24)}d ago`;
	}

	// ── Mount ─────────────────────────────────────────────────────

	onMount(async () => {
		// Load layout preferences
		try {
			const raw = localStorage.getItem(AI_PAGE_KEY);
			if (raw) {
				const cfg = JSON.parse(raw);
				if (typeof cfg.leftWidth === 'number') leftWidth = Math.min(LEFT_MAX, Math.max(LEFT_MIN, cfg.leftWidth));
				if (typeof cfg.statsOpen === 'boolean') statsOpen = cfg.statsOpen;
			}
		} catch { /* ignore */ }

		window.addEventListener('mousemove', onResizeMove);
		window.addEventListener('mouseup',   stopResize);

		// Restore history
		conversations = loadConvs();
		activeId = conversations[0]?.id ?? null;

		// Health + models (parallel)
		const [health, modelsRes] = await Promise.all([
			aiApi.health(),
			aiApi.models(),
		]);

		ollamaOnline = health?.status === 'online';
		checking     = false;

		if (modelsRes?.models?.length) {
			models = modelsRes.models.map((m) => m.name);
			if (!models.includes($selectedModel)) selectedModel.set(models[0]);
		} else {
			models = [$selectedModel];  // API failed → keep current selection visible
		}

		// Handle ?q= navigation from quick-bar / overlay
		const params = get(page).url.searchParams;
		const q      = params.get('q');
		const qModel = params.get('model');

		if (qModel && models.includes(qModel)) selectedModel.set(qModel);

		if (q) {
			createNewChat();
			await tick();
			inputText = q;
			await send();
		} else if (!activeId) {
			createNewChat();
		}

		// Activate study mode if resources page sent context
		const pending = get(pendingAiContext);
		if (pending) {
			pendingAiContext.set(null);
			studyMode    = true;
			studySubject = pending.subject || '';
			if (!activeId) createNewChat();
			await tick();
			inputText = `I've loaded "${pending.filename}" into study mode. Summarise the key concepts and help me understand the material.`;
		}

		await tick();
		scrollToBottom();
		inputEl?.focus();
	});
</script>

<svelte:head>
	<title>Nexus — AI</title>
</svelte:head>

<div class="ai-page">

	<!-- ── Left panel: conversation list + model selector ──── -->
	<aside class="left-panel" style="width: {leftWidth}px">

		<button class="new-chat-btn" on:click={createNewChat}>
			+ new chat
		</button>

		<div
			class="conv-list"
			role="list"
			tabindex="0"
			on:keydown={(e) => {
				if (e.key === 'Enter' && activeId) selectConv(activeId);
			}}
		>
			{#each conversations as conv (conv.id)}
				<!-- svelte-ignore a11y-click-events-have-key-events -->
				<div
					class="conv-item"
					class:active={conv.id === activeId}
					role="listitem"
					on:click={() => selectConv(conv.id)}
				>
					<div class="conv-body">
						<span class="conv-title">{conv.title}</span>
						<div class="conv-sub">
							<span class="conv-model">{conv.model}</span>
							<span class="conv-time">{relTime(conv.created_at)}</span>
						</div>
					</div>
					<button
						class="del-btn"
						on:click|stopPropagation={(e) => deleteConv(conv.id, e)}
						aria-label="Delete conversation"
						title="Delete"
					>✕</button>
				</div>
			{/each}

			{#if conversations.length === 0}
				<p class="no-convs">No conversations yet</p>
			{/if}
		</div>

		<!-- Model selector -->
		<div class="model-footer">
			<div class="model-row">
				<span class="model-label">model</span>
				<span
					class="status-dot"
					class:dot-online={ollamaOnline}
					class:dot-checking={checking}
					class:dot-offline={!ollamaOnline && !checking}
					title={checking ? 'checking…' : ollamaOnline ? 'Ollama online' : 'Ollama offline'}
				></span>
			</div>

			{#if models.length}
				<select
					class="model-select"
					bind:value={$selectedModel}
					aria-label="Ollama model"
				>
					{#each models as m}
						<option value={m}>{m}</option>
					{/each}
				</select>
			{:else}
				<span class="model-status">
					{checking ? 'connecting…' : '⚠ ollama offline'}
				</span>
			{/if}

			<!-- Study mode controls -->
			<div class="study-row">
				<span class="model-label">study mode</span>
				<!-- svelte-ignore a11y-click-events-have-key-events -->
				<button
					class="study-toggle"
					class:study-on={studyMode}
					on:click={() => { studyMode = !studyMode; }}
					role="switch"
					aria-checked={studyMode}
					title={studyMode ? 'Disable study mode' : 'Enable study mode'}
				>
					<span class="study-thumb"></span>
				</button>
			</div>

			{#if studyMode}
				<select class="model-select" bind:value={studySubject} aria-label="Study subject">
					<option value="">— any subject —</option>
					{#each studySubjects as s}
						<option value={s}>{s}</option>
					{/each}
				</select>
				<select class="model-select" bind:value={studyModeType} aria-label="Study mode type">
					<option value="context">Use context + knowledge</option>
					<option value="resources-only">Resources only</option>
				</select>

				<!-- Pomodoro -->
				<div class="pomo-panel">
					<div class="pomo-header">
						<span class="pomo-label">🍅 pomodoro</span>
						<span class="pomo-sessions">{pomoSessions} sessions</span>
					</div>
					<div class="pomo-ring-row">
						<svg class="pomo-ring" viewBox="0 0 48 48">
							<circle class="pomo-track" cx="24" cy="24" r="20" />
							<circle
								class="pomo-fill"
								cx="24" cy="24" r="20"
								stroke-dasharray="125.66"
								stroke-dashoffset={pomoDash}
								class:pomo-break={pomoPhase === 1}
							/>
						</svg>
						<div class="pomo-time-col">
							<span class="pomo-time">{pomoDisplay}</span>
							<span class="pomo-phase">{pomoPhase === 0 ? 'work' : 'break'}</span>
						</div>
					</div>
					<div class="pomo-btns">
						<button class="pomo-btn" on:click={pomoToggle}>
							{pomoRunning ? '⏸' : '▶'}
						</button>
						<button class="pomo-btn pomo-reset" on:click={pomoReset} title="Reset">↺</button>
					</div>
				</div>
			{/if}
		</div>
	</aside>

	<!-- ── Left-panel resize handle ─────────────────────────── -->
	<div
		class="panel-resize"
		class:resizing={isResizing}
		role="separator"
		aria-label="Resize conversation panel"
		aria-orientation="vertical"
		on:mousedown={startResize}
	></div>

	<!-- ── Right panel: thread + input bar ──────────────────── -->
	<div class="right-panel">

		<!-- Stats toggle -->
		<button
			class="stats-toggle"
			class:open={statsOpen}
			on:click={() => { statsOpen = !statsOpen; saveAiLayout(); }}
			aria-label={statsOpen ? 'Close stats' : 'Open stats'}
			title="Chat stats"
		>{statsOpen ? '‹' : '›'}</button>

		<!-- Stats drawer -->
		<div class="stats-drawer" class:open={statsOpen} aria-hidden={!statsOpen}>
			<div class="srow"><span class="sk">MODEL</span><span class="sv">{$selectedModel}</span></div>
			<div class="srow">
				<span class="sk">STATUS</span>
				<span class="sv sdot-row">
					<span class="sdot" class:sdot-on={ollamaOnline}></span>
					{ollamaOnline ? 'online' : 'offline'}
				</span>
			</div>
			<div class="srow"><span class="sk">LAST RESP</span><span class="sv">{lastRespMs !== null ? `${lastRespMs}ms` : '—'}</span></div>
			<div class="srow"><span class="sk">TOKENS/SEC</span><span class="sv">{lastTokensPerSec !== null ? `${lastTokensPerSec} t/s` : '—'}</span></div>
			<div class="srow"><span class="sk">CONVERSATIONS</span><span class="sv">{conversations.length}</span></div>
			<div class="srow"><span class="sk">MESSAGES</span><span class="sv">{totalMessages}</span></div>
		</div>

		<!-- Study mode banner -->
		{#if studyMode}
			<div class="study-banner">
				<span class="study-banner-dot"></span>
				<span class="study-banner-text">
					Study mode active{studySubject ? ` · ${studySubject}` : ''} · {studyModeType === 'resources-only' ? 'resources only' : 'context + knowledge'}
				</span>
				<button class="study-banner-close" on:click={() => studyMode = false}>✕</button>
			</div>
		{/if}

		<!-- Message thread -->
		<div class="thread" bind:this={threadEl} aria-label="Conversation messages">

			{#if messages.length === 0}
				{#if !ollamaOnline && !checking}
					<!-- Offline state -->
					<EmptyState
						variant="unreachable"
						size="large"
						title="AI Assistant is offline"
						body="No AI backend is configured. Nexus supports Ollama, OpenAI-compatible APIs, and local LLM servers."
						primaryAction="Configure in Settings"
						primaryHref="/settings"
						secondaryAction="View docs"
					/>
					<div class="quickstart-callout">
						<div class="qs-header">QUICK START</div>
						<pre class="qs-body">$ ollama pull llama3
$ ollama serve
# then configure endpoint below</pre>
					</div>
				{:else}
					<!-- Empty / welcome state -->
					<div class="empty-state">
						<div class="empty-glyph" aria-hidden="true">⬡</div>
						<p class="empty-heading">Ask your homelab anything</p>
						<p class="empty-sub">
							Model: <span class="empty-model">{$selectedModel}</span>
							&nbsp;·&nbsp;
							<kbd>ctrl</kbd>+<kbd>enter</kbd> to send
						</p>
					</div>
				{/if}

			{:else}
				{#each messages as msg (msg.id)}
					<div
						class="msg-wrap"
						class:msg-user={msg.role === 'user'}
						class:msg-asst={msg.role === 'assistant'}
					>
						{#if msg.role === 'user'}
							<div class="bubble bubble-user">
								<p class="user-text">{msg.content}</p>
							</div>
						{:else}
							<div class="bubble bubble-asst" class:bubble-error={msg.error}>
								{#if msg.content || msg.streaming}
									<div class="md-body">
										{@html renderMd(msg.content)}
										{#if msg.streaming}
											<span class="cursor" aria-hidden="true"></span>
										{/if}
									</div>
								{/if}
							</div>
							{#if msg.ragSources && msg.ragSources.length > 0}
								<div class="rag-sources">
									<span class="rag-icon">⌗</span>
									Based on {msg.ragSources.length} source{msg.ragSources.length > 1 ? 's' : ''}:
									{msg.ragSources.slice(0, 3).join(', ')}{msg.ragSources.length > 3 ? ` +${msg.ragSources.length - 3} more` : ''}
								</div>
							{/if}
						{/if}
						<span class="msg-time">{relTime(msg.timestamp)}</span>
					</div>
				{/each}
			{/if}
		</div>

		<!-- Input bar — pinned to bottom via flex column -->
		<div class="input-bar">
			<span class="prompt-char" aria-hidden="true">❯</span>

			<textarea
				bind:this={inputEl}
				bind:value={inputText}
				class="input-field"
				placeholder="Ask anything… (ctrl+enter to send, enter for newline)"
				rows="1"
				autocomplete="off"
				spellcheck="false"
				disabled={streaming}
				on:keydown={handleKeydown}
				on:input={(e) => autoGrow(e.currentTarget)}
				aria-label="Message input"
			></textarea>

			<button
				class="send-btn"
				on:click={send}
				disabled={streaming || !inputText.trim()}
				aria-label="Send (Ctrl+Enter)"
				title="Send (Ctrl+Enter)"
			>
				{#if streaming}
					<span class="send-spinner" aria-hidden="true"></span>
				{:else}
					↵
				{/if}
			</button>
		</div>
	</div>

</div>

<style>
	/*
	  The layout's .content has padding: 1.5rem and overflow-y: auto.
	  We escape that padding with negative margins so the AI page is
	  edge-to-edge, and handle all scrolling internally (thread only).
	*/
	.ai-page {
		display: flex;
		margin: -1.5rem;
		width:  calc(100% + 3rem);
		height: calc(100% + 3rem);
		overflow: hidden;
		background: var(--bg0);
	}

	/* ── Left panel ─────────────────────────────────────────── */
	.left-panel {
		/* width set via style binding */
		flex-shrink: 0;
		background: var(--bg1);
		border-right: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	/* ── Panel resize handle ─────────────────────────────────── */
	.panel-resize {
		width: 4px;
		flex-shrink: 0;
		background: var(--border);
		cursor: col-resize;
		transition: background 0.12s;
		position: relative;
		z-index: 10;
	}

	.panel-resize:hover,
	.panel-resize.resizing {
		background: var(--accent3);
	}

	.new-chat-btn {
		margin: 0.75rem;
		padding: 0.45rem 0.75rem;
		background: none;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.78rem;
		cursor: pointer;
		text-align: left;
		transition: border-color 0.12s, color 0.12s, background 0.12s;
		flex-shrink: 0;
	}

	.new-chat-btn:hover {
		border-color: var(--accent3);
		color: var(--accent3);
		background: color-mix(in srgb, var(--accent3) 6%, transparent);
	}

	/* Conversation list */
	.conv-list {
		flex: 1;
		overflow-y: auto;
		padding: 0 0.4rem 0.4rem;
	}

	.conv-item {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.45rem 0.5rem;
		border-radius: var(--radius);
		cursor: pointer;
		transition: background 0.1s;
		position: relative;
		outline: none;
	}

	.conv-item:hover   { background: var(--bg2); }
	.conv-item.active  { background: color-mix(in srgb, var(--accent3) 10%, transparent); }
	.conv-item:focus-visible { outline: 1px solid var(--accent3); }

	.conv-body {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}

	.conv-title {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text0);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		display: block;
	}

	.conv-item.active .conv-title { color: var(--accent3); }

	.conv-sub {
		display: flex;
		gap: 0.4rem;
		align-items: center;
	}

	.conv-model {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 80px;
	}

	.conv-time {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		flex-shrink: 0;
	}

	/* Delete button — hidden until hover */
	.del-btn {
		background: none;
		border: none;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		padding: 0.1rem 0.25rem;
		border-radius: 3px;
		cursor: pointer;
		opacity: 0;
		flex-shrink: 0;
		transition: opacity 0.1s, color 0.1s;
	}

	.conv-item:hover .del-btn { opacity: 1; }
	.del-btn:hover { color: var(--red); }

	.no-convs {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text2);
		padding: 0.75rem 0.5rem;
	}

	/* Model footer */
	.model-footer {
		border-top: 1px solid var(--border);
		padding: 0.65rem 0.75rem;
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		flex-shrink: 0;
	}

	.model-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.model-label {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text2);
	}

	.status-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--text2);
		transition: background 0.3s;
	}

	.dot-online   { background: var(--green);  }
	.dot-checking { background: var(--yellow); }
	.dot-offline  { background: var(--red);    }

	.model-select {
		width: 100%;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.78rem;
		padding: 0.3rem 0.5rem;
		cursor: pointer;
	}

	.model-select:focus {
		outline: 1px solid var(--accent3);
		border-color: var(--accent3);
	}

	.model-status {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--red);
	}

	/* ── Right panel ────────────────────────────────────────── */
	.right-panel {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		position: relative;
	}

	/* Thread — flex 1, scrolls vertically */
	.thread {
		flex: 1;
		overflow-y: auto;
		padding: 1.25rem 1rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	/* ── Offline banner ─────────────────────────────────────── */
	/* ── Quickstart callout (below offline EmptyState) ─────────── */
	.quickstart-callout {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-left: 3px solid var(--yellow);
		border-radius: var(--radius);
		padding: 14px 18px;
		max-width: 380px;
		margin: 0 auto;
	}

	.qs-header {
		font-family: var(--font-mono);
		font-size: 0.625rem;
		font-weight: 600;
		color: var(--yellow);
		letter-spacing: 1px;
		margin-bottom: 8px;
	}

	.qs-body {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text1);
		line-height: 1.7;
		white-space: pre;
		background: none;
		border: none;
		padding: 0;
	}

	/* ── Empty / welcome state ──────────────────────────────── */
	.empty-state {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		flex: 1;
		gap: 0.5rem;
		text-align: center;
		padding: 2rem;
	}

	.empty-glyph {
		font-size: 2.5rem;
		color: var(--text2);
		line-height: 1;
		margin-bottom: 0.25rem;
	}

	.empty-heading {
		font-family: var(--font-mono);
		font-size: 0.95rem;
		color: var(--text1);
	}

	.empty-sub {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text2);
	}

	.empty-model { color: var(--accent3); }

	/* ── Message layout ─────────────────────────────────────── */
	.msg-wrap {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		max-width: 78%;
	}

	.msg-wrap.msg-user { align-self: flex-end; align-items: flex-end; }
	.msg-wrap.msg-asst { align-self: flex-start; align-items: flex-start; }

	/* Bubbles */
	.bubble {
		border-radius: var(--radius);
		padding: 0.65rem 0.9rem;
		font-family: var(--font-mono);
		font-size: 0.84rem;
		line-height: 1.65;
		word-break: break-word;
	}

	.bubble-user {
		background: color-mix(in srgb, var(--accent3) 15%, var(--bg2));
		border: 1px solid color-mix(in srgb, var(--accent3) 30%, var(--border));
		color: var(--text0);
	}

	.user-text { margin: 0; white-space: pre-wrap; }

	.bubble-asst {
		background: var(--bg1);
		border: 1px solid var(--border);
		color: var(--text0);
	}

	.bubble-error {
		border-color: color-mix(in srgb, var(--red) 40%, var(--border));
		background: color-mix(in srgb, var(--red) 6%, var(--bg1));
	}

	.msg-time {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		padding: 0 0.25rem;
	}

	/* ── Blinking cursor ────────────────────────────────────── */
	@keyframes blink {
		0%, 100% { opacity: 1; }
		50%       { opacity: 0; }
	}

	.cursor {
		display: inline-block;
		width: 7px;
		height: 0.9em;
		background: var(--accent);
		vertical-align: text-bottom;
		margin-left: 1px;
		animation: blink 1s step-end infinite;
	}

	/* ── Input bar ──────────────────────────────────────────── */
	.input-bar {
		display: flex;
		align-items: flex-end;
		gap: 0.6rem;
		padding: 0.75rem 1rem;
		border-top: 1px solid var(--border);
		background: var(--bg1);
		flex-shrink: 0;
	}

	.prompt-char {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--accent);
		padding-bottom: 0.55rem;
		flex-shrink: 0;
	}

	.input-field {
		flex: 1;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.84rem;
		line-height: 1.5;
		padding: 0.45rem 0.7rem;
		resize: none;
		outline: none;
		caret-color: var(--accent);
		transition: border-color 0.12s;
		min-height: 36px;
		max-height: 120px;
		overflow-y: auto;
	}

	.input-field:focus    { border-color: var(--accent3); }
	.input-field:disabled { opacity: 0.5; cursor: not-allowed; }
	.input-field::placeholder { color: var(--text2); }

	.send-btn {
		width: 36px;
		height: 36px;
		flex-shrink: 0;
		background: var(--accent3);
		border: none;
		border-radius: var(--radius);
		color: var(--bg0);
		font-family: var(--font-mono);
		font-size: 1rem;
		font-weight: 700;
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
		transition: opacity 0.12s;
	}

	.send-btn:disabled          { opacity: 0.25; cursor: not-allowed; }
	.send-btn:not(:disabled):hover { opacity: 0.82; }

	@keyframes spin {
		to { transform: rotate(360deg); }
	}

	.send-spinner {
		display: inline-block;
		width: 14px;
		height: 14px;
		border: 2px solid rgba(255,255,255,0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 0.7s linear infinite;
	}

	/* ── Markdown body styles (:global — rendered via marked) ── */

	:global(.md-body) {
		font-family: var(--font-mono);
		font-size: 0.84rem;
		line-height: 1.7;
		color: var(--text0);
		overflow-wrap: break-word;
	}

	:global(.md-body p) {
		margin: 0 0 0.6em;
	}
	:global(.md-body p:last-child) { margin-bottom: 0; }

	:global(.md-body h1),
	:global(.md-body h2),
	:global(.md-body h3),
	:global(.md-body h4) {
		font-family: var(--font-mono);
		font-weight: 700;
		color: var(--text0);
		margin: 0.9em 0 0.4em;
		line-height: 1.3;
	}
	:global(.md-body h1) { font-size: 1.15em; color: var(--accent3); }
	:global(.md-body h2) { font-size: 1.05em; color: var(--accent2); }
	:global(.md-body h3) { font-size: 0.95em; }
	:global(.md-body h4) { font-size: 0.9em;  color: var(--text1); }

	:global(.md-body ul),
	:global(.md-body ol) {
		margin: 0.4em 0 0.6em 1.25em;
		display: flex;
		flex-direction: column;
		gap: 0.15em;
	}

	:global(.md-body li) { line-height: 1.6; }

	:global(.md-body blockquote) {
		border-left: 3px solid var(--accent3);
		margin: 0.6em 0;
		padding: 0.3em 0.75em;
		color: var(--text1);
		background: color-mix(in srgb, var(--accent3) 5%, transparent);
		border-radius: 0 var(--radius) var(--radius) 0;
	}

	:global(.md-body a) {
		color: var(--accent2);
		text-decoration: underline;
		text-underline-offset: 2px;
	}

	:global(.md-body strong) { color: var(--text0); font-weight: 700; }
	:global(.md-body em)     { font-style: italic; color: var(--text1); }

	:global(.md-body hr) {
		border: none;
		border-top: 1px solid var(--border);
		margin: 0.8em 0;
	}

	/* Inline code */
	:global(.md-body code) {
		font-family: var(--font-mono);
		font-size: 0.88em;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 3px;
		padding: 0.05em 0.3em;
		color: var(--accent4);
	}

	/* Code blocks */
	:global(.md-body pre) {
		background: var(--bg0);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 0.75rem 1rem;
		overflow-x: auto;
		margin: 0.6em 0;
		position: relative;
	}

	:global(.md-body pre code) {
		/* Reset inline code styles inside a block */
		background: none;
		border: none;
		padding: 0;
		border-radius: 0;
		color: var(--text0);
		font-size: 0.82rem;
		line-height: 1.6;
	}

	/* Tables */
	:global(.md-body table) {
		border-collapse: collapse;
		width: 100%;
		margin: 0.6em 0;
		font-size: 0.82rem;
	}

	:global(.md-body th),
	:global(.md-body td) {
		border: 1px solid var(--border);
		padding: 0.3em 0.6em;
		text-align: left;
	}

	:global(.md-body th) {
		background: var(--bg2);
		color: var(--text1);
		font-weight: 700;
	}

	:global(.md-body td) { color: var(--text0); }

	:global(.md-body tr:nth-child(even) td) {
		background: color-mix(in srgb, var(--bg2) 40%, transparent);
	}

	/* ── Stats toggle button ─────────────────────────────────── */
	.stats-toggle {
		position: absolute;
		right: 0;
		top: 50%;
		transform: translateY(-50%);
		z-index: 20;
		width: 20px;
		height: 48px;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-right: none;
		border-radius: var(--radius) 0 0 var(--radius);
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.9rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: right 0.2s ease, color 0.12s;
		padding: 0;
	}

	.stats-toggle.open      { right: 220px; color: var(--accent3); }
	.stats-toggle:hover     { color: var(--accent3); }

	/* ── Stats drawer ────────────────────────────────────────── */
	.stats-drawer {
		position: absolute;
		right: 0;
		top: 0;
		bottom: 0;
		width: 220px;
		transform: translateX(100%);
		transition: transform 0.2s ease;
		background: var(--bg1);
		border-left: 1px solid var(--border);
		overflow-y: auto;
		z-index: 15;
		display: flex;
		flex-direction: column;
		padding: 1.25rem 0.85rem;
		gap: 1rem;
	}

	.stats-drawer.open { transform: translateX(0); }

	.srow { display: flex; flex-direction: column; gap: 0.2rem; }

	.sk {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text2);
	}

	.sv {
		font-family: var(--font-mono);
		font-size: 0.8rem;
		color: var(--text0);
		word-break: break-all;
	}

	.sdot-row { display: flex; align-items: center; gap: 0.35rem; }

	.sdot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--red);
		flex-shrink: 0;
	}

	.sdot.sdot-on { background: var(--green); }

	/* ── Study mode controls ─────────────────────────────────── */
	.study-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-top: 0.25rem;
	}

	.study-toggle {
		width: 32px;
		height: 18px;
		border-radius: 9px;
		border: 1px solid var(--border);
		background: var(--bg2);
		padding: 2px;
		cursor: pointer;
		display: flex;
		align-items: center;
		transition: background 0.2s, border-color 0.2s;
		position: relative;
	}

	.study-toggle.study-on {
		background: color-mix(in srgb, var(--yellow) 30%, var(--bg2));
		border-color: var(--yellow);
	}

	.study-thumb {
		width: 12px;
		height: 12px;
		border-radius: 50%;
		background: var(--text2);
		transition: transform 0.2s, background 0.2s;
	}

	.study-toggle.study-on .study-thumb {
		transform: translateX(14px);
		background: var(--yellow);
	}

	/* ── Study banner ────────────────────────────────────────── */
	.study-banner {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.4rem 0.85rem;
		background: color-mix(in srgb, var(--yellow) 8%, var(--bg1));
		border-bottom: 1px solid color-mix(in srgb, var(--yellow) 25%, var(--border));
		flex-shrink: 0;
	}

	.study-banner-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: var(--yellow);
		flex-shrink: 0;
		animation: pulse-dot 2s ease-in-out infinite;
	}

	@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:0.4} }

	.study-banner-text {
		flex: 1;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--yellow);
	}

	.study-banner-close {
		background: none;
		border: none;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.7rem;
		cursor: pointer;
		padding: 0.1rem 0.25rem;
		border-radius: 3px;
		transition: color 0.1s;
	}
	.study-banner-close:hover { color: var(--red); }

	/* ── Pomodoro panel ──────────────────────────────────────── */
	.pomo-panel {
		background: var(--bg0);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 0.6rem 0.65rem;
		display: flex;
		flex-direction: column;
		gap: 0.45rem;
		margin-top: 0.25rem;
	}

	.pomo-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.pomo-label {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		text-transform: uppercase;
		letter-spacing: 0.07em;
		color: var(--text2);
	}

	.pomo-sessions {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--accent3);
	}

	.pomo-ring-row {
		display: flex;
		align-items: center;
		gap: 0.65rem;
	}

	.pomo-ring {
		width: 52px;
		height: 52px;
		flex-shrink: 0;
		transform: rotate(-90deg);
	}

	.pomo-track { fill: none; stroke: var(--bg2); stroke-width: 3; }

	.pomo-fill {
		fill: none;
		stroke: var(--accent3);
		stroke-width: 3;
		stroke-linecap: round;
		transition: stroke-dashoffset 0.9s linear;
	}

	.pomo-fill.pomo-break { stroke: var(--green); }

	.pomo-time-col {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}

	.pomo-time {
		font-family: var(--font-mono);
		font-size: 1.1rem;
		font-weight: 700;
		color: var(--text0);
		line-height: 1;
	}

	.pomo-phase {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text2);
	}

	.pomo-btns {
		display: flex;
		gap: 0.35rem;
	}

	.pomo-btn {
		flex: 1;
		padding: 0.25rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-size: 0.85rem;
		cursor: pointer;
		transition: border-color 0.1s, background 0.1s;
	}
	.pomo-btn:hover { border-color: var(--accent3); background: color-mix(in srgb, var(--accent3) 8%, var(--bg2)); }
	.pomo-reset { flex: 0 0 32px; color: var(--text2); font-size: 1rem; }
	.pomo-reset:hover { color: var(--red); border-color: var(--red); }

	@media (max-width: 768px) {
		.left-panel  { display: none; }
		.panel-resize { display: none; }
	}

	/* ── RAG source attribution ──────────────────────────────── */
	.rag-sources {
		margin-top: 8px;
		padding: 5px 10px;
		background: color-mix(in srgb, var(--accent2) 8%, var(--bg1));
		border: 1px solid color-mix(in srgb, var(--accent2) 25%, var(--border));
		border-radius: 5px;
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--accent2);
		line-height: 1.5;
	}

	.rag-icon {
		margin-right: 4px;
		opacity: 0.7;
	}
</style>
