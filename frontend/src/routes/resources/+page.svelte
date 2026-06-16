<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { marked } from 'marked';
	import {
		Upload,
		FolderPlus,
		FolderOpen,
		Folder,
		FileText,
		File,
		Image,
		Download,
		ChevronRight,
		ChevronDown,
		Cpu,
		CheckCircle,
		XCircle,
		Loader,
		BookOpen,
		RotateCcw,
		Library,
	} from '@lucide/svelte';
	import { selectedModel } from '$lib/stores';
	import { pendingAiContext } from '$lib/stores';
	import { resources as resourcesApi, ai as aiApi } from '$lib/api';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import { generateId } from '$lib/utils';

	marked.setOptions({ gfm: true, breaks: true });

	// ── Types ─────────────────────────────────────────────────────────────────

	interface ResourceFolder {
		id: string;
		name: string;
		parentId: string | null;
	}

	interface Flashcard {
		front: string;
		back: string;
	}

	interface ResourceFile {
		id: string;
		name: string;
		content: string;
		type: string;
		size: number;
		uploadDate: number;
		folderId: string;
		processingStatus: 'none' | 'processing' | 'ready' | 'failed';
		extractedText?: string;
		flashcards?: Flashcard[];
		sessionOnly?: boolean; // not persisted — file too large for localStorage
	}

	interface PaperQuestion {
		text: string;
		userAnswer: string;
		feedback: string;
		correct: boolean | null;
	}

	type ViewMode = 'preview' | 'flashcards' | 'pastpaper';

	// ── Storage ───────────────────────────────────────────────────────────────

	const STORAGE_KEY = 'nexus_resources';
	const PAGE_KEY    = 'dashboard_config.resources';

	const DEFAULT_FOLDERS: ResourceFolder[] = [];

	let folders: ResourceFolder[] = [];
	let files: ResourceFile[] = [];

	function load() {
		if (!browser) return;
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (raw) {
				const data = JSON.parse(raw);
				folders = data.folders ?? DEFAULT_FOLDERS;
				files   = data.files   ?? [];
			} else {
				folders = [...DEFAULT_FOLDERS];
				files   = [];
			}
		} catch {
			folders = [...DEFAULT_FOLDERS];
			files   = [];
		}
	}

	function save() {
		if (!browser) return;
		// Never persist session-only files (too large for localStorage)
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify({ folders, files: files.filter((f) => !f.sessionOnly) }));
		} catch { /* full */ }
	}

	// ── Upload toast ──────────────────────────────────────────────────────────

	let toastMsg = '';
	let toastTimer: ReturnType<typeof setTimeout> | null = null;

	function showToast(msg: string) {
		toastMsg = msg;
		if (toastTimer) clearTimeout(toastTimer);
		toastTimer = setTimeout(() => { toastMsg = ''; }, 7000);
	}

	// ── Tree state ────────────────────────────────────────────────────────────

	let openFolders = new Set<string>(['s1', 's2']);
	let selectedFileId: string | null = null;
	let activeFolderId: string | null = null;

	$: selectedFile = files.find((f) => f.id === selectedFileId) ?? null;
	$: semesterFolders = folders.filter((f) => f.parentId === null);

	function getSubFolders(parentId: string) {
		return folders.filter((f) => f.parentId === parentId);
	}

	function getFolderFiles(folderId: string) {
		return files.filter((f) => f.folderId === folderId);
	}

	function toggleFolder(id: string) {
		const next = new Set(openFolders);
		if (next.has(id)) next.delete(id); else next.add(id);
		openFolders = next;
	}

	function selectFile(id: string) {
		if (selectedFileId === id) return;
		selectedFileId = id;
		viewMode = 'preview';
		flashcardIdx = 0;
		flashcardFlipped = false;
		paperQuestions = [];
		paperCurrentQ  = 0;
		paperScore     = 0;
		revokePdfUrl();
		buildPdfUrl();
	}

	// ── File icon helper ──────────────────────────────────────────────────────

	function fileIcon(type: string) {
		if (['png','jpg','jpeg','gif','webp'].includes(type)) return Image;
		if (type === 'pdf') return File;
		if (['pptx','ppt'].includes(type)) return FileText;
		if (type === 'md') return BookOpen;
		return File;
	}

	function formatBytes(n: number): string {
		if (n < 1024) return `${n}B`;
		if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)}KB`;
		return `${(n / (1024 * 1024)).toFixed(1)}MB`;
	}

	function formatDate(ts: number): string {
		return new Date(ts).toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' });
	}

	// ── Upload ────────────────────────────────────────────────────────────────

	let uploadInput: HTMLInputElement;

	function openUpload() { uploadInput?.click(); }

	function fileToBase64(file: File): Promise<string> {
		return new Promise((resolve, reject) => {
			const reader = new FileReader();
			reader.onload = (ev) => {
				const dataUrl = ev.target?.result as string;
				resolve(dataUrl.split(',')[1]);
			};
			reader.onerror = reject;
			reader.readAsDataURL(file);
		});
	}

	const SIZE_LIMIT = 2 * 1024 * 1024; // 2 MB

	async function handleUpload(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const list  = Array.from(input.files ?? []);
		const target = activeFolderId ?? folders.find((f) => f.parentId !== null)?.id ?? folders[0]?.id;
		if (!target) return;

		const large: string[] = [];

		for (const file of list) {
			const ext         = file.name.split('.').pop()?.toLowerCase() ?? '';
			const content     = await fileToBase64(file);
			const sessionOnly = file.size > SIZE_LIMIT;
			if (sessionOnly) large.push(file.name);

			const newFile: ResourceFile = {
				id: generateId(),
				name: file.name,
				content,
				type: ext,
				size: file.size,
				uploadDate: Date.now(),
				folderId: target,
				processingStatus: 'none',
				flashcards: [],
				sessionOnly,
			};
			files = [...files, newFile];
		}
		save();
		input.value = '';

		if (large.length) {
			showToast(
				`${large.map((n) => `"${n}"`).join(', ')} ${large.length === 1 ? 'is' : 'are'} over 2 MB — ` +
				`stored for this session only. Will not persist across navigation. Deploy to lab for full storage.`,
			);
		}
	}

	// ── New folder ────────────────────────────────────────────────────────────

	let newFolderOpen   = false;
	let newFolderName   = '';
	let newFolderParent = '';

	function openNewFolder() {
		newFolderName   = '';
		newFolderParent = semesterFolders[0]?.id ?? '';
		newFolderOpen   = true;
	}

	function confirmNewFolder() {
		if (!newFolderName.trim()) { newFolderOpen = false; return; }
		const f: ResourceFolder = {
			id: generateId(),
			name: newFolderName.trim(),
			parentId: newFolderParent || null,
		};
		folders = [...folders, f];
		save();
		newFolderOpen = false;
	}

	// ── Context menu ──────────────────────────────────────────────────────────

	interface CtxMenu {
		x: number;
		y: number;
		type: 'file' | 'folder';
		id: string;
		showMove?: boolean;
	}

	let ctxMenu: CtxMenu | null = null;
	let renamingId: string | null = null;
	let renameValue = '';
	let movingFileId: string | null = null;

	function openCtx(e: MouseEvent, type: 'file' | 'folder', id: string) {
		e.preventDefault();
		ctxMenu = { x: e.clientX, y: e.clientY, type, id };
		movingFileId = null;
	}

	function closeCtx() { ctxMenu = null; movingFileId = null; }

	function startRename(id: string, currentName: string) {
		renamingId  = id;
		renameValue = currentName;
		closeCtx();
		tick().then(() => {
			(document.querySelector('.rename-input') as HTMLInputElement)?.focus();
		});
	}

	function commitRename(id: string, type: 'file' | 'folder') {
		if (!renameValue.trim()) { renamingId = null; return; }
		if (type === 'file') {
			files = files.map((f) => f.id === id ? { ...f, name: renameValue.trim() } : f);
		} else {
			folders = folders.map((f) => f.id === id ? { ...f, name: renameValue.trim() } : f);
		}
		save();
		renamingId = null;
	}

	function deleteItem(id: string, type: 'file' | 'folder') {
		if (type === 'file') {
			if (selectedFileId === id) { selectedFileId = null; revokePdfUrl(); }
			files = files.filter((f) => f.id !== id);
		} else {
			const childIds = folders.filter((f) => f.parentId === id).map((f) => f.id);
			const allRemoved = new Set([id, ...childIds]);
			folders = folders.filter((f) => !allRemoved.has(f.id));
			files   = files.filter((f) => !allRemoved.has(f.folderId));
		}
		save();
		closeCtx();
	}

	function moveFile(fileId: string, targetFolderId: string) {
		files = files.map((f) => f.id === fileId ? { ...f, folderId: targetFolderId } : f);
		save();
		closeCtx();
	}

	// ── PDF blob URL ──────────────────────────────────────────────────────────

	let pdfBlobUrl: string | null = null;

	function revokePdfUrl() {
		if (pdfBlobUrl) { URL.revokeObjectURL(pdfBlobUrl); pdfBlobUrl = null; }
	}

	function buildPdfUrl() {
		// Use direct lookup — calling this synchronously after setting selectedFileId
		// means the reactive $: selectedFile hasn't re-evaluated yet.
		const file = files.find((f) => f.id === selectedFileId);
		if (!file || file.type !== 'pdf') return;
		try {
			const bytes = Uint8Array.from(atob(file.content), (c) => c.charCodeAt(0));
			const blob  = new Blob([bytes], { type: 'application/pdf' });
			pdfBlobUrl  = URL.createObjectURL(blob);
		} catch { pdfBlobUrl = null; }
	}

	$: renderedMd = (() => {
		if (selectedFile?.type !== 'md') return '';
		try { return marked.parse(atob(selectedFile.content)) as string; }
		catch { return ''; }
	})();

	$: imageSrc = (() => {
		if (!selectedFile) return '';
		const t = selectedFile.type;
		if (!['png','jpg','jpeg','gif','webp'].includes(t)) return '';
		const mime = t === 'jpg' ? 'jpeg' : t;
		return `data:image/${mime};base64,${selectedFile.content}`;
	})();

	// ── Processing ────────────────────────────────────────────────────────────

	function getFileSemester(file: ResourceFile): string {
		const folder = folders.find((f) => f.id === file.folderId);
		if (!folder) return '';
		if (folder.parentId === null) return folder.name;
		return folders.find((f) => f.id === folder.parentId)?.name ?? '';
	}

	function getFileSubject(file: ResourceFile): string {
		const folder = folders.find((f) => f.id === file.folderId);
		if (!folder) return '';
		if (folder.parentId !== null) return folder.name;
		return '';
	}

	async function processFile(file: ResourceFile) {
		files = files.map((f) =>
			f.id === file.id ? { ...f, processingStatus: 'processing' } : f,
		);
		save();

		try {
			const result = await resourcesApi.process({
				filename: file.name,
				content:  file.content,
				file_type: file.type,
				subject:  getFileSubject(file),
				semester: getFileSemester(file),
			});

			if (result) {
				files = files.map((f) =>
					f.id === file.id
						? { ...f, processingStatus: 'ready', extractedText: result.text }
						: f,
				);
			} else {
				files = files.map((f) =>
					f.id === file.id ? { ...f, processingStatus: 'failed' } : f,
				);
			}
		} catch {
			files = files.map((f) =>
				f.id === file.id ? { ...f, processingStatus: 'failed' } : f,
			);
		}
		save();
	}

	// ── SSE reader (same pattern as AI page) ──────────────────────────────────

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
				const blocks = buf.split('\n\n');
				buf = blocks.pop() ?? '';
				for (const block of blocks) {
					let event = 'message', data = '';
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

	async function streamAiText(prompt: string): Promise<string> {
		const res = await aiApi.chat({
			model:           $selectedModel,
			message:         prompt,
			conversation_id: generateId(),
		});
		if (!res.ok) return '';
		let out = '';
		for await (const { event, data } of readSSE(res)) {
			if (event === 'chunk') {
				try { out += (JSON.parse(data) as { content: string }).content; } catch {}
			} else if (event === 'done') break;
		}
		return out;
	}

	// ── Flashcards ────────────────────────────────────────────────────────────

	let viewMode: ViewMode = 'preview';
	let generatingFlashcards = false;
	let flashcardIdx     = 0;
	let flashcardFlipped = false;

	async function generateFlashcards(file: ResourceFile) {
		if (!file.extractedText) return;
		generatingFlashcards = true;
		const prompt = `Generate exactly 10 flashcards from this content. Return ONLY valid JSON, no other text:\n[{"front":"question","back":"answer"}]\n\nContent:\n${file.extractedText.slice(0, 8000)}`;
		try {
			const raw  = await streamAiText(prompt);
			const match = raw.match(/\[[\s\S]*\]/);
			if (match) {
				const cards = JSON.parse(match[0]) as Flashcard[];
				files = files.map((f) => f.id === file.id ? { ...f, flashcards: cards } : f);
				save();
				viewMode       = 'flashcards';
				flashcardIdx   = 0;
				flashcardFlipped = false;
			}
		} catch { /* ignore */ }
		generatingFlashcards = false;
	}

	function flipCard() { flashcardFlipped = !flashcardFlipped; }

	function prevCard() {
		if (flashcardIdx > 0) { flashcardIdx--; flashcardFlipped = false; }
	}

	function nextCard(total: number) {
		if (flashcardIdx < total - 1) { flashcardIdx++; flashcardFlipped = false; }
	}

	// ── Past paper mode ───────────────────────────────────────────────────────

	let paperQuestions:    PaperQuestion[] = [];
	let paperCurrentQ    = 0;
	let paperScore       = 0;
	let extractingPaper  = false;
	let markingAnswer    = false;
	let paperDone        = false;

	async function startPaperMode(file: ResourceFile) {
		if (!file.extractedText) return;
		viewMode       = 'pastpaper';
		extractingPaper = true;
		paperQuestions = [];
		paperCurrentQ  = 0;
		paperScore     = 0;
		paperDone      = false;

		const prompt = `Extract all exam questions from this past paper. Return ONLY a JSON array of question strings, no other text. Example: ["Q1 text","Q2 text"]\n\nPaper:\n${file.extractedText.slice(0, 8000)}`;
		try {
			const raw  = await streamAiText(prompt);
			const match = raw.match(/\[[\s\S]*\]/);
			if (match) {
				const qs = JSON.parse(match[0]) as string[];
				paperQuestions = qs.map((t) => ({ text: t, userAnswer: '', feedback: '', correct: null }));
			}
		} catch { /* ignore */ }
		extractingPaper = false;
	}

	async function checkAnswer() {
		const q = paperQuestions[paperCurrentQ];
		if (!q?.userAnswer.trim() || markingAnswer) return;
		markingAnswer = true;

		const prompt = `You are a teacher. Mark this answer.\nQuestion: "${q.text}"\nStudent answer: "${q.userAnswer}"\nReturn ONLY JSON: {"correct":true,"explanation":"...","study_tip":"..."}`;
		try {
			const raw  = await streamAiText(prompt);
			const match = raw.match(/\{[\s\S]*\}/);
			if (match) {
				const fb = JSON.parse(match[0]);
				if (fb.correct) paperScore++;
				paperQuestions = paperQuestions.map((pq, i) =>
					i === paperCurrentQ
						? { ...pq, feedback: `${fb.explanation}${fb.study_tip ? `\n\n💡 ${fb.study_tip}` : ''}`, correct: fb.correct }
						: pq,
				);
			}
		} catch { /* ignore */ }
		markingAnswer = false;
	}

	function nextQuestion() {
		if (paperCurrentQ < paperQuestions.length - 1) {
			paperCurrentQ++;
		} else {
			paperDone = true;
		}
	}

	function exitPaperMode() { viewMode = 'preview'; paperQuestions = []; paperDone = false; }

	// ── Ask AI about this file ────────────────────────────────────────────────

	function askAiAboutFile(file: ResourceFile) {
		pendingAiContext.set({
			filename: file.name,
			subject:  getFileSubject(file),
			text:     file.extractedText ?? '',
		});
		goto('/ai');
	}

	// ── Download ──────────────────────────────────────────────────────────────

	function downloadFile(file: ResourceFile) {
		try {
			const bytes = Uint8Array.from(atob(file.content), (c) => c.charCodeAt(0));
			const blob  = new Blob([bytes]);
			const url   = URL.createObjectURL(blob);
			const a     = document.createElement('a');
			a.href = url; a.download = file.name; a.click();
			URL.revokeObjectURL(url);
		} catch { /* ignore */ }
	}

	// ── Panel resize ──────────────────────────────────────────────────────────

	const RES_PAGE_KEY = 'dashboard_config.resources';
	let leftW  = 240;
	let rightW = 260;

	let resizingLeft   = false;
	let resizingRight  = false;
	let resizeStartX   = 0;
	let resizeStartW   = 0;

	function startResizeLeft(e: MouseEvent) {
		resizingLeft  = true; resizeStartX = e.clientX; resizeStartW = leftW; e.preventDefault();
	}
	function startResizeRight(e: MouseEvent) {
		resizingRight = true; resizeStartX = e.clientX; resizeStartW = rightW; e.preventDefault();
	}

	function onMouseMove(e: MouseEvent) {
		if (resizingLeft)  { leftW  = Math.min(400, Math.max(180, resizeStartW + (e.clientX - resizeStartX))); }
		if (resizingRight) { rightW = Math.min(400, Math.max(200, resizeStartW - (e.clientX - resizeStartX))); }
	}

	function onMouseUp() {
		if (resizingLeft || resizingRight) {
			resizingLeft = resizingRight = false;
			try { localStorage.setItem(RES_PAGE_KEY, JSON.stringify({ leftW, rightW })); } catch { /* ignore */ }
		}
	}

	// ── Mount / destroy ───────────────────────────────────────────────────────

	onMount(() => {
		load();

		// Restore panel widths
		try {
			const raw = localStorage.getItem(RES_PAGE_KEY);
			if (raw) { const cfg = JSON.parse(raw); leftW = cfg.leftW ?? 240; rightW = cfg.rightW ?? 260; }
		} catch { /* ignore */ }

		window.addEventListener('mousemove', onMouseMove);
		window.addEventListener('mouseup',   onMouseUp);
	});

	onDestroy(() => {
		revokePdfUrl();
		if (toastTimer) clearTimeout(toastTimer);
		if (typeof window !== 'undefined') {
			window.removeEventListener('mousemove', onMouseMove);
			window.removeEventListener('mouseup',   onMouseUp);
		}
	});
</script>

<svelte:head>
	<title>Nexus — Resources</title>
</svelte:head>

<!-- Toast -->
{#if toastMsg}
	<div class="toast-banner">
		<span class="toast-icon">⚠</span>
		<span class="toast-text">{toastMsg}</span>
		<button class="toast-close" on:click={() => toastMsg = ''}>✕</button>
	</div>
{/if}

<!-- Context menu backdrop -->
{#if ctxMenu}
	<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
	<div class="ctx-backdrop" on:click={closeCtx} on:contextmenu|preventDefault={closeCtx}></div>
	<div class="ctx-menu" style="left:{ctxMenu.x}px;top:{ctxMenu.y}px">
		<button class="ctx-item" on:click={() => {
			const item = ctxMenu!.type === 'file'
				? files.find(f => f.id === ctxMenu!.id)
				: folders.find(f => f.id === ctxMenu!.id);
			startRename(ctxMenu!.id, item?.name ?? '');
		}}>Rename</button>
		<button class="ctx-item ctx-danger" on:click={() => deleteItem(ctxMenu!.id, ctxMenu!.type)}>Delete</button>
		{#if ctxMenu.type === 'file'}
			<button class="ctx-item" on:click={() => { movingFileId = ctxMenu!.id; ctxMenu = {...ctxMenu!, showMove: true}; }}>
				Move to folder…
			</button>
			{#if ctxMenu.showMove && movingFileId}
				<div class="ctx-sub">
					{#each folders.filter(f => f.parentId !== null) as f}
						<button class="ctx-item" on:click={() => moveFile(movingFileId!, f.id)}>
							{folders.find(p => p.id === f.parentId)?.name} / {f.name}
						</button>
					{/each}
				</div>
			{/if}
		{/if}
	</div>
{/if}

<div class="res-page">

	<!-- ── Left: folder tree ────────────────────────────────── -->
	<aside class="res-left" style="width:{leftW}px">

		<div class="tree-header">
			<label class="hdr-btn" title="Upload files">
				<Upload size={13} strokeWidth={1.5} />
				Upload
				<input
					bind:this={uploadInput}
					type="file"
					multiple
					accept=".pdf,.pptx,.ppt,.md,.png,.jpg,.jpeg"
					class="sr-only"
					on:change={handleUpload}
				/>
			</label>

			<button class="hdr-btn" title="New folder" on:click={openNewFolder}>
				<FolderPlus size={13} strokeWidth={1.5} />
				Folder
			</button>
		</div>

		{#if newFolderOpen}
			<div class="new-folder-form">
				<input
					class="nf-input"
					type="text"
					placeholder="Folder name"
					bind:value={newFolderName}
					on:keydown={(e) => { if (e.key === 'Enter') confirmNewFolder(); if (e.key === 'Escape') newFolderOpen = false; }}
				/>
				<select class="nf-select" bind:value={newFolderParent}>
					<option value="">Root (semester)</option>
					{#each semesterFolders as sf}
						<option value={sf.id}>{sf.name}</option>
					{/each}
				</select>
				<div class="nf-btns">
					<button class="nf-btn" on:click={confirmNewFolder}>Add</button>
					<button class="nf-btn nf-cancel" on:click={() => newFolderOpen = false}>Cancel</button>
				</div>
			</div>
		{/if}

		<div class="tree-scroll">
			{#each semesterFolders as sem (sem.id)}
				<!-- svelte-ignore a11y-click-events-have-key-events -->
				<div
					class="tree-item tree-semester"
					class:open={openFolders.has(sem.id)}
					on:click={() => toggleFolder(sem.id)}
					on:contextmenu={(e) => openCtx(e, 'folder', sem.id)}
					role="treeitem"
					aria-expanded={openFolders.has(sem.id)}
				>
					{#if openFolders.has(sem.id)}
						<ChevronDown size={12} strokeWidth={2} />
					{:else}
						<ChevronRight size={12} strokeWidth={2} />
					{/if}
					{#if renamingId === sem.id}
						<!-- svelte-ignore a11y-click-events-have-key-events -->
						<input
							class="rename-input"
							bind:value={renameValue}
							on:blur={() => commitRename(sem.id, 'folder')}
							on:keydown={(e) => { if (e.key === 'Enter') commitRename(sem.id, 'folder'); if (e.key === 'Escape') renamingId = null; }}
							on:click|stopPropagation
						/>
					{:else}
						<span class="tree-name">{sem.name}</span>
					{/if}
					<span class="tree-count">{getFolderFiles(sem.id).length + getSubFolders(sem.id).reduce((s,f)=>s+getFolderFiles(f.id).length,0)}</span>
				</div>

				{#if openFolders.has(sem.id)}
					{#each getSubFolders(sem.id) as sub (sub.id)}
						<!-- svelte-ignore a11y-click-events-have-key-events -->
						<div
							class="tree-item tree-subject"
							class:open={openFolders.has(sub.id)}
							class:active-folder={activeFolderId === sub.id}
							on:click={() => { toggleFolder(sub.id); activeFolderId = sub.id; }}
							on:contextmenu={(e) => openCtx(e, 'folder', sub.id)}
							role="treeitem"
							aria-expanded={openFolders.has(sub.id)}
						>
							{#if openFolders.has(sub.id)}
								<FolderOpen size={12} strokeWidth={1.5} />
							{:else}
								<Folder size={12} strokeWidth={1.5} />
							{/if}
							{#if renamingId === sub.id}
								<!-- svelte-ignore a11y-click-events-have-key-events -->
								<input
									class="rename-input"
									bind:value={renameValue}
									on:blur={() => commitRename(sub.id, 'folder')}
									on:keydown={(e) => { if (e.key === 'Enter') commitRename(sub.id, 'folder'); if (e.key === 'Escape') renamingId = null; }}
									on:click|stopPropagation
								/>
							{:else}
								<span class="tree-name">{sub.name}</span>
							{/if}
							<span class="tree-count">{getFolderFiles(sub.id).length}</span>
						</div>

						{#if openFolders.has(sub.id)}
							{#each getFolderFiles(sub.id) as file (file.id)}
								<!-- svelte-ignore a11y-click-events-have-key-events -->
								<div
									class="tree-item tree-file"
									class:selected={selectedFileId === file.id}
									on:click={() => selectFile(file.id)}
									on:contextmenu={(e) => openCtx(e, 'file', file.id)}
									role="treeitem"
									aria-selected={selectedFileId === file.id}
								>
									<svelte:component this={fileIcon(file.type)} size={12} strokeWidth={1.5} />
									<div class="tree-file-info">
										{#if renamingId === file.id}
											<!-- svelte-ignore a11y-click-events-have-key-events -->
											<input
												class="rename-input"
												bind:value={renameValue}
												on:blur={() => commitRename(file.id, 'file')}
												on:keydown={(e) => { if (e.key === 'Enter') commitRename(file.id, 'file'); if (e.key === 'Escape') renamingId = null; }}
												on:click|stopPropagation
											/>
										{:else}
											<span class="tree-file-name">{file.name}</span>
										{/if}
										<span class="tree-file-meta">{formatBytes(file.size)} · {formatDate(file.uploadDate)}</span>
									</div>
									{#if file.sessionOnly}
										<span class="session-badge" title="Session only — not saved to localStorage">~</span>
									{:else if file.processingStatus === 'ready'}
										<span class="proc-dot proc-ready" title="Processed"></span>
									{:else if file.processingStatus === 'processing'}
										<span class="proc-dot proc-busy" title="Processing…"></span>
									{/if}
								</div>
							{/each}
						{/if}
					{/each}

					{#each getFolderFiles(sem.id) as file (file.id)}
						<!-- svelte-ignore a11y-click-events-have-key-events -->
						<div
							class="tree-item tree-file tree-file--semester"
							class:selected={selectedFileId === file.id}
							on:click={() => selectFile(file.id)}
							on:contextmenu={(e) => openCtx(e, 'file', file.id)}
							role="treeitem"
							aria-selected={selectedFileId === file.id}
						>
							<svelte:component this={fileIcon(file.type)} size={12} strokeWidth={1.5} />
							<div class="tree-file-info">
								<span class="tree-file-name">{file.name}</span>
								<span class="tree-file-meta">{formatBytes(file.size)} · {formatDate(file.uploadDate)}</span>
							</div>
						</div>
					{/each}
				{/if}
			{/each}
		</div>
	</aside>

	<!-- ── Left resize handle ────────────────────────────────── -->
	<div class="panel-resize" class:resizing={resizingLeft} on:mousedown={startResizeLeft} role="separator" aria-orientation="vertical" aria-label="Resize file tree"></div>

	<!-- ── Middle: viewer ───────────────────────────────────── -->
	<div class="res-mid">
		{#if viewMode === 'preview'}
			{#if !selectedFile}
				{#if files.length === 0}
					<EmptyState
						variant="not-configured"
						title="No resources"
						body="Upload files with the Upload button or drop them into the .nexus/resources/ folder on disk."
						primaryAction="Upload"
						primaryOnClick={openUpload}
					/>
				{:else}
					<div class="empty-state">
						<Library size={32} strokeWidth={1} />
						<p>Select a resource to preview</p>
					</div>
				{/if}

			{:else if selectedFile.type === 'pdf'}
				{#if pdfBlobUrl}
					<iframe class="pdf-frame" src={pdfBlobUrl} title={selectedFile.name}></iframe>
				{:else}
					<div class="empty-state"><p>Loading PDF…</p></div>
				{/if}

			{:else if ['pptx','ppt'].includes(selectedFile.type)}
				<div class="pptx-card">
					<FileText size={40} strokeWidth={1} />
					<h3>{selectedFile.name}</h3>
					<p class="pptx-meta">PowerPoint · {formatBytes(selectedFile.size)} · {formatDate(selectedFile.uploadDate)}</p>
					<button class="dl-btn" on:click={() => downloadFile(selectedFile!)}>
						<Download size={14} strokeWidth={1.5} /> Download
					</button>
				</div>

			{:else if selectedFile.type === 'md'}
				<div class="md-viewer">
					<div class="md-body">{@html renderedMd}</div>
				</div>

			{:else if imageSrc}
				<div class="img-viewer">
					<img src={imageSrc} alt={selectedFile.name} class="preview-img" />
				</div>

			{:else}
				<div class="empty-state">
					<File size={32} strokeWidth={1} />
					<p>No preview available</p>
					<button class="dl-btn" on:click={() => downloadFile(selectedFile!)}>
						<Download size={14} strokeWidth={1.5} /> Download
					</button>
				</div>
			{/if}

		{:else if viewMode === 'flashcards'}
			{@const cards = selectedFile?.flashcards ?? []}
			{@const card  = cards[flashcardIdx]}
			{#if !card}
				<div class="empty-state"><p>No flashcards</p></div>
			{:else}
				<div class="fc-viewer">
					<div class="fc-counter">{flashcardIdx + 1} / {cards.length}</div>
					<!-- svelte-ignore a11y-click-events-have-key-events -->
					<div class="fc-card" class:flipped={flashcardFlipped} on:click={flipCard} role="button" tabindex="0" on:keydown={(e) => e.key === 'Enter' && flipCard()}>
						<div class="fc-face fc-front">
							<span class="fc-side-label">QUESTION</span>
							<p class="fc-text">{card.front}</p>
							<span class="fc-hint">Click to reveal answer</span>
						</div>
						<div class="fc-face fc-back">
							<span class="fc-side-label">ANSWER</span>
							<p class="fc-text">{card.back}</p>
						</div>
					</div>
					<div class="fc-nav">
						<button class="fc-btn" on:click={prevCard} disabled={flashcardIdx === 0}>← Prev</button>
						<button class="fc-btn fc-regen" on:click={() => selectedFile && generateFlashcards(selectedFile)} disabled={generatingFlashcards}>
							{#if generatingFlashcards}<Loader size={13} class="spin" />{:else}<RotateCcw size={13} />{/if}
							Regenerate
						</button>
						<button class="fc-btn" on:click={() => nextCard(cards.length)} disabled={flashcardIdx >= cards.length - 1}>Next →</button>
					</div>
					<button class="fc-exit" on:click={() => viewMode = 'preview'}>← Back to preview</button>
				</div>
			{/if}

		{:else if viewMode === 'pastpaper'}
			<div class="pp-viewer">
				{#if extractingPaper}
					<div class="pp-loading">
						<Loader size={24} class="spin" />
						<p>Extracting questions from paper…</p>
					</div>

				{:else if paperDone}
					<div class="pp-done">
						<h3 class="pp-score">Score: {paperScore} / {paperQuestions.length}</h3>
						<p class="pp-score-sub">{Math.round((paperScore / Math.max(1, paperQuestions.length)) * 100)}% correct</p>
						<button class="pp-btn" on:click={exitPaperMode}>← Back to preview</button>
					</div>

				{:else if paperQuestions.length === 0}
					<div class="empty-state"><p>Could not extract questions from this file.</p><button class="pp-btn" on:click={exitPaperMode}>← Back</button></div>

				{:else}
					{@const q = paperQuestions[paperCurrentQ]}
					<div class="pp-question">
						<div class="pp-header">
							<span class="pp-counter">Question {paperCurrentQ + 1} of {paperQuestions.length}</span>
							<span class="pp-score-badge">Score: {paperScore}</span>
						</div>
						<p class="pp-q-text">{q.text}</p>
						<textarea
							class="pp-answer"
							placeholder="Type your answer…"
							bind:value={paperQuestions[paperCurrentQ].userAnswer}
							rows="5"
							disabled={q.correct !== null}
						></textarea>

						{#if q.correct === null}
							<button class="pp-btn" on:click={checkAnswer} disabled={markingAnswer || !q.userAnswer.trim()}>
								{#if markingAnswer}<Loader size={13} class="spin" /> Marking…{:else}Check Answer{/if}
							</button>
						{:else}
							<div class="pp-feedback" class:pp-correct={q.correct} class:pp-wrong={!q.correct}>
								<span class="pp-fb-badge">{q.correct ? '✓ Correct' : '✗ Incorrect'}</span>
								<p class="pp-fb-text">{q.feedback}</p>
							</div>
							<button class="pp-btn" on:click={nextQuestion}>
								{paperCurrentQ < paperQuestions.length - 1 ? 'Next Question →' : 'See Results'}
							</button>
						{/if}
					</div>
					<button class="pp-exit" on:click={exitPaperMode}>Exit Past Paper Mode</button>
				{/if}
			</div>
		{/if}
	</div>

	<!-- ── Right resize handle ───────────────────────────────── -->
	<div class="panel-resize" class:resizing={resizingRight} on:mousedown={startResizeRight} role="separator" aria-orientation="vertical" aria-label="Resize info panel"></div>

	<!-- ── Right: file info + AI actions ────────────────────── -->
	<aside class="res-right" style="width:{rightW}px">
		{#if !selectedFile}
			<div class="info-empty">
				<Library size={24} strokeWidth={1} />
				<p>No file selected</p>
			</div>
		{:else}
			<div class="info-panel">
				<!-- File info -->
				<div class="info-section">
					<div class="info-header">FILE INFO</div>
					<div class="info-name">{selectedFile.name}</div>
					<div class="info-row"><span class="info-k">Type</span><span class="info-v info-type">{selectedFile.type.toUpperCase()}</span></div>
					<div class="info-row"><span class="info-k">Size</span><span class="info-v">{formatBytes(selectedFile.size)}</span></div>
					<div class="info-row"><span class="info-k">Uploaded</span><span class="info-v">{formatDate(selectedFile.uploadDate)}</span></div>
					<div class="info-row"><span class="info-k">Subject</span><span class="info-v">{getFileSubject(selectedFile) || '—'}</span></div>
				</div>

				<!-- Download -->
				<div class="info-section">
					<button class="info-btn" on:click={() => downloadFile(selectedFile!)}>
						<Download size={13} strokeWidth={1.5} /> Download file
					</button>
				</div>

				<!-- AI processing -->
				<div class="info-section">
					<div class="info-header">AI PROCESSING</div>
					{#if selectedFile.processingStatus === 'none' || selectedFile.processingStatus === 'failed'}
						{#if selectedFile.processingStatus === 'failed'}
							<div class="proc-status proc-failed"><XCircle size={13} /> Failed</div>
						{/if}
						<button
							class="info-btn info-btn--primary"
							on:click={() => processFile(selectedFile!)}
							disabled={!['pdf','pptx','ppt','md'].includes(selectedFile.type)}
						>
							<Cpu size={13} strokeWidth={1.5} />
							{selectedFile.processingStatus === 'failed' ? 'Retry processing' : 'Process for AI'}
						</button>

					{:else if selectedFile.processingStatus === 'processing'}
						<div class="proc-status proc-processing">
							<Loader size={13} class="spin" /> Processing…
						</div>

					{:else if selectedFile.processingStatus === 'ready'}
						<div class="proc-status proc-ok">
							<CheckCircle size={13} /> Ready for study mode
						</div>
						<button class="info-btn info-btn--secondary" on:click={() => processFile(selectedFile!)}>
							Re-process
						</button>
					{/if}
				</div>

				<!-- AI actions (when processed) -->
				{#if selectedFile.processingStatus === 'ready'}
					<div class="info-section">
						<div class="info-header">AI ACTIONS</div>

						<button class="info-btn info-btn--accent" on:click={() => askAiAboutFile(selectedFile!)}>
							<BookOpen size={13} strokeWidth={1.5} /> Ask AI about this file
						</button>

						<button
							class="info-btn"
							on:click={() => generateFlashcards(selectedFile!)}
							disabled={generatingFlashcards}
						>
							{#if generatingFlashcards}
								<Loader size={13} class="spin" /> Generating…
							{:else}
								<RotateCcw size={13} strokeWidth={1.5} /> Generate Flashcards
							{/if}
						</button>

						{#if selectedFile.flashcards?.length}
							<button class="info-btn" on:click={() => { viewMode = 'flashcards'; flashcardIdx = 0; flashcardFlipped = false; }}>
								View {selectedFile.flashcards.length} Flashcards
							</button>
						{/if}

						{#if selectedFile.type === 'pdf'}
							<button
								class="info-btn"
								on:click={() => startPaperMode(selectedFile!)}
								disabled={extractingPaper}
							>
								{#if extractingPaper}
									<Loader size={13} class="spin" /> Extracting…
								{:else}
									Past Paper Mode
								{/if}
							</button>
						{/if}
					</div>
				{/if}
			</div>
		{/if}
	</aside>

</div>

<style>
	/* ── Full-bleed page ─────────────────────────────────────── */
	.res-page {
		display: flex;
		margin: -1.5rem;
		width:  calc(100% + 3rem);
		height: calc(100% + 3rem);
		overflow: hidden;
		background: var(--bg0);
	}

	/* ── Context menu ────────────────────────────────────────── */
	.ctx-backdrop {
		position: fixed; inset: 0; z-index: 100;
	}

	.ctx-menu {
		position: fixed;
		z-index: 101;
		background: var(--bg3);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 0.2rem;
		box-shadow: 0 8px 24px rgba(0,0,0,0.4);
		min-width: 140px;
		display: flex;
		flex-direction: column;
	}

	.ctx-item {
		text-align: left;
		padding: 0.35rem 0.6rem;
		background: none;
		border: none;
		border-radius: 3px;
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text1);
		cursor: pointer;
		transition: background 0.1s, color 0.1s;
	}
	.ctx-item:hover { background: var(--bg2); color: var(--text0); }
	.ctx-danger:hover { color: var(--red); }

	.ctx-sub {
		border-top: 1px solid var(--border);
		margin-top: 0.2rem;
		padding-top: 0.2rem;
		max-height: 200px;
		overflow-y: auto;
	}

	/* ── Left panel ──────────────────────────────────────────── */
	.res-left {
		flex-shrink: 0;
		background: var(--bg1);
		border-right: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.tree-header {
		display: flex;
		gap: 2px;
		padding: 0.5rem;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.hdr-btn {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		flex: 1;
		justify-content: center;
		padding: 0.3rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.7rem;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}
	.hdr-btn:hover { color: var(--text0); border-color: var(--accent); }

	/* New folder form */
	.new-folder-form {
		padding: 0.5rem;
		border-bottom: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		flex-shrink: 0;
	}

	.nf-input, .nf-select {
		width: 100%;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 3px;
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		padding: 0.25rem 0.4rem;
		outline: none;
	}
	.nf-input:focus, .nf-select:focus { border-color: var(--accent); }

	.nf-btns { display: flex; gap: 0.3rem; }

	.nf-btn {
		flex: 1;
		padding: 0.2rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 3px;
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.7rem;
		cursor: pointer;
	}
	.nf-btn:hover { color: var(--text0); border-color: var(--accent); }
	.nf-cancel:hover { border-color: var(--red); color: var(--red); }

	/* Tree */
	.tree-scroll {
		flex: 1;
		overflow-y: auto;
		padding: 0.25rem 0;
	}

	.tree-item {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.28rem 0.5rem;
		cursor: pointer;
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text1);
		transition: background 0.08s, color 0.08s;
		user-select: none;
		position: relative;
	}
	.tree-item:hover { background: var(--bg2); color: var(--text0); }

	.tree-semester { font-weight: 600; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text2); padding-left: 0.75rem; }
	.tree-subject  { padding-left: 1.25rem; }
	.tree-file     { padding-left: 2.25rem; align-items: flex-start; }
	.tree-file--semester { padding-left: 1.75rem; }

	.tree-file.selected { background: color-mix(in srgb, var(--yellow) 12%, transparent); color: var(--yellow); }
	.active-folder { color: var(--accent); }

	.tree-name { flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
	.tree-count { font-size: 0.62rem; color: var(--text2); flex-shrink: 0; }

	.tree-file-info { flex: 1; min-width: 0; }
	.tree-file-name { display: block; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 0.72rem; }
	.tree-file-meta { display: block; font-size: 0.6rem; color: var(--text2); }

	.proc-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; margin-top: 4px; }
	.proc-ready { background: var(--green); }
	.proc-busy  { background: var(--yellow); animation: pulse-dot 1s ease-in-out infinite; }

	@keyframes pulse-dot { 0%,100%{opacity:1} 50%{opacity:0.4} }

	.rename-input {
		flex: 1;
		background: var(--bg2);
		border: 1px solid var(--accent);
		border-radius: 3px;
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		padding: 0.1rem 0.3rem;
		outline: none;
	}

	/* ── Resize handle ───────────────────────────────────────── */
	.panel-resize {
		width: 4px;
		flex-shrink: 0;
		background: var(--border);
		cursor: col-resize;
		transition: background 0.12s;
	}
	.panel-resize:hover, .panel-resize.resizing { background: var(--accent); }

	/* ── Middle ──────────────────────────────────────────────── */
	.res-mid {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		overflow: hidden;
		background: var(--bg0);
	}

	.empty-state {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.82rem;
	}

	.pdf-frame {
		flex: 1;
		width: 100%;
		border: none;
	}

	.pptx-card {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		color: var(--text1);
		font-family: var(--font-mono);
		padding: 2rem;
	}
	.pptx-card h3 { font-size: 1rem; color: var(--text0); text-align: center; word-break: break-all; }
	.pptx-meta { font-size: 0.72rem; color: var(--text2); }

	.md-viewer { flex: 1; overflow-y: auto; padding: 1.5rem; }
	.img-viewer { flex: 1; display: flex; align-items: center; justify-content: center; overflow: auto; padding: 1rem; }
	.preview-img { max-width: 100%; max-height: 100%; object-fit: contain; }

	/* ── Flashcard viewer ────────────────────────────────────── */
	.fc-viewer {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 1rem;
		padding: 2rem;
	}

	.fc-counter {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text2);
	}

	.fc-card {
		width: 100%;
		max-width: 520px;
		height: 220px;
		position: relative;
		cursor: pointer;
		perspective: 1000px;
	}

	.fc-face {
		position: absolute;
		inset: 0;
		backface-visibility: hidden;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		transition: transform 0.45s ease;
	}

	.fc-front { transform: rotateY(0deg); }
	.fc-back  { transform: rotateY(180deg); }

	.fc-card.flipped .fc-front { transform: rotateY(-180deg); }
	.fc-card.flipped .fc-back  { transform: rotateY(0deg); }

	.fc-side-label {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--accent);
		align-self: flex-start;
	}

	.fc-back .fc-side-label { color: var(--accent2); }

	.fc-text {
		font-family: var(--font-mono);
		font-size: 0.9rem;
		color: var(--text0);
		text-align: center;
		line-height: 1.6;
	}

	.fc-hint {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
	}

	.fc-nav {
		display: flex;
		gap: 0.5rem;
		align-items: center;
	}

	.fc-btn {
		padding: 0.3rem 0.75rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.3rem;
		transition: color 0.1s, border-color 0.1s;
	}
	.fc-btn:hover:not(:disabled) { color: var(--text0); border-color: var(--accent); }
	.fc-btn:disabled { opacity: 0.3; cursor: not-allowed; }
	.fc-regen { color: var(--accent3); border-color: color-mix(in srgb, var(--accent3) 30%, var(--border)); }

	.fc-exit {
		background: none; border: none; font-family: var(--font-mono); font-size: 0.72rem;
		color: var(--text2); cursor: pointer; padding: 0.25rem 0;
	}
	.fc-exit:hover { color: var(--text0); }

	/* ── Past paper viewer ───────────────────────────────────── */
	.pp-viewer {
		flex: 1;
		display: flex;
		flex-direction: column;
		overflow-y: auto;
		padding: 1.5rem;
	}

	.pp-loading, .pp-done {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		font-family: var(--font-mono);
		color: var(--text1);
	}

	.pp-score { font-size: 1.5rem; color: var(--accent); }
	.pp-score-sub { font-size: 0.8rem; color: var(--text2); }

	.pp-question { display: flex; flex-direction: column; gap: 0.75rem; max-width: 680px; }

	.pp-header { display: flex; justify-content: space-between; align-items: center; }
	.pp-counter { font-family: var(--font-mono); font-size: 0.68rem; color: var(--text2); text-transform: uppercase; letter-spacing: 0.08em; }
	.pp-score-badge { font-family: var(--font-mono); font-size: 0.72rem; color: var(--accent); }

	.pp-q-text {
		font-family: var(--font-mono);
		font-size: 0.9rem;
		color: var(--text0);
		line-height: 1.65;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 0.85rem 1rem;
	}

	.pp-answer {
		width: 100%;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.82rem;
		padding: 0.6rem 0.75rem;
		resize: vertical;
		outline: none;
		line-height: 1.55;
	}
	.pp-answer:focus { border-color: var(--accent); }

	.pp-btn {
		align-self: flex-start;
		padding: 0.35rem 1rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.35rem;
		transition: color 0.1s, border-color 0.1s;
	}
	.pp-btn:hover:not(:disabled) { color: var(--text0); border-color: var(--accent); }
	.pp-btn:disabled { opacity: 0.3; cursor: not-allowed; }

	.pp-feedback {
		padding: 0.75rem;
		border-radius: var(--radius);
		border: 1px solid var(--border);
		background: var(--bg1);
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
	}
	.pp-correct { border-color: color-mix(in srgb, var(--green) 35%, var(--border)); background: color-mix(in srgb, var(--green) 6%, var(--bg1)); }
	.pp-wrong   { border-color: color-mix(in srgb, var(--red)   35%, var(--border)); background: color-mix(in srgb, var(--red)   6%, var(--bg1)); }

	.pp-fb-badge { font-family: var(--font-mono); font-size: 0.72rem; font-weight: 700; }
	.pp-correct .pp-fb-badge { color: var(--green); }
	.pp-wrong   .pp-fb-badge { color: var(--red); }

	.pp-fb-text { font-family: var(--font-mono); font-size: 0.78rem; color: var(--text1); line-height: 1.6; white-space: pre-wrap; }

	.pp-exit {
		margin-top: auto;
		padding-top: 1rem;
		background: none;
		border: none;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--text2);
		cursor: pointer;
		align-self: flex-start;
	}
	.pp-exit:hover { color: var(--red); }

	/* ── Right panel ─────────────────────────────────────────── */
	.res-right {
		flex-shrink: 0;
		background: var(--bg1);
		border-left: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		overflow-y: auto;
	}

	.info-empty {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.75rem;
	}

	.info-panel { display: flex; flex-direction: column; }

	.info-section {
		padding: 0.6rem 0.75rem;
		border-bottom: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.info-header {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text2);
		margin-bottom: 0.15rem;
	}

	.info-name {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		font-weight: 600;
		color: var(--text0);
		word-break: break-all;
		line-height: 1.4;
	}

	.info-row { display: flex; justify-content: space-between; align-items: center; gap: 0.25rem; }
	.info-k { font-family: var(--font-mono); font-size: 0.65rem; color: var(--text2); }
	.info-v { font-family: var(--font-mono); font-size: 0.72rem; color: var(--text1); text-align: right; }
	.info-type { color: var(--accent2); font-weight: 700; }

	.info-btn {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.32rem 0.6rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.7rem;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s, background 0.1s;
	}
	.info-btn:hover:not(:disabled) { color: var(--text0); border-color: var(--accent); }
	.info-btn:disabled { opacity: 0.35; cursor: not-allowed; }

	.info-btn--primary {
		color: var(--accent);
		border-color: color-mix(in srgb, var(--accent) 35%, var(--border));
		background: color-mix(in srgb, var(--accent) 8%, var(--bg2));
	}

	.info-btn--secondary {
		font-size: 0.62rem;
		color: var(--text2);
		padding: 0.18rem 0.4rem;
		align-self: flex-start;
	}

	.info-btn--accent {
		color: var(--accent3);
		border-color: color-mix(in srgb, var(--accent3) 35%, var(--border));
		background: color-mix(in srgb, var(--accent3) 8%, var(--bg2));
	}

	.proc-status {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-family: var(--font-mono);
		font-size: 0.72rem;
		padding: 0.25rem 0;
	}
	.proc-ok      { color: var(--green); }
	.proc-failed  { color: var(--red); }
	.proc-processing { color: var(--yellow); }

	/* ── Spinner ─────────────────────────────────────────────── */
	.dl-btn {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.35rem 0.75rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}
	.dl-btn:hover { color: var(--text0); border-color: var(--accent); }

	:global(.spin) {
		animation: spin 0.8s linear infinite;
	}
	@keyframes spin { to { transform: rotate(360deg); } }

	/* ── Markdown body ───────────────────────────────────────── */
	:global(.md-body) { font-family: var(--font-mono); font-size: 0.84rem; line-height: 1.7; color: var(--text0); }
	:global(.md-body p) { margin: 0 0 0.6em; }
	:global(.md-body h1),
	:global(.md-body h2),
	:global(.md-body h3) { font-weight: 700; color: var(--accent); margin: 0.9em 0 0.4em; }
	:global(.md-body code) { background: var(--bg2); border: 1px solid var(--border); border-radius: 3px; padding: 0.05em 0.3em; font-size: 0.88em; }
	:global(.md-body pre) { background: var(--bg0); border: 1px solid var(--border); border-radius: var(--radius); padding: 0.75rem; overflow-x: auto; margin: 0.6em 0; }
	:global(.md-body pre code) { background: none; border: none; padding: 0; }
	:global(.md-body ul),
	:global(.md-body ol) { margin: 0.4em 0 0.6em 1.25em; }
	:global(.md-body blockquote) { border-left: 3px solid var(--accent); padding: 0.3em 0.75em; color: var(--text1); }

	/* ── Session-only badge ──────────────────────────────────── */
	.session-badge {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		font-weight: 700;
		color: var(--yellow);
		background: color-mix(in srgb, var(--yellow) 15%, transparent);
		border: 1px solid color-mix(in srgb, var(--yellow) 35%, transparent);
		border-radius: 3px;
		padding: 0 3px;
		flex-shrink: 0;
		margin-top: 2px;
		line-height: 1.4;
	}

	/* ── Toast banner ────────────────────────────────────────── */
	.toast-banner {
		position: fixed;
		bottom: 1.25rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 200;
		display: flex;
		align-items: flex-start;
		gap: 0.6rem;
		max-width: 480px;
		width: calc(100% - 3rem);
		background: color-mix(in srgb, var(--yellow) 10%, var(--bg1));
		border: 1px solid color-mix(in srgb, var(--yellow) 40%, var(--border));
		border-left: 3px solid var(--yellow);
		border-radius: var(--radius);
		padding: 0.7rem 0.85rem;
		box-shadow: 0 8px 24px rgba(0,0,0,0.45);
		animation: toast-in 0.18s ease;
	}

	@keyframes toast-in {
		from { opacity: 0; transform: translateX(-50%) translateY(8px); }
		to   { opacity: 1; transform: translateX(-50%) translateY(0);   }
	}

	.toast-icon { font-size: 0.9rem; color: var(--yellow); flex-shrink: 0; margin-top: 1px; }

	.toast-text {
		flex: 1;
		font-family: var(--font-mono);
		font-size: 0.74rem;
		color: var(--text0);
		line-height: 1.55;
	}

	.toast-close {
		background: none; border: none; color: var(--text2);
		font-family: var(--font-mono); font-size: 0.7rem; cursor: pointer;
		padding: 0.1rem; flex-shrink: 0; transition: color 0.1s;
	}
	.toast-close:hover { color: var(--red); }

	/* ── Utility ─────────────────────────────────────────────── */
	.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; }
</style>
