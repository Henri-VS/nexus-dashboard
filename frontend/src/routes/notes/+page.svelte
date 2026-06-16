<script lang="ts">
	// /notes — Full Obsidian-replacement notes system
	// TODO: replace localStorage with GET/POST /api/notes endpoints when vault path is configured.
	// The backend/app/routers/notes.py already exists — wire it up later.

	import { onMount, onDestroy } from 'svelte';
	import { ChevronRight, ChevronLeft } from '@lucide/svelte';
	import NotesSidebar from '$lib/components/notes/NotesSidebar.svelte';
	import NotesEditor from '$lib/components/notes/NotesEditor.svelte';
	import NotesProperties from '$lib/components/notes/NotesProperties.svelte';
	import CommandPalette from '$lib/components/notes/CommandPalette.svelte';
	import {
		type StoredFile, type StoredVault, type Tab,
		getFileType, createDefaultVaults,
	} from '$lib/components/notes/types';

	const STORAGE_KEY     = 'dashboard-notes-v1';
	const NOTES_PAGE_KEY  = 'dashboard_config.notes';
	const SIDEBAR_MIN     = 160;
	const SIDEBAR_MAX     = 480;
	const SIDEBAR_DEFAULT = 240;
	const PROPS_MIN       = 200;
	const PROPS_MAX       = 500;
	const PROPS_DEFAULT   = 260;

	// ── Vault state ──────────────────────────────────────────────────────────
	let vaultData: Record<string, StoredVault> = {};
	let activeVaultId = 'main';

	// ── Per-vault tab state ──────────────────────────────────────────────────
	let vaultTabState: Record<string, { tabs: Tab[]; active: string }> = {};

	// ── Dirty tracking ───────────────────────────────────────────────────────
	let dirtyPaths = new Set<string>();

	// ── UI state ─────────────────────────────────────────────────────────────
	let propsOpen = true;
	let editorMode: 'edit' | 'preview' | 'split' = 'split';
	let showPalette = false;
	let mounted = false;

	// ── Sidebar resize ────────────────────────────────────────────────────────
	let sidebarWidth = SIDEBAR_DEFAULT;
	let isResizing   = false;
	let resizeStartX = 0;
	let resizeStartW = 0;

	// ── Properties panel resize ───────────────────────────────────────────────
	let propsWidth     = PROPS_DEFAULT;
	let propsResizing  = false;
	let propsResStartX = 0;
	let propsResStartW = 0;

	function startSidebarResize(e: MouseEvent | TouchEvent) {
		const cx     = 'touches' in e ? (e as TouchEvent).touches[0].clientX : (e as MouseEvent).clientX;
		isResizing   = true;
		resizeStartX = cx;
		resizeStartW = sidebarWidth;
		e.preventDefault();
	}

	function startPropsResize(e: MouseEvent | TouchEvent) {
		const cx       = 'touches' in e ? (e as TouchEvent).touches[0].clientX : (e as MouseEvent).clientX;
		propsResizing  = true;
		propsResStartX = cx;
		propsResStartW = propsWidth;
		e.preventDefault();
	}

	function onResizeMove(e: MouseEvent | TouchEvent) {
		const cx = 'touches' in e ? (e as TouchEvent).touches[0].clientX : (e as MouseEvent).clientX;
		if (isResizing) {
			sidebarWidth = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, resizeStartW + (cx - resizeStartX)));
		}
		if (propsResizing) {
			propsWidth = Math.min(PROPS_MAX, Math.max(PROPS_MIN, propsResStartW - (cx - propsResStartX)));
		}
	}

	function stopResize() {
		if (!isResizing && !propsResizing) return;
		isResizing    = false;
		propsResizing = false;
		try {
			const raw = localStorage.getItem(NOTES_PAGE_KEY);
			const cfg = raw ? JSON.parse(raw) : {};
			localStorage.setItem(NOTES_PAGE_KEY, JSON.stringify({ ...cfg, sidebarWidth, propsWidth }));
		} catch { /* ignore */ }
	}

	onDestroy(() => {
		if (typeof window !== 'undefined') {
			window.removeEventListener('mousemove', onResizeMove);
			window.removeEventListener('mouseup',   stopResize);
		}
	});

	// ── Sidebar ref for exported methods ─────────────────────────────────────
	let sidebarRef: NotesSidebar;

	// ── Derived ──────────────────────────────────────────────────────────────
	$: vaultList = Object.values(vaultData);
	$: activeVault = vaultData[activeVaultId] ?? null;
	$: currentVTS = vaultTabState[activeVaultId] ?? { tabs: [], active: '' };
	$: openTabs = currentVTS.tabs;
	$: activeTabPath = currentVTS.active;
	$: activeFile = activeVault?.files[activeTabPath] ?? null;
	$: allVaultFiles = activeVault?.files ?? {};

	// ── Persistence ───────────────────────────────────────────────────────────
	function loadState() {
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			if (raw) {
				const parsed = JSON.parse(raw);
				vaultData = parsed.vaults ?? {};
				activeVaultId = parsed.activeVaultId ?? 'main';
				vaultTabState = parsed.vaultTabState ?? {};
			}
		} catch {
			/* ignore */
		}
		if (Object.keys(vaultData).length === 0) {
			vaultData = createDefaultVaults();
		}
	}

	function saveState() {
		if (!mounted) return;
		try {
			localStorage.setItem(STORAGE_KEY, JSON.stringify({
				vaults: vaultData,
				activeVaultId,
				vaultTabState,
			}));
		} catch {
			/* localStorage full — binary files too large */
		}
	}

	$: if (mounted) { void vaultData; void vaultTabState; void activeVaultId; saveState(); }

	onMount(() => {
		loadState();
		mounted = true;

		// Load layout preferences
		try {
			const raw = localStorage.getItem(NOTES_PAGE_KEY);
			if (raw) {
				const cfg = JSON.parse(raw);
				if (typeof cfg.sidebarWidth === 'number')
					sidebarWidth = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, cfg.sidebarWidth));
				if (typeof cfg.propsWidth === 'number')
					propsWidth = Math.min(PROPS_MAX, Math.max(PROPS_MIN, cfg.propsWidth));
			}
		} catch { /* ignore */ }

		window.addEventListener('mousemove', onResizeMove);
		window.addEventListener('mouseup',   stopResize);

		// Open first file of active vault if no saved tabs
		const vts = vaultTabState[activeVaultId];
		if (!vts || vts.tabs.length === 0) {
			const vault = vaultData[activeVaultId];
			if (vault) {
				const firstMd = Object.values(vault.files).find((f) => f.type === 'md');
				if (firstMd) openFile(firstMd.path);
			}
		}
	});

	// ── Tab state helpers ────────────────────────────────────────────────────
	function updateTabState(tabs: Tab[], active: string) {
		vaultTabState = { ...vaultTabState, [activeVaultId]: { tabs, active } };
	}

	// ── File operations ───────────────────────────────────────────────────────
	function openFile(path: string) {
		if (!activeVault?.files[path]) return;

		// Already open → just switch focus, no new tab
		if (openTabs.some((t) => t.path === path)) {
			updateTabState(openTabs, path);
			return;
		}

		// Build the new tab and insert it immediately to the right of the active tab
		const f = activeVault.files[path];
		const newTab: Tab = {
			path,
			vaultId: activeVaultId,
			name: path.split('/').pop() ?? path,
			fileType: f.type,
		};
		let tabs = [...openTabs];
		const activeIdx = tabs.findIndex((t) => t.path === activeTabPath);
		if (activeIdx >= 0) {
			tabs.splice(activeIdx + 1, 0, newTab);
		} else {
			tabs.push(newTab);
		}

		// Enforce max 10 tabs: evict the oldest non-active, non-new tab from the left
		const MAX_TABS = 10;
		if (tabs.length > MAX_TABS) {
			const victimIdx = tabs.findIndex((t) => t.path !== path && t.path !== activeTabPath);
			if (victimIdx >= 0) {
				dirtyPaths.delete(tabs[victimIdx].path);
				dirtyPaths = new Set(dirtyPaths);
				tabs.splice(victimIdx, 1);
			}
		}

		updateTabState(tabs, path);
	}

	function closeTab(path: string) {
		const closedIdx = openTabs.findIndex((t) => t.path === path);
		const tabs = openTabs.filter((t) => t.path !== path);

		let active = activeTabPath;
		if (activeTabPath === path) {
			if (closedIdx > 0) {
				// Go to the tab on the left
				active = tabs[closedIdx - 1]?.path ?? '';
			} else {
				// Was the first tab; go to the new first (right)
				active = tabs[0]?.path ?? '';
			}
		}

		updateTabState(tabs, active);
		dirtyPaths.delete(path);
		dirtyPaths = new Set(dirtyPaths);
	}

	function selectTab(path: string) {
		updateTabState(openTabs, path);
	}

	// ── Content changes ────────────────────────────────────────────────────
	function handleContentChange(path: string, content: string) {
		if (!activeVault) return;
		const file = activeVault.files[path];
		if (!file) return;
		vaultData = {
			...vaultData,
			[activeVaultId]: {
				...activeVault,
				files: { ...activeVault.files, [path]: { ...file, content, modified: Date.now() } },
			},
		};
	}

	function handleFrontmatterChange(path: string, newContent: string) {
		handleContentChange(path, newContent);
	}

	function handleDirtyChange(path: string, dirty: boolean) {
		if (dirty) dirtyPaths.add(path); else dirtyPaths.delete(path);
		dirtyPaths = new Set(dirtyPaths);
	}

	// ── Sidebar events ────────────────────────────────────────────────────
	function handleNewNote(path: string, content: string) {
		if (!activeVault) return;
		const type = getFileType(path.split('/').pop() ?? path);
		const now = Date.now();
		const file: StoredFile = { path, content, type, created: now, modified: now };
		vaultData = {
			...vaultData,
			[activeVaultId]: { ...activeVault, files: { ...activeVault.files, [path]: file } },
		};
		openFile(path);
	}

	function handleNewFolder(folderPath: string) {
		handleNewNote(`${folderPath}/.gitkeep`, '');
	}

	function handleRenameFile(oldPath: string, newName: string) {
		if (!activeVault) return;
		const file = activeVault.files[oldPath];
		if (!file) return;
		const dir = oldPath.includes('/') ? oldPath.slice(0, oldPath.lastIndexOf('/') + 1) : '';
		const newPath = dir + newName;
		const updatedFiles = { ...activeVault.files };
		delete updatedFiles[oldPath];
		updatedFiles[newPath] = { ...file, path: newPath };
		vaultData = { ...vaultData, [activeVaultId]: { ...activeVault, files: updatedFiles } };
		const tabs = openTabs.map((t) =>
			t.path === oldPath
				? { ...t, path: newPath, name: newName, fileType: getFileType(newName) }
				: t,
		);
		const active = activeTabPath === oldPath ? newPath : activeTabPath;
		updateTabState(tabs, active);
	}

	function handleMoveFile(oldPath: string, newFolder: string) {
		if (!activeVault) return;
		const file = activeVault.files[oldPath];
		if (!file) return;
		const name = oldPath.split('/').pop() ?? oldPath;
		const newPath = newFolder ? `${newFolder}/${name}` : name;
		if (newPath === oldPath) return;
		const updatedFiles = { ...activeVault.files };
		delete updatedFiles[oldPath];
		updatedFiles[newPath] = { ...file, path: newPath };
		vaultData = { ...vaultData, [activeVaultId]: { ...activeVault, files: updatedFiles } };
		const tabs = openTabs.map((t) =>
			t.path === oldPath ? { ...t, path: newPath, name } : t,
		);
		const active = activeTabPath === oldPath ? newPath : activeTabPath;
		updateTabState(tabs, active);
	}

	function handleDeleteFile(path: string) {
		if (!activeVault) return;
		const updatedFiles = { ...activeVault.files };
		const isFolder = !activeVault.files[path];
		if (isFolder) {
			for (const key of Object.keys(updatedFiles)) {
				if (key === path || key.startsWith(path + '/')) delete updatedFiles[key];
			}
		} else {
			delete updatedFiles[path];
		}
		vaultData = { ...vaultData, [activeVaultId]: { ...activeVault, files: updatedFiles } };
		const tabs = openTabs.filter((t) => updatedFiles[t.path]);
		const active = updatedFiles[activeTabPath] ? activeTabPath : (tabs[tabs.length - 1]?.path ?? '');
		updateTabState(tabs, active);
	}

	function handleChangeVault(id: string) {
		activeVaultId = id;
		// Restore saved tab state or open first file
		const vts = vaultTabState[id];
		if (!vts || vts.tabs.length === 0) {
			const vault = vaultData[id];
			if (vault) {
				const firstMd = Object.values(vault.files).find((f) => f.type === 'md');
				if (firstMd) {
					const tab: Tab = { path: firstMd.path, vaultId: id, name: firstMd.path.split('/').pop() ?? '', fileType: firstMd.type };
					vaultTabState = { ...vaultTabState, [id]: { tabs: [tab], active: firstMd.path } };
				}
			}
		}
	}

	function handleNewVault(id: string, name: string) {
		vaultData = { ...vaultData, [id]: { id, name, files: {} } };
		handleChangeVault(id);
	}

	function handleUploadFiles(files: StoredFile[]) {
		if (!activeVault) return;
		const newFiles = { ...activeVault.files };
		for (const f of files) newFiles[f.path] = f;
		vaultData = { ...vaultData, [activeVaultId]: { ...activeVault, files: newFiles } };
		// Open first md file if any
		const firstMd = files.find((f) => f.type === 'md');
		if (firstMd) openFile(firstMd.path);
	}

	function handleUploadImage(name: string, dataUrl: string) {
		if (!activeVault) return;
		const path = `Assets/${name}`;
		const now = Date.now();
		const imgFile: StoredFile = { path, content: dataUrl, type: 'image', created: now, modified: now };
		vaultData = {
			...vaultData,
			[activeVaultId]: { ...activeVault, files: { ...activeVault.files, [path]: imgFile } },
		};
	}

	// ── Global keyboard handler ───────────────────────────────────────────
	function handleGlobalKeydown(e: KeyboardEvent) {
		if ((e.ctrlKey || e.metaKey) && e.key === 'p') {
			e.preventDefault();
			showPalette = !showPalette;
		}
		if (e.key === 'Escape' && showPalette) {
			showPalette = false;
		}
	}
</script>

<svelte:head>
	<title>Nexus — Notes</title>
</svelte:head>

<svelte:window on:keydown={handleGlobalKeydown} />

<div class="notes-page">
	<!-- ── Left: sidebar ─────────────────────────────────────────── -->
	<div class="sidebar-wrapper" style="width: {sidebarWidth}px">
		<NotesSidebar
			bind:this={sidebarRef}
			vaults={vaultList}
			{activeVaultId}
			activeFilePath={activeTabPath}
			{openTabs}
			onSelectFile={openFile}
			onNewNote={handleNewNote}
			onNewFolder={handleNewFolder}
			onRenameFile={handleRenameFile}
			onDeleteFile={handleDeleteFile}
			onMoveFile={handleMoveFile}
			onChangeVault={handleChangeVault}
			onNewVault={handleNewVault}
			onUploadFiles={handleUploadFiles}
		/>
	</div>

	<!-- ── Sidebar resize handle ────────────────────────────────── -->
	<div
		class="sidebar-resize"
		class:resizing={isResizing}
		role="separator"
		aria-label="Resize sidebar"
		aria-orientation="vertical"
		on:mousedown={startSidebarResize}
	></div>

	<!-- ── Middle: editor ────────────────────────────────────────── -->
	<NotesEditor
		file={activeFile}
		{openTabs}
		{activeTabPath}
		allFiles={allVaultFiles}
		mode={editorMode}
		{dirtyPaths}
		onContentChange={handleContentChange}
		onCloseTab={closeTab}
		onSelectTab={selectTab}
		onModeChange={(m) => (editorMode = m)}
		onOpenFile={openFile}
		onDirtyChange={handleDirtyChange}
		onUploadImage={handleUploadImage}
	/>

	<!-- ── Properties resize handle ───────────────────────────── -->
	{#if propsOpen}
		<div
			class="props-resize"
			class:resizing={propsResizing}
			role="separator"
			aria-label="Resize properties panel"
			aria-orientation="vertical"
			on:mousedown={startPropsResize}
			on:touchstart|preventDefault={startPropsResize}
		></div>
	{/if}

	<!-- ── Right: properties + toggle ───────────────────────────── -->
	<div class="props-wrap" style="width: {propsOpen ? propsWidth + 'px' : '0px'}">
		<button
			class="props-toggle"
			class:open={propsOpen}
			on:click={() => (propsOpen = !propsOpen)}
			title={propsOpen ? 'Close properties' : 'Open properties'}
			aria-label={propsOpen ? 'Close properties' : 'Open properties'}
		>
			{#if propsOpen}
				<ChevronRight size={14} strokeWidth={2} />
			{:else}
				<ChevronLeft size={14} strokeWidth={2} />
			{/if}
		</button>

		<NotesProperties
			file={activeFile}
			allFiles={allVaultFiles}
			open={propsOpen}
			onFrontmatterChange={handleFrontmatterChange}
			onOpenFile={openFile}
		/>
	</div>
</div>

<!-- ── Command palette (Ctrl+P) ──────────────────────────────────── -->
{#if showPalette}
	<CommandPalette
		allFiles={allVaultFiles}
		vaults={vaultList}
		currentMode={editorMode}
		{propsOpen}
		onOpenFile={openFile}
		onNewNote={() => sidebarRef?.openNewNote()}
		onNewNoteFromTemplate={() => sidebarRef?.openNewNote('', 'blank')}
		onSwitchVault={handleChangeVault}
		onToggleMode={(m) => (editorMode = m)}
		onToggleProps={() => (propsOpen = !propsOpen)}
		onClose={() => (showPalette = false)}
	/>
{/if}

<style>
	/*
	  86px = topbar (40px) + quickbar (44px) + 2px borders.
	  Negative margin + full-bleed width fills the viewport without double scrollbar.
	*/
	.notes-page {
		display: flex;
		height: calc(100vh - 86px);
		overflow: hidden;
		margin: -1.5rem;
		width: calc(100% + 3rem);
		background: var(--bg0);
	}

	/* ── Sidebar resize ─────────────────────────────────────────── */
	.sidebar-wrapper {
		flex-shrink: 0;
		overflow: hidden;
		display: flex;
	}

	.sidebar-wrapper :global(> *) {
		width: 100% !important;
		min-width: 0 !important;
		max-width: none !important;
		flex-shrink: 0;
	}

	.sidebar-resize {
		width: 4px;
		flex-shrink: 0;
		background: var(--border);
		cursor: col-resize;
		transition: background 0.12s;
		position: relative;
		z-index: 10;
	}

	.sidebar-resize:hover,
	.sidebar-resize.resizing {
		background: var(--accent);
	}

	/* ── Properties resize handle ──────────────────────────────── */
	.props-resize {
		width: 4px;
		flex-shrink: 0;
		background: var(--border);
		cursor: col-resize;
		transition: background 0.12s;
		position: relative;
		z-index: 10;
		touch-action: none;
	}
	.props-resize:hover, .props-resize.resizing { background: var(--accent2); }

	/* ── Properties wrapper ─────────────────────────────────────── */
	.props-wrap {
		display: flex;
		flex-shrink: 0;
		position: relative;
		overflow: hidden;
		transition: width 0.05s;
	}

	.props-toggle {
		position: absolute;
		left: -20px;
		top: 50%;
		transform: translateY(-50%);
		z-index: 10;
		width: 20px;
		height: 48px;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-right: none;
		border-radius: 6px 0 0 6px;
		color: var(--text2);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition: color 0.1s, background 0.1s;
	}

	.props-toggle:hover { color: var(--text0); background: var(--bg2); }

	@media (max-width: 768px) {
		.sidebar-wrapper { display: none; }
		.sidebar-resize  { display: none; }
	}
</style>
