<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { editMode } from '$lib/stores/dashConfig';
	import {
		Home, Box, Shield, Play, Server, Cloud, Globe,
		Database, Lock, Cpu, Terminal, Plus, X, GripVertical,
	} from '@lucide/svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	const STORAGE_KEY = 'nexus_quicklinks';
	const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8088';

	interface QuickLink { id: string; name: string; url: string; }
	interface LinkStatus { online: boolean | null; latency_ms: number | null; }

	const DEFAULTS: QuickLink[] = [
		{ id: 'ha',        name: 'Home Assistant', url: 'http://192.168.1.1:8124' },
		{ id: 'portainer', name: 'Portainer',       url: 'http://192.168.1.1:9000' },
		{ id: 'wazuh',     name: 'Wazuh',           url: 'http://192.168.1.1:5601' },
		{ id: 'jellyfin',  name: 'Jellyfin',        url: 'http://192.168.1.1:8096' },
		{ id: 'crafty',    name: 'Crafty',          url: 'http://192.168.1.1:8123' },
		{ id: 'nextcloud', name: 'Nextcloud',       url: 'http://192.168.1.1:8080' },
	];

	const ICON_MAP: Array<[string, any]> = [
		['home assistant', Home],
		['portainer',      Box],
		['wazuh',          Shield],
		['jellyfin',       Play],
		['crafty',         Server],
		['nextcloud',      Cloud],
		['database',       Database],
		['vpn',            Lock],
		['proxmox',        Cpu],
		['terminal',       Terminal],
	];

	function getIcon(name: string): any {
		const lc = name.toLowerCase();
		for (const [k, icon] of ICON_MAP) {
			if (lc.includes(k)) return icon;
		}
		return Globe;
	}

	let links: QuickLink[]                 = [];
	let statuses: Record<string, LinkStatus> = {};
	let pollTimer: ReturnType<typeof setInterval> | null = null;

	let showAdd = false;
	let newName = '';
	let newUrl  = '';

	let dragId:     string | null = null;
	let dragOverId: string | null = null;

	$: if (!$editMode) { showAdd = false; newName = ''; newUrl = ''; }

	function load() {
		try {
			const raw = localStorage.getItem(STORAGE_KEY);
			links = raw ? JSON.parse(raw) : [...DEFAULTS];
		} catch {
			links = [...DEFAULTS];
		}
		for (const l of links) {
			statuses[l.id] ??= { online: null, latency_ms: null };
		}
	}

	function save() {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(links));
	}

	async function pingOne(link: QuickLink) {
		try {
			const r = await fetch(`${BASE}/api/quicklinks/ping?url=${encodeURIComponent(link.url)}`);
			if (r.ok) {
				statuses[link.id] = await r.json();
				statuses = statuses;
			}
		} catch {
			statuses[link.id] = { online: false, latency_ms: null };
			statuses = statuses;
		}
	}

	function pingAll() {
		for (const l of links) pingOne(l);
	}

	function removeLink(id: string) {
		links = links.filter((l) => l.id !== id);
		save();
	}

	function addLink() {
		if (!newName.trim() || !newUrl.trim()) return;
		const url = newUrl.trim().startsWith('http') ? newUrl.trim() : `http://${newUrl.trim()}`;
		const id  = `ql_${Date.now()}`;
		links = [...links, { id, name: newName.trim(), url }];
		statuses[id] = { online: null, latency_ms: null };
		save();
		pingOne(links[links.length - 1]);
		newName = '';
		newUrl  = '';
		showAdd = false;
	}

	function startDrag(e: DragEvent, id: string) {
		dragId = id;
		if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move';
	}

	function onDragOver(e: DragEvent, id: string) {
		e.preventDefault();
		dragOverId = id;
	}

	function onDrop(e: DragEvent, targetId: string) {
		e.preventDefault();
		if (dragId && dragId !== targetId) {
			const from = links.findIndex((l) => l.id === dragId);
			const to   = links.findIndex((l) => l.id === targetId);
			const arr  = [...links];
			const [m]  = arr.splice(from, 1);
			arr.splice(to, 0, m);
			links = arr;
			save();
		}
		dragId = dragOverId = null;
	}

	onMount(() => {
		load();
		pingAll();
		pollTimer = setInterval(pingAll, 60_000);
	});

	onDestroy(() => {
		if (pollTimer) clearInterval(pollTimer);
	});
</script>

<div class="widget">
	<div class="accent-bar"></div>
	<div class="body">

		<div class="header">
			<span class="title">quick links</span>
			{#if $editMode}
				<button class="add-btn" on:click={() => (showAdd = !showAdd)}>
					<Plus size={11} strokeWidth={2.5} /> add
				</button>
			{/if}
		</div>

		{#if showAdd && $editMode}
			<div class="add-form">
				<input class="add-input" placeholder="Name" bind:value={newName} />
				<input class="add-input" placeholder="http://…" bind:value={newUrl} />
				<button class="add-save" on:click={addLink}>Add</button>
				<button class="add-cancel" on:click={() => { showAdd = false; newName = ''; newUrl = ''; }}>✕</button>
			</div>
		{/if}

		{#if links.length === 0}
			<EmptyState
				variant="not-configured"
				size="compact"
				title="No quick links"
				body="Add links in Settings → Data."
			/>
		{/if}
		<div class="links-grid">
			{#each links as link (link.id)}
				{@const st   = statuses[link.id]}
				{@const Icon = getIcon(link.name)}

				{#if $editMode}
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<div
						class="card edit-card"
						class:drag-over={dragOverId === link.id}
						draggable="true"
						on:dragstart={(e) => startDrag(e, link.id)}
						on:dragover={(e) => onDragOver(e, link.id)}
						on:drop={(e) => onDrop(e, link.id)}
						on:dragend={() => { dragId = dragOverId = null; }}
					>
						<button class="rm-btn" on:click={() => removeLink(link.id)} title="Remove">
							<X size={10} strokeWidth={2.5} />
						</button>
						<span class="dh" aria-hidden="true"><GripVertical size={10} strokeWidth={1.5} /></span>
						<svelte:component this={Icon} size={18} strokeWidth={1.5} />
						<span class="card-name">{link.name}</span>
						<div class="status-row">
							<span class="dot" class:on={st?.online === true} class:off={st?.online === false}></span>
						</div>
					</div>
				{:else}
					<a
						class="card"
						href={link.url}
						target="_blank"
						rel="noopener noreferrer"
						title="{link.name} — {link.url}"
					>
						<svelte:component this={Icon} size={18} strokeWidth={1.5} />
						<span class="card-name">{link.name}</span>
						<div class="status-row">
							<span class="dot" class:on={st?.online === true} class:off={st?.online === false}></span>
							{#if st?.online && st?.latency_ms != null}
								<span class="latency">{st.latency_ms}ms</span>
							{:else if st?.online === false}
								<span class="latency err">offline</span>
							{:else}
								<span class="latency muted">…</span>
							{/if}
						</div>
					</a>
				{/if}
			{/each}
		</div>

	</div>
</div>

<style>
	.widget {
		display: flex;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
	}

	.accent-bar {
		width: 3px;
		background: var(--accent2);
		flex-shrink: 0;
	}

	.body {
		flex: 1;
		padding: 0.7rem 0.85rem;
		min-width: 0;
	}

	/* ── Header ─────────────────────────────────────────────── */
	.header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.65rem;
	}

	.title {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text2);
	}

	.add-btn {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		padding: 0.15rem 0.5rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.62rem;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}
	.add-btn:hover { color: var(--accent2); border-color: var(--accent2); }

	/* ── Add form ────────────────────────────────────────────── */
	.add-form {
		display: flex;
		gap: 0.4rem;
		margin-bottom: 0.65rem;
		flex-wrap: wrap;
	}

	.add-input {
		flex: 1;
		min-width: 80px;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		padding: 0.25rem 0.5rem;
		outline: none;
	}
	.add-input:focus { border-color: var(--accent2); }
	.add-input::placeholder { color: var(--text2); }

	.add-save {
		padding: 0.25rem 0.6rem;
		background: color-mix(in srgb, var(--accent2) 15%, var(--bg2));
		border: 1px solid var(--accent2);
		border-radius: var(--radius);
		color: var(--accent2);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		cursor: pointer;
	}

	.add-cancel {
		padding: 0.25rem 0.5rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		cursor: pointer;
	}

	/* ── Grid ────────────────────────────────────────────────── */
	.links-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 0.5rem;
	}

	/* ── Cards ───────────────────────────────────────────────── */
	.card {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.3rem;
		padding: 0.55rem 0.4rem 0.45rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		text-decoration: none;
		color: var(--text1);
		transition: background 0.12s, border-color 0.12s, color 0.12s;
		min-width: 0;
	}
	.card:hover {
		background: var(--bg3);
		border-color: var(--accent2);
		color: var(--text0);
	}

	.edit-card {
		position: relative;
		cursor: default;
		color: var(--text2);
	}
	.edit-card.drag-over {
		border-color: var(--accent);
		background: color-mix(in srgb, var(--accent) 10%, var(--bg2));
	}

	.rm-btn {
		position: absolute;
		top: 2px;
		right: 2px;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 16px;
		height: 16px;
		background: color-mix(in srgb, var(--red) 15%, var(--bg2));
		border: 1px solid color-mix(in srgb, var(--red) 40%, var(--border));
		border-radius: 3px;
		color: var(--red);
		cursor: pointer;
		padding: 0;
	}

	.dh {
		position: absolute;
		top: 2px;
		left: 3px;
		color: var(--text2);
		cursor: grab;
		line-height: 1;
	}
	.dh:active { cursor: grabbing; }

	.card-name {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 600;
		text-align: center;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		width: 100%;
		line-height: 1.2;
	}

	/* ── Status ──────────────────────────────────────────────── */
	.status-row {
		display: flex;
		align-items: center;
		gap: 0.25rem;
	}

	.dot {
		width: 5px;
		height: 5px;
		border-radius: 50%;
		background: var(--text2);
		flex-shrink: 0;
		transition: background 0.3s;
	}
	.dot.on  { background: var(--green); }
	.dot.off { background: var(--red);   }

	.latency {
		font-family: var(--font-mono);
		font-size: 0.56rem;
		color: var(--text2);
	}
	.latency.err   { color: var(--red);   }
	.latency.muted { color: var(--text2); }
</style>
