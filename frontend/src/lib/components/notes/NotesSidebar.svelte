<script lang="ts">
	import {
		File, Folder, FolderOpen, FileText, Image, Plus, FolderPlus,
		Upload, ChevronRight, ChevronDown, PenTool, Search, X,
	} from '@lucide/svelte';
	import {
		type StoredVault, type StoredFile, type DisplayNode, type Tab,
		buildDisplayTree, getFileType, TEMPLATES,
	} from './types';

	// ── Props ───────────────────────────────────────────────────────────────
	export let vaults: StoredVault[] = [];
	export let activeVaultId: string = '';
	export let activeFilePath: string = '';
	export let openTabs: Tab[] = [];

	export let onSelectFile: (path: string) => void = () => {};
	export let onNewNote: (path: string, content: string) => void = () => {};
	export let onNewFolder: (path: string) => void = () => {};
	export let onRenameFile: (oldPath: string, newName: string) => void = () => {};
	export let onDeleteFile: (path: string) => void = () => {};
	export let onMoveFile: (oldPath: string, newFolder: string) => void = () => {};
	export let onChangeVault: (id: string) => void = () => {};
	export let onNewVault: (id: string, name: string) => void = () => {};
	export let onUploadFiles: (files: StoredFile[]) => void = () => {};

	// ── Internal state ──────────────────────────────────────────────────────
	let collapsed = new Set<string>();
	let assetsCollapsed = false;
	let contextMenu: { x: number; y: number; node: DisplayNode | null } | null = null;
	let showNewNote = false;
	let showNewFolder = false;
	let showRename = false;
	let showMove = false;
	let showSearch = false;
	let searchQuery = '';
	let newNoteName = '';
	let newNoteTemplate = 'blank';
	let newNoteType: 'md' | 'excalidraw' = 'md';
	let newNoteFolderPath = '';
	let newFolderName = '';
	let newFolderParent = '';
	let renamePath = '';
	let renameName = '';
	let movePath = '';
	let moveTarget = '';
	let newNoteInput: HTMLInputElement;
	let newFolderInput: HTMLInputElement;
	let renameInput: HTMLInputElement;
	let searchInput: HTMLInputElement;
	let fileInput: HTMLInputElement;
	let vaultSelect: HTMLSelectElement;

	// ── Derived ─────────────────────────────────────────────────────────────
	$: activeVault = vaults.find((v) => v.id === activeVaultId) ?? null;
	$: allDisplayNodes = activeVault ? buildDisplayTree(activeVault.files, collapsed) : [];
	$: displayNodes = searchQuery.trim() ? filterNodes(allDisplayNodes, searchQuery.toLowerCase(), activeVault?.files ?? {}) : allDisplayNodes;
	$: vaultFolders = getVaultFolders(activeVault?.files ?? {});
	$: assetFiles = Object.entries(activeVault?.files ?? {})
		.filter(([, f]) => f.type === 'image')
		.map(([path, f]) => ({ path, name: path.split('/').pop() ?? path, src: f.content }));

	function getVaultFolders(files: Record<string, StoredFile>): string[] {
		const s = new Set<string>(['']);
		for (const path of Object.keys(files)) {
			const parts = path.split('/');
			for (let i = 1; i < parts.length; i++) {
				s.add(parts.slice(0, i).join('/'));
			}
		}
		return Array.from(s).sort();
	}

	function filterNodes(nodes: DisplayNode[], q: string, files: Record<string, StoredFile>): DisplayNode[] {
		const matchPaths = new Set<string>();
		for (const node of nodes) {
			if (node.kind === 'file') {
				const nameMatch = node.name.toLowerCase().includes(q);
				const contentMatch = (files[node.path]?.content ?? '').toLowerCase().includes(q);
				if (nameMatch || contentMatch) {
					matchPaths.add(node.path);
					const parts = node.path.split('/');
					for (let i = 1; i < parts.length; i++) {
						matchPaths.add(parts.slice(0, i).join('/'));
					}
				}
			}
		}
		return nodes.filter((n) => matchPaths.has(n.path));
	}

	// ── Tree interactions ────────────────────────────────────────────────────
	function toggleFolder(path: string) {
		if (collapsed.has(path)) { collapsed.delete(path); } else { collapsed.add(path); }
		collapsed = new Set(collapsed);
	}

	function handleNodeKeydown(e: KeyboardEvent, node: DisplayNode) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			if (node.kind === 'folder') toggleFolder(node.path);
			else onSelectFile(node.path);
		}
	}

	// ── Context menu ─────────────────────────────────────────────────────────
	function openContextMenu(e: MouseEvent, node: DisplayNode | null) {
		e.preventDefault();
		e.stopPropagation();
		contextMenu = { x: e.clientX, y: e.clientY, node };
	}

	function closeContextMenu() { contextMenu = null; }

	function ctxParentFolder(node: DisplayNode | null): string {
		if (!node) return '';
		if (node.kind === 'folder') return node.path;
		return node.path.includes('/') ? node.path.slice(0, node.path.lastIndexOf('/')) : '';
	}

	function ctxNewNote() {
		newNoteFolderPath = ctxParentFolder(contextMenu?.node ?? null);
		newNoteName = '';
		newNoteTemplate = 'blank';
		newNoteType = 'md';
		closeContextMenu();
		showNewNote = true;
		setTimeout(() => newNoteInput?.focus(), 30);
	}

	function ctxNewFolder() {
		newFolderParent = ctxParentFolder(contextMenu?.node ?? null);
		newFolderName = '';
		closeContextMenu();
		showNewFolder = true;
		setTimeout(() => newFolderInput?.focus(), 30);
	}

	function ctxRename() {
		if (!contextMenu?.node) return;
		renamePath = contextMenu.node.path;
		renameName = contextMenu.node.name;
		closeContextMenu();
		showRename = true;
		setTimeout(() => {
			renameInput?.focus();
			const dot = renameName.lastIndexOf('.');
			renameInput?.setSelectionRange(0, dot > 0 ? dot : renameName.length);
		}, 30);
	}

	function ctxMove() {
		if (!contextMenu?.node || contextMenu.node.kind !== 'file') return;
		movePath = contextMenu.node.path;
		const currentFolder = movePath.includes('/') ? movePath.slice(0, movePath.lastIndexOf('/')) : '';
		moveTarget = currentFolder;
		closeContextMenu();
		showMove = true;
	}

	function ctxDelete() {
		if (!contextMenu?.node) return;
		const { path, kind } = contextMenu.node;
		closeContextMenu();
		const label = kind === 'folder' ? `folder "${path}" and all its files` : `"${path}"`;
		if (confirm(`Delete ${label}?`)) {
			onDeleteFile(path);
		}
	}

	// ── New note modal ─────────────────────────────────────────────────────
	export function openNewNote(folderPath = '', templateId = 'blank') {
		newNoteFolderPath = folderPath;
		newNoteName = '';
		newNoteTemplate = templateId;
		newNoteType = 'md';
		showNewNote = true;
		setTimeout(() => newNoteInput?.focus(), 30);
	}

	export function openNewNoteFromTemplate() {
		openNewNote('', 'blank');
	}

	function confirmNewNote() {
		const raw = newNoteName.trim();
		if (!raw) return;

		let name: string;
		let content: string;

		if (newNoteType === 'excalidraw') {
			name    = raw.endsWith('.excalidraw') ? raw : raw + '.excalidraw';
			content = JSON.stringify({
				type: 'excalidraw', version: 2, source: 'dashboard',
				elements: [], appState: { viewBackgroundColor: '#1e1e2e', currentItemFontFamily: 1 }, files: {},
			}, null, 2);
		} else {
			name    = raw.endsWith('.md') ? raw : raw + '.md';
			const tpl = TEMPLATES.find((t) => t.id === newNoteTemplate);
			content = tpl ? tpl.content() : '';
		}

		const path = newNoteFolderPath ? `${newNoteFolderPath}/${name}` : name;
		showNewNote = false;
		onNewNote(path, content);
	}

	function cancelNewNote() { showNewNote = false; }

	// ── New folder modal ──────────────────────────────────────────────────
	function openNewFolderModal(parentPath = '') {
		newFolderParent = parentPath;
		newFolderName = '';
		showNewFolder = true;
		setTimeout(() => newFolderInput?.focus(), 30);
	}

	function confirmNewFolder() {
		const raw = newFolderName.trim();
		if (!raw) return;
		const path = newFolderParent ? `${newFolderParent}/${raw}` : raw;
		showNewFolder = false;
		onNewFolder(path);
	}

	function cancelNewFolder() { showNewFolder = false; }

	// ── Rename modal ──────────────────────────────────────────────────────
	function confirmRename() {
		const raw = renameName.trim();
		if (!raw || !renamePath) return;
		showRename = false;
		onRenameFile(renamePath, raw);
	}

	function cancelRename() { showRename = false; }

	// ── Move to folder modal ──────────────────────────────────────────────
	function confirmMove() {
		if (!movePath) return;
		showMove = false;
		onMoveFile(movePath, moveTarget);
	}

	function cancelMove() { showMove = false; }

	// ── Vault switcher ────────────────────────────────────────────────────
	function handleVaultChange(e: Event) {
		const val = (e.currentTarget as HTMLSelectElement).value;
		if (val === '__new__') {
			const name = prompt('New vault name:')?.trim();
			if (!name) {
				setTimeout(() => { if (vaultSelect) vaultSelect.value = activeVaultId; }, 0);
				return;
			}
			const id = name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
			onNewVault(id, name);
		} else {
			onChangeVault(val);
		}
	}

	// ── Upload ────────────────────────────────────────────────────────────
	async function handleUpload(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		if (!input.files?.length) return;
		const results: StoredFile[] = [];
		for (const f of Array.from(input.files)) {
			const type = getFileType(f.name);
			let content = '';
			if (type === 'md' || type === 'excalidraw') {
				content = await f.text();
			} else {
				content = await new Promise<string>((res) => {
					const reader = new FileReader();
					reader.onload = () => res(reader.result as string);
					reader.readAsDataURL(f);
				});
			}
			const path = type === 'image' ? `Assets/${f.name}` : f.name;
			results.push({ path, content, type, created: Date.now(), modified: Date.now() });
		}
		onUploadFiles(results);
		input.value = '';
	}

	// ── Keyboard shortcuts ────────────────────────────────────────────────
	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') {
			closeContextMenu();
			showNewNote = false;
			showNewFolder = false;
			showRename = false;
			showMove = false;
			if (showSearch) {
				showSearch = false;
				searchQuery = '';
			}
		}
	}

	function toggleSearch() {
		showSearch = !showSearch;
		if (!showSearch) { searchQuery = ''; }
		else { setTimeout(() => searchInput?.focus(), 30); }
	}

	function fileIcon(ft: string | undefined) {
		if (ft === 'pdf') return File;
		if (ft === 'image') return Image;
		if (ft === 'excalidraw') return PenTool;
		return FileText;
	}
</script>

<svelte:window on:click={closeContextMenu} on:keydown={handleKeydown} />

<aside class="sidebar">
	<!-- ── Vault switcher ─────────────────────────────────────────── -->
	<div class="vault-bar">
		<select
			class="vault-select"
			bind:this={vaultSelect}
			value={activeVaultId}
			on:change={handleVaultChange}
			aria-label="Select vault"
		>
			{#each vaults as v}
				<option value={v.id}>{v.name}</option>
			{/each}
			<option value="__new__">+ New vault</option>
		</select>
	</div>

	<!-- ── Action buttons ────────────────────────────────────────── -->
	<div class="actions">
		<button class="action-btn" title="New note (N)" on:click={() => openNewNote()}>
			<Plus size={13} strokeWidth={2} />
			<span>New note</span>
		</button>
		<button class="action-btn icon-only" title="New folder" on:click={() => openNewFolderModal()}>
			<FolderPlus size={13} strokeWidth={2} />
		</button>
		<button class="action-btn icon-only" title={showSearch ? 'Close search' : 'Search notes'} class:active={showSearch} on:click={toggleSearch}>
			<Search size={13} strokeWidth={2} />
		</button>
		<button class="action-btn icon-only" title="Upload files" on:click={() => fileInput?.click()}>
			<Upload size={13} strokeWidth={2} />
		</button>
		<input
			bind:this={fileInput}
			type="file"
			accept=".md,.pdf,.pptx,.ppt,.png,.jpg,.jpeg,.gif,.webp,.svg,.excalidraw"
			multiple
			class="hidden-input"
			on:change={handleUpload}
		/>
	</div>

	<!-- ── Search bar ────────────────────────────────────────────── -->
	{#if showSearch}
		<div class="search-bar">
			<Search size={11} strokeWidth={1.5} />
			<input
				bind:this={searchInput}
				class="search-input"
				type="text"
				placeholder="Search notes…"
				bind:value={searchQuery}
			/>
			{#if searchQuery}
				<button class="search-clear" on:click={() => (searchQuery = '')} title="Clear">
					<X size={11} strokeWidth={2} />
				</button>
			{/if}
		</div>
	{/if}

	<!-- ── File tree ─────────────────────────────────────────────── -->
	<nav
		class="tree"
		aria-label="File tree"
		on:contextmenu={(e) => openContextMenu(e, null)}
	>
		{#if searchQuery && displayNodes.length === 0}
			<div class="tree-empty">No results for "{searchQuery}"</div>
		{/if}
		{#each displayNodes as node (node.path)}
			{#if node.kind === 'folder'}
				<button
					class="tree-folder"
					style="padding-left: {0.45 + node.depth * 0.9}rem"
					on:click={() => toggleFolder(node.path)}
					on:keydown={(e) => handleNodeKeydown(e, node)}
					on:contextmenu={(e) => openContextMenu(e, node)}
					aria-expanded={!node.collapsed}
				>
					<span class="fold-arrow">
						{#if node.collapsed}
							<ChevronRight size={12} strokeWidth={2} />
						{:else}
							<ChevronDown size={12} strokeWidth={2} />
						{/if}
					</span>
					<svelte:component this={node.collapsed ? Folder : FolderOpen} size={13} strokeWidth={1.5} />
					<span class="node-name">{node.name}</span>
				</button>
			{:else}
				<button
					class="tree-file"
					class:active={node.path === activeFilePath}
					class:open={openTabs.some((t) => t.path === node.path)}
					style="padding-left: {0.45 + node.depth * 0.9}rem"
					on:click={() => onSelectFile(node.path)}
					on:keydown={(e) => handleNodeKeydown(e, node)}
					on:contextmenu={(e) => openContextMenu(e, node)}
					title={node.path}
				>
					<svelte:component this={fileIcon(node.fileType)} size={12} strokeWidth={1.5} />
					<span class="node-name">{node.name}</span>
				</button>
			{/if}
		{/each}
	</nav>

	<!-- ── Assets panel ─────────────────────────────────────────── -->
	{#if assetFiles.length}
		<div class="assets-section">
			<button class="assets-header" on:click={() => (assetsCollapsed = !assetsCollapsed)}>
				<span class="fold-arrow">
					{#if assetsCollapsed}
						<ChevronRight size={11} strokeWidth={2} />
					{:else}
						<ChevronDown size={11} strokeWidth={2} />
					{/if}
				</span>
				<Image size={12} strokeWidth={1.5} />
				<span>Assets</span>
				<span class="assets-count">{assetFiles.length}</span>
			</button>
			{#if !assetsCollapsed}
				<div class="assets-grid">
					{#each assetFiles as asset (asset.path)}
						<button
							class="asset-thumb"
							class:active={asset.path === activeFilePath}
							title={asset.name}
							on:click={() => onSelectFile(asset.path)}
						>
							<img src={asset.src} alt={asset.name} />
						</button>
					{/each}
				</div>
			{/if}
		</div>
	{/if}

	<!-- ── Context menu ───────────────────────────────────────────── -->
	{#if contextMenu}
		<div
			class="ctx-menu"
			role="menu"
			style="left: {contextMenu.x}px; top: {contextMenu.y}px"
			on:click|stopPropagation
			on:keydown|stopPropagation
		>
			{#if !contextMenu.node}
				<!-- Background right-click: new note / new folder -->
				<button class="ctx-item" on:click={ctxNewNote}>New note here</button>
				<button class="ctx-item" on:click={ctxNewFolder}>New folder here</button>
			{:else if contextMenu.node.kind === 'folder'}
				<!-- Folder right-click -->
				<button class="ctx-item" on:click={ctxNewNote}>New note inside</button>
				<button class="ctx-item" on:click={ctxNewFolder}>New folder inside</button>
				<div class="ctx-sep"></div>
				<button class="ctx-item" on:click={ctxRename}>Rename</button>
				<button class="ctx-item ctx-danger" on:click={ctxDelete}>Delete folder</button>
			{:else}
				<!-- File right-click -->
				<button class="ctx-item" on:click={ctxRename}>Rename</button>
				<button class="ctx-item" on:click={ctxMove}>Move to folder…</button>
				<div class="ctx-sep"></div>
				<button class="ctx-item ctx-danger" on:click={ctxDelete}>Delete</button>
			{/if}
		</div>
	{/if}
</aside>

<!-- ── New note modal ─────────────────────────────────────────────── -->
{#if showNewNote}
	<div class="modal-backdrop" role="presentation" on:click={cancelNewNote} on:keydown={(e) => e.key === 'Escape' && cancelNewNote()}>
		<div class="modal" role="dialog" on:click|stopPropagation on:keydown|stopPropagation>
			<div class="modal-title">New note</div>
			{#if newNoteFolderPath}
				<div class="modal-sub">in <span class="folder-hint">{newNoteFolderPath}/</span></div>
			{/if}

			<div class="modal-field">
				<label class="modal-label">Type</label>
				<div class="type-group">
					<label class="type-opt">
						<input type="radio" bind:group={newNoteType} value="md" />
						<FileText size={11} strokeWidth={2} /> Markdown
					</label>
					<label class="type-opt">
						<input type="radio" bind:group={newNoteType} value="excalidraw" />
						<PenTool size={11} strokeWidth={2} /> Drawing
					</label>
				</div>
			</div>

			<input
				bind:this={newNoteInput}
				class="modal-input"
				type="text"
				placeholder={newNoteType === 'excalidraw' ? 'diagram-name' : 'filename.md'}
				bind:value={newNoteName}
				on:keydown={(e) => { if (e.key === 'Enter') confirmNewNote(); if (e.key === 'Escape') cancelNewNote(); }}
			/>

			{#if newNoteType === 'md'}
			<div class="modal-field">
				<label class="modal-label">Template</label>
				<select class="modal-select" bind:value={newNoteTemplate}>
					{#each TEMPLATES as tpl}
						<option value={tpl.id}>{tpl.label}</option>
					{/each}
				</select>
			</div>
			{/if}

			<div class="modal-actions">
				<button class="modal-btn" on:click={cancelNewNote}>Cancel</button>
				<button class="modal-btn primary" on:click={confirmNewNote}>Create</button>
			</div>
		</div>
	</div>
{/if}

<!-- ── New folder modal ───────────────────────────────────────────── -->
{#if showNewFolder}
	<div class="modal-backdrop" role="presentation" on:click={cancelNewFolder} on:keydown={(e) => e.key === 'Escape' && cancelNewFolder()}>
		<div class="modal" role="dialog" on:click|stopPropagation on:keydown|stopPropagation>
			<div class="modal-title">New folder</div>
			{#if newFolderParent}
				<div class="modal-sub">in <span class="folder-hint">{newFolderParent}/</span></div>
			{/if}
			<input
				bind:this={newFolderInput}
				class="modal-input"
				type="text"
				placeholder="Folder name"
				bind:value={newFolderName}
				on:keydown={(e) => { if (e.key === 'Enter') confirmNewFolder(); if (e.key === 'Escape') cancelNewFolder(); }}
			/>
			<div class="modal-actions">
				<button class="modal-btn" on:click={cancelNewFolder}>Cancel</button>
				<button class="modal-btn primary" on:click={confirmNewFolder}>Create</button>
			</div>
		</div>
	</div>
{/if}

<!-- ── Rename modal ───────────────────────────────────────────────── -->
{#if showRename}
	<div class="modal-backdrop" role="presentation" on:click={cancelRename} on:keydown={(e) => e.key === 'Escape' && cancelRename()}>
		<div class="modal" role="dialog" on:click|stopPropagation on:keydown|stopPropagation>
			<div class="modal-title">Rename</div>
			<input
				bind:this={renameInput}
				class="modal-input"
				type="text"
				bind:value={renameName}
				on:keydown={(e) => { if (e.key === 'Enter') confirmRename(); if (e.key === 'Escape') cancelRename(); }}
			/>
			<div class="modal-actions">
				<button class="modal-btn" on:click={cancelRename}>Cancel</button>
				<button class="modal-btn primary" on:click={confirmRename}>Rename</button>
			</div>
		</div>
	</div>
{/if}

<!-- ── Move to folder modal ───────────────────────────────────────── -->
{#if showMove}
	<div class="modal-backdrop" role="presentation" on:click={cancelMove} on:keydown={(e) => e.key === 'Escape' && cancelMove()}>
		<div class="modal" role="dialog" on:click|stopPropagation on:keydown|stopPropagation>
			<div class="modal-title">Move to folder</div>
			<div class="modal-sub">Moving <span class="folder-hint">{movePath.split('/').pop()}</span></div>
			<div class="modal-field">
				<label class="modal-label">Destination</label>
				<select class="modal-select" bind:value={moveTarget}>
					{#each vaultFolders as folder}
						<option value={folder}>{folder === '' ? '/ (root)' : folder}</option>
					{/each}
				</select>
			</div>
			<div class="modal-actions">
				<button class="modal-btn" on:click={cancelMove}>Cancel</button>
				<button class="modal-btn primary" on:click={confirmMove}>Move</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.sidebar {
		width: 240px;
		flex-shrink: 0;
		background: var(--bg1);
		border-right: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		overflow: hidden;
		position: relative;
	}

	/* ── Vault switcher ──────────────────────────────────────────── */
	.vault-bar {
		padding: 0.55rem 0.6rem 0.5rem;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.vault-select {
		width: 100%;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		padding: 0.28rem 0.45rem;
		cursor: pointer;
		appearance: auto;
	}

	.vault-select:focus { outline: 1px solid var(--accent); border-color: var(--accent); }

	/* ── Action buttons ──────────────────────────────────────────── */
	.actions {
		display: flex;
		gap: 0.25rem;
		padding: 0.4rem 0.5rem;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.action-btn {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		padding: 0.25rem 0.45rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		cursor: pointer;
		transition: color 0.12s, border-color 0.12s, background 0.12s;
		white-space: nowrap;
		flex: 1;
	}

	.action-btn:hover { color: var(--text0); border-color: var(--accent); }
	.action-btn.active { color: var(--accent3); border-color: var(--accent3); background: color-mix(in srgb, var(--accent3) 10%, var(--bg2)); }

	.action-btn.icon-only { flex: 0; padding: 0.25rem 0.4rem; }
	.hidden-input { display: none; }

	/* ── Search bar ──────────────────────────────────────────────── */
	.search-bar {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.35rem 0.55rem;
		border-bottom: 1px solid var(--border);
		background: var(--bg2);
		flex-shrink: 0;
		color: var(--text2);
	}

	.search-input {
		flex: 1;
		background: none;
		border: none;
		outline: none;
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.72rem;
	}

	.search-input::placeholder { color: var(--text2); }

	.search-clear {
		display: flex;
		align-items: center;
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		padding: 2px;
		border-radius: 3px;
	}

	.search-clear:hover { color: var(--text0); }

	/* ── File tree ───────────────────────────────────────────────── */
	.tree {
		flex: 1;
		overflow-y: auto;
		overflow-x: hidden;
		padding: 0.3rem 0;
		user-select: none;
	}

	.tree-empty {
		padding: 1rem 0.8rem;
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
		text-align: center;
	}

	.tree-folder,
	.tree-file {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding-top: 0.22rem;
		padding-bottom: 0.22rem;
		padding-right: 0.5rem;
		cursor: pointer;
		border: none;
		border-left: 2px solid transparent;
		background: none;
		text-align: left;
		width: 100%;
		appearance: none;
		font-family: var(--font-mono);
		font-size: 0.71rem;
		white-space: nowrap;
		overflow: hidden;
		outline: none;
		transition: background 0.1s;
	}

	.tree-folder { color: var(--text1); }
	.tree-folder:hover { background: var(--bg2); color: var(--text0); }

	.tree-file { color: var(--text1); }
	.tree-file:hover { background: var(--bg2); color: var(--text0); }

	.tree-file.open { color: var(--text0); }

	.tree-file.active {
		color: var(--accent3);
		border-left-color: var(--accent3);
		background: color-mix(in srgb, var(--accent3) 8%, transparent);
	}

	.fold-arrow { display: flex; align-items: center; flex-shrink: 0; color: var(--text2); }

	.node-name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		flex: 1;
		min-width: 0;
	}

	/* ── Context menu ────────────────────────────────────────────── */
	.ctx-menu {
		position: fixed;
		z-index: 100;
		background: var(--bg3);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 0.2rem;
		min-width: 150px;
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
	}

	.ctx-item {
		display: block;
		width: 100%;
		padding: 0.32rem 0.65rem;
		background: none;
		border: none;
		border-radius: 3px;
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		text-align: left;
		cursor: pointer;
		transition: background 0.1s, color 0.1s;
	}

	.ctx-item:hover { background: var(--bg2); color: var(--text0); }
	.ctx-item.ctx-danger:hover { color: var(--red); background: color-mix(in srgb, var(--red) 10%, transparent); }

	.ctx-sep { height: 1px; background: var(--border); margin: 0.2rem 0.4rem; }

	/* ── Modals ──────────────────────────────────────────────────── */
	.modal-backdrop {
		position: fixed;
		inset: 0;
		z-index: 200;
		background: rgba(0, 0, 0, 0.55);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.modal {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 1.25rem;
		min-width: 300px;
		display: flex;
		flex-direction: column;
		gap: 0.7rem;
		box-shadow: 0 16px 48px rgba(0, 0, 0, 0.6);
	}

	.modal-title { font-family: var(--font-mono); font-size: 0.82rem; font-weight: 700; color: var(--text0); letter-spacing: 0.04em; }
	.modal-sub { font-family: var(--font-mono); font-size: 0.7rem; color: var(--text2); margin-top: -0.4rem; }
	.folder-hint { color: var(--accent3); }

	.modal-input,
	.modal-select {
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.78rem;
		padding: 0.4rem 0.6rem;
		width: 100%;
	}

	.modal-input:focus,
	.modal-select:focus { outline: 1px solid var(--accent3); border-color: var(--accent3); }

	.modal-field { display: flex; flex-direction: column; gap: 0.3rem; }
	.modal-label { font-family: var(--font-mono); font-size: 0.65rem; color: var(--text2); text-transform: uppercase; letter-spacing: 0.06em; }

	.modal-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.3rem; }

	.modal-btn {
		padding: 0.35rem 0.85rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		cursor: pointer;
		transition: color 0.12s, border-color 0.12s;
	}

	.modal-btn:hover { color: var(--text0); border-color: var(--text2); }

	.modal-btn.primary {
		background: color-mix(in srgb, var(--accent3) 15%, var(--bg2));
		border-color: var(--accent3);
		color: var(--accent3);
	}

	.modal-btn.primary:hover { background: color-mix(in srgb, var(--accent3) 25%, var(--bg2)); }

	/* ── New-note type toggle ────────────────────────────────── */
	.type-group {
		display: flex;
		gap: 0.9rem;
	}

	.type-opt {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text1);
		cursor: pointer;
	}

	.type-opt input[type="radio"] { cursor: pointer; accent-color: var(--accent3); }

	/* ── Assets panel ────────────────────────────────────────────── */
	.assets-section {
		flex-shrink: 0;
		border-top: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		overflow: hidden;
		max-height: 210px;
	}

	.assets-header {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.28rem 0.5rem;
		background: none;
		border: none;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		cursor: pointer;
		text-align: left;
		width: 100%;
		flex-shrink: 0;
		transition: color 0.1s;
	}

	.assets-header:hover { color: var(--text0); }

	.assets-count {
		margin-left: auto;
		font-size: 0.6rem;
		color: var(--text2);
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 20px;
		padding: 0 0.35rem;
	}

	.assets-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 0.25rem;
		padding: 0.25rem 0.5rem 0.4rem;
		overflow-y: auto;
	}

	.asset-thumb {
		aspect-ratio: 1;
		overflow: hidden;
		border-radius: 3px;
		border: 1px solid var(--border);
		background: var(--bg2);
		cursor: pointer;
		padding: 0;
		transition: border-color 0.1s;
	}

	.asset-thumb:hover { border-color: var(--accent); }
	.asset-thumb.active { border-color: var(--accent3); }

	.asset-thumb img {
		width: 100%;
		height: 100%;
		object-fit: cover;
		display: block;
	}
</style>
