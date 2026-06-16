<script lang="ts">
	import { onMount } from 'svelte';
	import { FileText, Plus, Eye, Edit2, Columns, Search, Database, ChevronRight } from '@lucide/svelte';
	import type { StoredFile, StoredVault } from './types';

	export let allFiles: Record<string, StoredFile> = {};
	export let vaults: StoredVault[] = [];
	export let currentMode: 'edit' | 'preview' | 'split' = 'split';
	export let propsOpen: boolean = true;

	export let onOpenFile: (path: string) => void = () => {};
	export let onNewNote: () => void = () => {};
	export let onNewNoteFromTemplate: () => void = () => {};
	export let onSwitchVault: (id: string) => void = () => {};
	export let onToggleMode: (mode: 'edit' | 'preview' | 'split') => void = () => {};
	export let onToggleProps: () => void = () => {};
	export let onClose: () => void = () => {};

	let query = '';
	let selectedIndex = 0;
	let inputEl: HTMLInputElement;

	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	type IconComponent = any;

	interface Item {
		type: 'file' | 'command';
		label: string;
		desc?: string;
		Icon: IconComponent;
		action: () => void;
	}

	$: fileItems = Object.entries(allFiles)
		.filter(([, f]) => f.type === 'md')
		.sort(([, a], [, b]) => b.modified - a.modified)
		.map(([path]) => ({
			type: 'file' as const,
			label: path.split('/').pop()?.replace(/\.md$/, '') ?? path,
			desc: path,
			Icon: FileText,
			action: () => { onOpenFile(path); onClose(); },
		}));

	$: vaultCommands = vaults.map((v) => ({
		type: 'command' as const,
		label: `Switch vault: ${v.name}`,
		desc: v.id,
		Icon: Database,
		action: () => { onSwitchVault(v.id); onClose(); },
	}));

	$: modeCommands = [
		{ type: 'command' as const, label: 'Mode: Edit', desc: 'Show editor only', Icon: Edit2, action: () => { onToggleMode('edit'); onClose(); } },
		{ type: 'command' as const, label: 'Mode: Split', desc: 'Editor + preview side by side', Icon: Columns, action: () => { onToggleMode('split'); onClose(); } },
		{ type: 'command' as const, label: 'Mode: Preview', desc: 'Show preview only', Icon: Eye, action: () => { onToggleMode('preview'); onClose(); } },
	];

	$: builtinCommands = [
		{ type: 'command' as const, label: 'New note', desc: 'Create a blank note', Icon: Plus, action: () => { onClose(); onNewNote(); } },
		{ type: 'command' as const, label: 'New note from template', desc: 'Pick a template', Icon: Plus, action: () => { onClose(); onNewNoteFromTemplate(); } },
		{ type: 'command' as const, label: `Toggle properties (${propsOpen ? 'open' : 'closed'})`, desc: 'Right panel', Icon: ChevronRight, action: () => { onToggleProps(); onClose(); } },
	];

	$: allCommands = ([...builtinCommands, ...modeCommands, ...vaultCommands] as Item[]);

	$: q = query.trim().toLowerCase();
	$: shownFiles = q
		? fileItems.filter((f) => f.label.toLowerCase().includes(q) || (f.desc ?? '').toLowerCase().includes(q))
		: fileItems.slice(0, 8);
	$: shownCommands = q
		? allCommands.filter((c) => c.label.toLowerCase().includes(q) || (c.desc ?? '').toLowerCase().includes(q))
		: allCommands;
	$: items = [...shownFiles, ...shownCommands] as Item[];
	$: if (selectedIndex >= items.length) selectedIndex = Math.max(0, items.length - 1);

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'ArrowDown') { e.preventDefault(); selectedIndex = Math.min(selectedIndex + 1, items.length - 1); scrollSelected(); }
		else if (e.key === 'ArrowUp') { e.preventDefault(); selectedIndex = Math.max(selectedIndex - 1, 0); scrollSelected(); }
		else if (e.key === 'Enter') { e.preventDefault(); items[selectedIndex]?.action(); }
		else if (e.key === 'Escape') { e.preventDefault(); onClose(); }
	}

	let listEl: HTMLDivElement;
	function scrollSelected() {
		setTimeout(() => {
			const el = listEl?.children[selectedIndex] as HTMLElement | undefined;
			el?.scrollIntoView({ block: 'nearest' });
		}, 0);
	}

	onMount(() => { inputEl?.focus(); });
</script>

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="palette-backdrop" on:click={onClose}>
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div class="palette" on:click|stopPropagation>
		<div class="palette-input-wrap">
			<Search size={14} strokeWidth={1.5} />
			<input
				bind:this={inputEl}
				class="palette-input"
				type="text"
				placeholder="Search notes or type a command…"
				bind:value={query}
				on:keydown={handleKeydown}
				on:input={() => { selectedIndex = 0; }}
			/>
			<span class="esc-hint">esc</span>
		</div>

		<div class="palette-list" bind:this={listEl}>
			{#if items.length === 0}
				<div class="palette-empty">No results for "{query}"</div>
			{:else}
				{#if shownFiles.length > 0}
					<div class="palette-section">notes</div>
				{/if}
				{#each shownFiles as item, i}
					<!-- svelte-ignore a11y-click-events-have-key-events -->
					<div
						class="palette-item"
						class:selected={i === selectedIndex}
						on:click={item.action}
						on:mouseenter={() => (selectedIndex = i)}
					>
						<svelte:component this={item.Icon} size={13} strokeWidth={1.5} />
						<div class="palette-item-text">
							<span class="palette-label">{item.label}</span>
							{#if item.desc}<span class="palette-desc">{item.desc}</span>{/if}
						</div>
					</div>
				{/each}

				{#if shownCommands.length > 0}
					<div class="palette-section">commands</div>
				{/if}
				{#each shownCommands as item, i}
					<!-- svelte-ignore a11y-click-events-have-key-events -->
					<div
						class="palette-item"
						class:selected={(shownFiles.length + i) === selectedIndex}
						on:click={item.action}
						on:mouseenter={() => (selectedIndex = shownFiles.length + i)}
					>
						<svelte:component this={item.Icon} size={13} strokeWidth={1.5} />
						<div class="palette-item-text">
							<span class="palette-label">{item.label}</span>
							{#if item.desc}<span class="palette-desc">{item.desc}</span>{/if}
						</div>
					</div>
				{/each}
			{/if}
		</div>
	</div>
</div>

<style>
	.palette-backdrop {
		position: fixed;
		inset: 0;
		z-index: 300;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: flex-start;
		justify-content: center;
		padding-top: 10vh;
	}

	.palette {
		width: min(560px, 90vw);
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		box-shadow: 0 24px 64px rgba(0, 0, 0, 0.7);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		max-height: 60vh;
	}

	.palette-input-wrap {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.65rem 0.85rem;
		border-bottom: 1px solid var(--border);
		background: var(--bg2);
		flex-shrink: 0;
		color: var(--text2);
	}

	.palette-input {
		flex: 1;
		background: none;
		border: none;
		outline: none;
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.82rem;
	}

	.palette-input::placeholder { color: var(--text2); }

	.esc-hint {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text2);
		background: var(--bg3);
		border: 1px solid var(--border);
		border-radius: 3px;
		padding: 0.1rem 0.35rem;
		flex-shrink: 0;
	}

	.palette-list {
		overflow-y: auto;
		padding: 0.2rem;
	}

	.palette-section {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text2);
		padding: 0.45rem 0.65rem 0.2rem;
	}

	.palette-item {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.4rem 0.65rem;
		border-radius: 4px;
		cursor: pointer;
		color: var(--text1);
		transition: background 0.08s, color 0.08s;
	}

	.palette-item:hover,
	.palette-item.selected {
		background: var(--bg2);
		color: var(--text0);
	}

	.palette-item.selected { background: color-mix(in srgb, var(--accent3) 12%, var(--bg2)); }

	.palette-item-text {
		display: flex;
		flex-direction: column;
		gap: 0.05rem;
		min-width: 0;
	}

	.palette-label {
		font-family: var(--font-mono);
		font-size: 0.76rem;
		color: inherit;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.palette-desc {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.palette-empty {
		padding: 1.5rem;
		text-align: center;
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text2);
	}
</style>
