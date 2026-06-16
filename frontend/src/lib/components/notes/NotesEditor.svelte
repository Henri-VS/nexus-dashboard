<script lang="ts">
	import { afterUpdate, onMount, onDestroy } from 'svelte';
	import { marked } from 'marked';
	import { X, Eye, Edit2, Columns, Download } from '@lucide/svelte';
	import { type StoredFile, type Tab, parseFrontmatter, getFileType } from './types';
	import { EXCALIDRAW_URL } from '$lib/api';

	// ── Props ───────────────────────────────────────────────────────────────
	export let file: StoredFile | null = null;
	export let openTabs: Tab[] = [];
	export let activeTabPath: string = '';
	export let allFiles: Record<string, StoredFile> = {};
	export let mode: 'edit' | 'preview' | 'split' = 'split';
	export let dirtyPaths: Set<string> = new Set();

	export let onContentChange: (path: string, content: string) => void = () => {};
	export let onCloseTab: (path: string) => void = () => {};
	export let onSelectTab: (path: string) => void = () => {};
	export let onModeChange: (mode: 'edit' | 'preview' | 'split') => void = () => {};
	export let onOpenFile: (path: string) => void = () => {};
	export let onDirtyChange: (path: string, dirty: boolean) => void = () => {};
	export let onUploadImage: (name: string, dataUrl: string) => void = () => {};

	// ── State ────────────────────────────────────────────────────────────────
	let localContent = '';
	let saved = true;
	let saveTimer: ReturnType<typeof setTimeout>;
	let wordCount = 0;
	let charCount = 0;
	let previewEl: HTMLDivElement;
	let editorEl: HTMLTextAreaElement;
	let dragOver = false;

	// ── Sync file → localContent (only on path change or external update) ──
	let prevPath = '';

	$: if (file) syncFile(file);

	function syncFile(f: StoredFile) {
		if (f.path !== prevPath) {
			// Tab switched — save any pending dirty content immediately
			if (!saved && prevPath) {
				clearTimeout(saveTimer);
				onContentChange(prevPath, localContent);
				onDirtyChange(prevPath, false);
			}
			prevPath = f.path;
			localContent = f.content;
			saved = true;
			clearTimeout(saveTimer);
			updateCounts(f.content);
			excalidrawJsonSaved = true;
		} else if (saved && f.content !== localContent) {
			// Same file, saved, external update (e.g. frontmatter from properties panel)
			localContent = f.content;
			updateCounts(f.content);
		}
	}

	function updateCounts(text: string) {
		charCount = text.length;
		wordCount = text.trim() ? text.trim().split(/\s+/).length : 0;
	}

	function handleInput() {
		if (saved && file) {
			saved = false;
			onDirtyChange(file.path, true);
		}
		updateCounts(localContent);
		clearTimeout(saveTimer);
		saveTimer = setTimeout(() => {
			if (file) {
				onContentChange(file.path, localContent);
				onDirtyChange(file.path, false);
				saved = true;
			}
		}, 900);
	}

	// ── Markdown renderer ─────────────────────────────────────────────────
	function stripFrontmatter(content: string): string {
		const { body } = parseFrontmatter(content);
		return body;
	}

	function resolveWikilinkPath(target: string): string | null {
		const t = target.toLowerCase();
		for (const path of Object.keys(allFiles)) {
			const stem = path.replace(/\.[^/.]+$/, '');
			const filename = stem.split('/').pop() ?? '';
			if (
				filename.toLowerCase() === t ||
				stem.toLowerCase() === t ||
				path.toLowerCase() === t
			) {
				return path;
			}
		}
		return null;
	}

	function resolveWikiImage(name: string): string {
		const n = name.toLowerCase();
		for (const [path, f] of Object.entries(allFiles)) {
			const basename = (path.split('/').pop() ?? '').toLowerCase();
			if (basename === n && f.type === 'image') return f.content;
		}
		return '';
	}

	function escAttr(s: string): string {
		return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
	}

	function highlightWikilinks(html: string): string {
		return html.replace(/\[\[([^\]]+)\]\]/g, (_, inner) => {
			const [target, label] = inner.split('|');
			const display = label ?? target;
			const resolved = resolveWikilinkPath(target);
			const cls = resolved ? 'wikilink' : 'wikilink wikilink-broken';
			const dataPart = resolved ? ` data-wikipath="${escAttr(resolved)}"` : '';
			return `<span class="${cls}"${dataPart}>${display}</span>`;
		});
	}

	function preprocessImages(content: string): string {
		return content.replace(
			/!\[\[([^\]]+\.(png|jpe?g|gif|webp|svg))\]\]/gi,
			(_, name) => {
				const src = resolveWikiImage(name);
				return src ? `![${name}](${src})` : `*[missing image: ${name}]*`;
			},
		);
	}

	function renderMarkdown(content: string): string {
		const body = stripFrontmatter(content);
		const processed = preprocessImages(body);
		const html = marked.parse(processed, { gfm: true, breaks: true }) as string;
		return highlightWikilinks(html);
	}

	$: rendered = file?.type === 'md' ? renderMarkdown(localContent) : '';

	// Clickable wikilinks (event delegation on preview div)
	function handlePreviewClick(e: MouseEvent) {
		const span = (e.target as HTMLElement).closest('[data-wikipath]') as HTMLElement | null;
		if (span?.dataset.wikipath) {
			onOpenFile(span.dataset.wikipath);
		}
	}

	// Apply hljs after preview updates
	afterUpdate(() => {
		if ((mode === 'preview' || mode === 'split') && previewEl) {
			const hljs = (window as any).hljs;
			if (hljs) {
				previewEl.querySelectorAll('pre code:not(.hljs)').forEach((el) => {
					hljs.highlightElement(el);
				});
			}
		}
	});

	// ── File download ─────────────────────────────────────────────────────
	function downloadFile() {
		if (!file) return;
		const a = document.createElement('a');
		if (file.content.startsWith('data:')) {
			a.href = file.content;
		} else {
			const blob = new Blob([file.content], { type: 'text/plain' });
			a.href = URL.createObjectURL(blob);
		}
		a.download = file.path.split('/').pop() ?? file.path;
		a.click();
	}

	// ── Text manipulation helpers ─────────────────────────────────────────
	function insertAtCursor(text: string) {
		const el = editorEl;
		if (!el) return;
		const start = el.selectionStart ?? localContent.length;
		const end = el.selectionEnd ?? start;
		localContent = localContent.slice(0, start) + text + localContent.slice(end);
		setTimeout(() => { el.selectionStart = el.selectionEnd = start + text.length; }, 0);
		handleInput();
	}

	function wrapSelection(before: string, after: string) {
		const el = editorEl;
		if (!el) return;
		const start = el.selectionStart;
		const end = el.selectionEnd;
		const selected = localContent.slice(start, end);
		const replacement = before + selected + after;
		localContent = localContent.slice(0, start) + replacement + localContent.slice(end);
		setTimeout(() => {
			if (start === end) {
				el.selectionStart = el.selectionEnd = start + before.length;
			} else {
				el.selectionStart = start;
				el.selectionEnd = start + replacement.length;
			}
		}, 0);
		handleInput();
	}

	// ── Keyboard shortcuts ────────────────────────────────────────────────
	function handleEditorKeydown(e: KeyboardEvent) {
		if (e.key === 'Tab') {
			e.preventDefault();
			insertAtCursor('  ');
			return;
		}
		if (e.ctrlKey || e.metaKey) {
			if (e.key === 'b') { e.preventDefault(); wrapSelection('**', '**'); return; }
			if (e.key === 'i') { e.preventDefault(); wrapSelection('*', '*'); return; }
			if (e.key === 'k') { e.preventDefault(); wrapSelection('[', '](url)'); return; }
		}
	}

	// ── Drag and drop images into editor ──────────────────────────────────
	function handleEditorDragover(e: DragEvent) {
		const hasFiles = Array.from(e.dataTransfer?.items ?? []).some((item) => item.kind === 'file');
		if (hasFiles) { e.preventDefault(); dragOver = true; }
	}

	function handleEditorDragleave() { dragOver = false; }

	function handleEditorDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		const files = Array.from(e.dataTransfer?.files ?? []);
		for (const f of files) {
			const type = getFileType(f.name);
			if (type === 'image') {
				const reader = new FileReader();
				reader.onload = () => {
					const dataUrl = reader.result as string;
					onUploadImage(f.name, dataUrl);
					insertAtCursor(`![[${f.name}]]`);
				};
				reader.readAsDataURL(f);
			}
		}
	}

	// ── Tab close with middle-click ───────────────────────────────────────
	function handleTabMousedown(e: MouseEvent, path: string) {
		if (e.button === 1) { e.preventDefault(); onCloseTab(path); }
	}

	// ── Excalidraw ─────────────────────────────────────────────────────────
	let excalidrawJson      = '';
	let excalidrawJsonSaved = true;
	let excalidrawJsonPath  = '';
	let excalidrawElements: any[]  = [];
	let excalidrawViewBox          = '0 0 800 600';
	let excalidrawSvgContent       = '';

	// Service reachability: null = not yet checked, true/false = result cached for session
	let excalidrawReachable: boolean | null = null;
	let excalidrawServiceChecked = false;
	let excalidrawIframeEl: HTMLIFrameElement | null = null;

	// Re-sync buffer on file switch
	$: if (file?.type === 'excalidraw' && file.path !== excalidrawJsonPath) {
		excalidrawJson      = file.content;
		excalidrawJsonSaved = true;
		excalidrawJsonPath  = file.path;
	}

	// Trigger service check whenever an excalidraw file is active
	$: if (file?.type === 'excalidraw') checkExcalidrawService();

	async function checkExcalidrawService() {
		if (excalidrawServiceChecked) return;
		excalidrawServiceChecked = true;
		excalidrawReachable = null;
		try {
			const ctrl = new AbortController();
			const t = setTimeout(() => ctrl.abort(), 2000);
			await fetch(EXCALIDRAW_URL, { signal: ctrl.signal, mode: 'no-cors' });
			clearTimeout(t);
			excalidrawReachable = true;
		} catch {
			excalidrawReachable = false;
		}
	}

	function handleIframeLoad() {
		if (!excalidrawIframeEl || !file) return;
		try {
			const data = JSON.parse(file.content || '{}');
			excalidrawIframeEl.contentWindow?.postMessage({ type: 'load', data }, '*');
		} catch { /* invalid JSON */ }
	}

	function handleExcalidrawMessage(e: MessageEvent) {
		if (e.data?.type === 'save' && file?.type === 'excalidraw') {
			try {
				const content = JSON.stringify(e.data.data, null, 2);
				onContentChange(file.path, content);
				onDirtyChange(file.path, false);
				excalidrawJsonSaved = true;
			} catch { /* ignore */ }
		}
	}

	onMount(() => { window.addEventListener('message', handleExcalidrawMessage); });
	onDestroy(() => { window.removeEventListener('message', handleExcalidrawMessage); });

	function calcViewBox(els: any[]): string {
		if (!els.length) return '0 0 800 600';
		const xs: number[] = [], ys: number[] = [];
		for (const el of els) {
			xs.push(el.x ?? 0, (el.x ?? 0) + (el.width ?? 0));
			ys.push(el.y ?? 0, (el.y ?? 0) + (el.height ?? 0));
		}
		const pad = 24;
		const minX = Math.min(...xs) - pad, minY = Math.min(...ys) - pad;
		const maxX = Math.max(...xs) + pad, maxY = Math.max(...ys) + pad;
		return `${minX} ${minY} ${maxX - minX} ${maxY - minY}`;
	}

	function renderExcalidrawEl(el: any): string {
		const stroke = el.strokeColor || '#aaaaaa';
		const fill   = (!el.backgroundColor || el.backgroundColor === 'transparent') ? 'none' : el.backgroundColor;
		const sw     = el.strokeWidth ?? 2;
		const x = el.x ?? 0, y = el.y ?? 0, w = el.width ?? 0, h = el.height ?? 0;
		if (el.type === 'rectangle')
			return `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}" rx="3"/>`;
		if (el.type === 'ellipse')
			return `<ellipse cx="${x + w / 2}" cy="${y + h / 2}" rx="${w / 2}" ry="${h / 2}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
		if (el.type === 'diamond') {
			const cx = x + w / 2, cy = y + h / 2;
			return `<polygon points="${cx},${y} ${x + w},${cy} ${cx},${y + h} ${x},${cy}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
		}
		if (el.type === 'text') {
			const fs = el.fontSize || 16;
			const safe = (el.text || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
			return `<text x="${x}" y="${y + fs}" font-size="${fs}" font-family="monospace" fill="${stroke}">${safe}</text>`;
		}
		if (el.type === 'line' || el.type === 'arrow') {
			const pts: [number, number][] = Array.isArray(el.points) ? el.points : [[0, 0], [w, h]];
			const d = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${x + p[0]} ${y + p[1]}`).join(' ');
			const mk = el.type === 'arrow' ? ' marker-end="url(#excali-arrow)"' : '';
			return `<path d="${d}" stroke="${stroke}" stroke-width="${sw}" fill="none"${mk}/>`;
		}
		if (el.type === 'freedraw' && Array.isArray(el.points) && el.points.length > 1) {
			const d = (el.points as [number, number][]).map((p, i) => `${i === 0 ? 'M' : 'L'} ${x + p[0]} ${y + p[1]}`).join(' ');
			return `<path d="${d}" stroke="${stroke}" stroke-width="${sw}" fill="none"/>`;
		}
		return '';
	}

	$: {
		try {
			const parsed = JSON.parse(excalidrawJson || '{}');
			excalidrawElements = Array.isArray(parsed.elements) ? parsed.elements : [];
		} catch { excalidrawElements = []; }
		excalidrawViewBox    = calcViewBox(excalidrawElements);
		excalidrawSvgContent = excalidrawElements.map(renderExcalidrawEl).join('\n');
	}

	function openInExcalidrawCom() {
		const json   = excalidrawJson || '{}';
		const base64 = btoa(unescape(encodeURIComponent(json)));
		window.open(`https://excalidraw.com/#json=${base64}`, '_blank', 'noopener,noreferrer');
	}

	function saveExcalidrawJson() {
		if (!file) return;
		onContentChange(file.path, excalidrawJson);
		onDirtyChange(file.path, false);
		excalidrawJsonSaved = true;
	}
</script>

<svelte:head>
	<link
		rel="stylesheet"
		href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css"
	/>
	<!-- svelte-ignore security-anchor-rel-noopener -->
	<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
</svelte:head>

<div class="editor-wrap">
	<!-- ── Tab bar ──────────────────────────────────────────────────── -->
	<div class="tab-bar" role="tablist">
		{#each openTabs as tab (tab.path)}
			{@const isDirty = (tab.path === activeTabPath && !saved) || (tab.path !== activeTabPath && dirtyPaths.has(tab.path))}
			<div
				class="tab"
				class:active={tab.path === activeTabPath}
				role="tab"
				aria-selected={tab.path === activeTabPath}
				tabindex="0"
				title={tab.path}
				on:click={() => onSelectTab(tab.path)}
				on:mousedown={(e) => handleTabMousedown(e, tab.path)}
				on:keydown={(e) => e.key === 'Enter' && onSelectTab(tab.path)}
			>
				{#if isDirty}<span class="tab-dirty" aria-hidden="true">●</span>{/if}
				<span class="tab-name">{tab.name}</span>
				<button
					class="tab-close"
					aria-label="Close {tab.name}"
					on:click|stopPropagation={() => onCloseTab(tab.path)}
				>
					<X size={10} strokeWidth={2.5} />
				</button>
			</div>
		{/each}
		{#if openTabs.length === 0}
			<div class="tab-empty">no open files</div>
		{/if}
	</div>

	{#if !file}
		<!-- ── Empty state ──────────────────────────────────────────── -->
		<div class="empty-state">
			<div class="empty-icon">◦</div>
			<div class="empty-text">Select a file to open it</div>
			<div class="empty-hint">right-click the sidebar or use Ctrl+P</div>
		</div>
	{:else if file.type === 'md'}
		<!-- ── Markdown editor ──────────────────────────────────────── -->

		<!-- Toolbar -->
		<div class="toolbar">
			<div class="mode-group" role="group" aria-label="View mode">
				<button class="mode-btn" class:active={mode === 'edit'} on:click={() => onModeChange('edit')} title="Edit mode (Ctrl+P → Mode: Edit)">
					<Edit2 size={12} strokeWidth={2} /> Edit
				</button>
				<button class="mode-btn" class:active={mode === 'split'} on:click={() => onModeChange('split')} title="Split mode">
					<Columns size={12} strokeWidth={2} /> Split
				</button>
				<button class="mode-btn" class:active={mode === 'preview'} on:click={() => onModeChange('preview')} title="Preview mode">
					<Eye size={12} strokeWidth={2} /> Preview
				</button>
			</div>
			<div class="toolbar-right">
				<span class="save-badge" class:unsaved={!saved}>{saved ? 'saved' : 'saving…'}</span>
			</div>
		</div>

		<!-- Editor / Preview / Split -->
		<div class="content-area" class:split={mode === 'split'}>
			{#if mode === 'edit' || mode === 'split'}
				<!-- svelte-ignore a11y-no-static-element-interactions -->
				<textarea
					bind:this={editorEl}
					class="editor"
					class:half={mode === 'split'}
					class:dragover={dragOver}
					bind:value={localContent}
					on:input={handleInput}
					on:keydown={handleEditorKeydown}
					on:dragover={handleEditorDragover}
					on:dragleave={handleEditorDragleave}
					on:drop={handleEditorDrop}
					spellcheck="false"
					autocomplete="off"
					autocapitalize="off"
					aria-label="Markdown editor"
				></textarea>
			{/if}
			{#if mode === 'preview' || mode === 'split'}
				<!-- svelte-ignore a11y-no-static-element-interactions -->
				<div
					bind:this={previewEl}
					class="preview"
					class:half={mode === 'split'}
					on:click={handlePreviewClick}
				>
					{@html rendered}
				</div>
			{/if}
		</div>

		<!-- Status bar -->
		<div class="status-bar">
			<span class="status-path">{file.path}</span>
			<div class="status-right">
				<span class="status-stat">{wordCount} words</span>
				<span class="status-sep">·</span>
				<span class="status-stat">{charCount} chars</span>
			</div>
		</div>

	{:else if file.type === 'pdf'}
		<!-- ── PDF viewer ─────────────────────────────────────────── -->
		<div class="binary-header">
			<span class="binary-name">{file.path.split('/').pop()}</span>
			<button class="dl-btn" on:click={downloadFile}><Download size={12} strokeWidth={2} /> Download</button>
		</div>
		{#if file.content.startsWith('data:')}
			<iframe title={file.path} src={file.content} class="pdf-frame"></iframe>
		{:else}
			<div class="unsupported">PDF cannot be displayed — no content stored.</div>
		{/if}

	{:else if file.type === 'image'}
		<!-- ── Image viewer ───────────────────────────────────────── -->
		<div class="binary-header">
			<span class="binary-name">{file.path.split('/').pop()}</span>
			<button class="dl-btn" on:click={downloadFile}><Download size={12} strokeWidth={2} /> Download</button>
		</div>
		<div class="image-wrap">
			<img src={file.content} alt={file.path} class="image-view" />
		</div>

	{:else if file.type === 'excalidraw'}
		<!-- ── Excalidraw viewer ─────────────────────────────────── -->
		<div class="binary-header">
			<span class="binary-name">{file.path.split('/').pop()}</span>
			{#if excalidrawReachable !== true}
				<span class="excalidraw-label">
					{#if excalidrawReachable === null}checking excalidraw service…{:else}excalidraw — edit raw JSON below{/if}
				</span>
			{/if}
			<div class="excalidraw-actions">
				{#if excalidrawReachable !== true}
					<button class="dl-btn" on:click={openInExcalidrawCom}>Open in Excalidraw.com</button>
					<button class="dl-btn" disabled={excalidrawJsonSaved} on:click={saveExcalidrawJson}>
						{excalidrawJsonSaved ? 'saved' : 'save'}
					</button>
				{/if}
			</div>
		</div>

		{#if excalidrawReachable === true}
			<!-- Embedded Excalidraw service -->
			<iframe
				bind:this={excalidrawIframeEl}
				class="excalidraw-frame"
				src={EXCALIDRAW_URL}
				title="Excalidraw editor"
				on:load={handleIframeLoad}
				allow="clipboard-read; clipboard-write"
			></iframe>
		{:else if excalidrawReachable === false}
			<!-- Fallback: SVG preview + JSON editor -->
			{#if excalidrawElements.length}
				<div class="excalidraw-preview">
					<svg viewBox={excalidrawViewBox} xmlns="http://www.w3.org/2000/svg" class="excalidraw-svg">
						<defs>
							<marker id="excali-arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
								<polygon points="0 0, 8 3, 0 6" fill="#aaaaaa"/>
							</marker>
						</defs>
						{@html excalidrawSvgContent}
					</svg>
				</div>
			{:else}
				<div class="excalidraw-empty">no elements · excalidraw service offline · edit JSON below or open in excalidraw.com</div>
			{/if}
			<textarea
				class="excalidraw-json"
				bind:value={excalidrawJson}
				on:input={() => { excalidrawJsonSaved = false; }}
				spellcheck="false"
				aria-label="Excalidraw JSON editor"
			></textarea>
		{:else}
			<!-- null = still checking -->
			<div class="excalidraw-checking">Checking for local Excalidraw service…</div>
		{/if}

	{:else}
		<!-- ── Unsupported file ───────────────────────────────────── -->
		<div class="binary-header">
			<span class="binary-name">{file.path.split('/').pop()}</span>
			<button class="dl-btn" on:click={downloadFile}><Download size={12} strokeWidth={2} /> Download</button>
		</div>
		<div class="unsupported">Preview not available for this file type.</div>
	{/if}
</div>

<style>
	.editor-wrap {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		background: var(--bg0);
		overflow: hidden;
		border-right: 1px solid var(--border);
	}

	/* ── Tabs ─────────────────────────────────────────────────────── */
	.tab-bar {
		display: flex;
		align-items: stretch;
		background: var(--bg1);
		border-bottom: 1px solid var(--border);
		overflow-x: auto;
		flex-shrink: 0;
		min-height: 32px;
	}

	.tab-bar::-webkit-scrollbar { height: 2px; }

	.tab {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		padding: 0 0.7rem;
		cursor: pointer;
		border-right: 1px solid var(--border);
		border-bottom: 2px solid transparent;
		font-family: var(--font-mono);
		font-size: 0.71rem;
		color: var(--text2);
		white-space: nowrap;
		user-select: none;
		outline: none;
		transition: color 0.1s, border-color 0.1s;
		flex-shrink: 0;
		min-height: 32px;
	}

	.tab:hover { color: var(--text1); background: var(--bg2); }

	.tab.active {
		color: var(--text0);
		border-bottom-color: var(--accent3);
		background: var(--bg0);
	}

	.tab-dirty {
		font-size: 0.55rem;
		color: var(--yellow);
		line-height: 1;
		flex-shrink: 0;
	}

	.tab-name { max-width: 140px; overflow: hidden; text-overflow: ellipsis; }

	.tab-close {
		display: flex;
		align-items: center;
		justify-content: center;
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		padding: 2px;
		border-radius: 3px;
		opacity: 0;
		transition: opacity 0.1s, color 0.1s;
	}

	.tab:hover .tab-close,
	.tab.active .tab-close { opacity: 1; }
	.tab-close:hover { color: var(--text0); background: var(--bg2); }

	.tab-empty {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
		display: flex;
		align-items: center;
		padding: 0 0.75rem;
	}

	/* ── Empty state ─────────────────────────────────────────────── */
	.empty-state {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.5rem;
		color: var(--text2);
	}

	.empty-icon { font-size: 2rem; color: var(--border); }
	.empty-text { font-family: var(--font-mono); font-size: 0.82rem; color: var(--text2); }
	.empty-hint { font-family: var(--font-mono); font-size: 0.68rem; color: var(--text2); }

	/* ── Toolbar ─────────────────────────────────────────────────── */
	.toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 0.75rem;
		height: 36px;
		border-bottom: 1px solid var(--border);
		background: var(--bg1);
		flex-shrink: 0;
	}

	.mode-group { display: flex; gap: 2px; }

	.mode-btn {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		padding: 0.2rem 0.5rem;
		background: none;
		border: 1px solid transparent;
		border-radius: var(--radius);
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		cursor: pointer;
		transition: color 0.1s, background 0.1s, border-color 0.1s;
	}

	.mode-btn:hover { color: var(--text1); background: var(--bg2); }

	.mode-btn.active {
		color: var(--accent3);
		background: color-mix(in srgb, var(--accent3) 10%, transparent);
		border-color: color-mix(in srgb, var(--accent3) 30%, transparent);
	}

	.toolbar-right { display: flex; align-items: center; gap: 0.6rem; }

	.save-badge {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--green);
		transition: color 0.2s;
	}

	.save-badge.unsaved { color: var(--yellow); }

	/* ── Content area ────────────────────────────────────────────── */
	.content-area {
		flex: 1;
		display: flex;
		min-height: 0;
		overflow: hidden;
	}

	.content-area.split { flex-direction: row; }

	.editor {
		flex: 1;
		width: 100%;
		padding: 1rem 1.25rem;
		background: var(--bg0);
		border: none;
		outline: none;
		resize: none;
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.83rem;
		line-height: 1.75;
		caret-color: var(--accent3);
		tab-size: 2;
		transition: box-shadow 0.1s;
	}

	.editor.half {
		flex: 1;
		border-right: 1px solid var(--border);
		min-width: 0;
	}

	.editor.dragover {
		box-shadow: inset 0 0 0 2px var(--accent3);
		background: color-mix(in srgb, var(--accent3) 4%, var(--bg0));
	}

	/* ── Preview ─────────────────────────────────────────────────── */
	.preview {
		flex: 1;
		overflow-y: auto;
		padding: 1rem 1.5rem;
		font-family: var(--font-mono);
		font-size: 0.82rem;
		line-height: 1.8;
		color: var(--text0);
		min-width: 0;
	}

	.preview.half { flex: 1; background: var(--bg1); }

	.preview :global(h1) {
		font-size: 1.15em; font-weight: 700; color: var(--accent4);
		margin: 0 0 0.6em; padding-bottom: 0.3em;
		border-bottom: 1px solid var(--border);
	}
	.preview :global(h2) { font-size: 0.95em; font-weight: 700; color: var(--accent3); margin: 1em 0 0.35em; }
	.preview :global(h3) { font-size: 0.87em; font-weight: 700; color: var(--accent2); margin: 0.8em 0 0.25em; }
	.preview :global(h4) { font-size: 0.82em; font-weight: 700; color: var(--text1); margin: 0.7em 0 0.2em; }
	.preview :global(p) { margin: 0 0 0.5em; }
	.preview :global(ul), .preview :global(ol) { margin: 0 0 0.5em 1.2em; }
	.preview :global(li) { margin: 0.1em 0; }
	.preview :global(li input[type="checkbox"]) { margin-right: 0.35em; }
	.preview :global(a) { color: var(--accent2); }
	.preview :global(strong) { color: var(--text0); font-weight: 700; }
	.preview :global(em) { color: var(--text1); font-style: italic; }
	.preview :global(code) {
		font-family: var(--font-mono); font-size: 0.85em;
		color: var(--accent); background: color-mix(in srgb, var(--accent) 12%, var(--bg2));
		border: 1px solid color-mix(in srgb, var(--accent) 20%, var(--border));
		border-radius: 3px; padding: 0.05em 0.3em;
	}
	.preview :global(pre) {
		background: var(--bg1) !important;
		border: 1px solid var(--border);
		border-left: 3px solid var(--accent2);
		border-radius: var(--radius);
		padding: 0.7rem 1rem;
		overflow-x: auto;
		margin: 0.6em 0;
		font-size: 0.78rem;
		line-height: 1.6;
	}
	.preview :global(pre code) { background: none !important; border: none; padding: 0; color: var(--text0); font-size: inherit; }
	.preview :global(blockquote) {
		border-left: 3px solid var(--accent2); margin: 0.6em 0;
		padding: 0.3em 0.85em; color: var(--text1);
		background: color-mix(in srgb, var(--accent2) 6%, transparent);
		border-radius: 0 3px 3px 0;
	}
	.preview :global(table) { border-collapse: collapse; width: 100%; margin: 0.6em 0; font-size: 0.8em; }
	.preview :global(th), .preview :global(td) { border: 1px solid var(--border); padding: 0.35em 0.65em; text-align: left; }
	.preview :global(th) { background: var(--bg2); color: var(--text1); font-weight: 600; }
	.preview :global(tr:nth-child(even)) { background: color-mix(in srgb, var(--bg2) 40%, transparent); }
	.preview :global(hr) { border: none; border-top: 1px solid var(--border); margin: 1em 0; }
	.preview :global(img) { max-width: 100%; border-radius: var(--radius); margin: 0.5em 0; }

	/* ── Wikilinks ───────────────────────────────────────────────── */
	.preview :global(.wikilink) {
		color: var(--accent);
		cursor: pointer;
		text-decoration: underline;
		text-decoration-color: color-mix(in srgb, var(--accent) 40%, transparent);
		text-underline-offset: 2px;
	}
	.preview :global(.wikilink:hover) { text-decoration-color: var(--accent); }
	.preview :global(.wikilink-broken) {
		color: var(--red);
		text-decoration-color: color-mix(in srgb, var(--red) 40%, transparent);
		cursor: not-allowed;
	}

	/* ── Status bar ──────────────────────────────────────────────── */
	.status-bar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0 0.85rem;
		height: 26px;
		background: var(--bg1);
		border-top: 1px solid var(--border);
		flex-shrink: 0;
	}

	.status-path {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 55%;
	}

	.status-right { display: flex; align-items: center; gap: 0.4rem; }
	.status-stat { font-family: var(--font-mono); font-size: 0.62rem; color: var(--text2); }
	.status-sep { color: var(--border); font-size: 0.65rem; }

	/* ── Binary / unsupported viewers ────────────────────────────── */
	.binary-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 0.85rem;
		border-bottom: 1px solid var(--border);
		background: var(--bg1);
		flex-shrink: 0;
	}

	.binary-name { font-family: var(--font-mono); font-size: 0.75rem; color: var(--text0); }

	.dl-btn {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		padding: 0.22rem 0.6rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		cursor: pointer;
		text-decoration: none;
		transition: color 0.1s, border-color 0.1s;
	}

	.dl-btn:hover { color: var(--text0); border-color: var(--accent2); }

	.pdf-frame { flex: 1; width: 100%; border: none; background: var(--bg0); }

	.image-wrap {
		flex: 1;
		overflow: auto;
		display: flex;
		align-items: flex-start;
		justify-content: center;
		padding: 1rem;
		background: var(--bg0);
	}

	.image-view { max-width: 100%; border-radius: var(--radius); }

	.excalidraw-label {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text2);
		flex: 1;
		padding: 0 0.5rem;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.excalidraw-actions {
		display: flex;
		gap: 0.4rem;
		flex-shrink: 0;
	}

	.excalidraw-preview {
		flex-shrink: 0;
		max-height: 260px;
		border-bottom: 1px solid var(--border);
		background: var(--bg1);
		overflow: auto;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 0.75rem;
	}

	.excalidraw-svg {
		max-width: 100%;
		max-height: 220px;
		height: auto;
	}

	.excalidraw-empty {
		flex-shrink: 0;
		padding: 0.65rem 1rem;
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
		border-bottom: 1px solid var(--border);
	}

	.excalidraw-frame {
		flex: 1;
		width: 100%;
		border: none;
		background: var(--bg0);
		display: block;
	}

	.excalidraw-checking {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text2);
	}

	.excalidraw-json {
		flex: 1;
		min-height: 0;
		resize: none;
		background: var(--bg0);
		border: none;
		outline: none;
		padding: 0.85rem 1.25rem;
		font-family: var(--font-mono);
		font-size: 0.78rem;
		line-height: 1.7;
		color: var(--text1);
		tab-size: 2;
		white-space: pre;
	}

	.unsupported {
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text2);
	}
</style>
