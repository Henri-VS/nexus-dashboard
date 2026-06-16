<script lang="ts">
	import { onMount } from 'svelte';
	import { services as servicesApi, homeAssistant, type Service } from '$lib/api';
	import type { HomeEntity } from '$lib/types';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import {
		Globe, Play, Box, Shield, Database, Lock, Cpu, Terminal,
		Wifi, Server, Home, Zap, BookOpen, Music, Camera, Monitor,
		Activity, Code, Layers, Plus, Pencil, Trash2, RefreshCw,
	} from '@lucide/svelte';

	type LucideIcon = typeof Globe;

	const ICON_MAP: Record<string, LucideIcon> = {
		globe: Globe, play: Play, box: Box, shield: Shield,
		database: Database, lock: Lock, cpu: Cpu, terminal: Terminal,
		wifi: Wifi, server: Server, home: Home, zap: Zap,
		book: BookOpen, music: Music, camera: Camera, monitor: Monitor,
		activity: Activity, code: Code, layers: Layers,
	};

	function getIcon(name: string): LucideIcon {
		return ICON_MAP[name.toLowerCase()] ?? Globe;
	}

	// ── State ───────────────────────────────────────────────────────
	let allServices: Service[] = [];
	let statuses: Record<string, { online: boolean | null; ms: number | null }> = {};
	let haEntities: HomeEntity[] = [];
	let loading = true;
	let showForm = false;
	let editingId: string | null = null;
	let saving = false;

	type FormData = { name: string; url: string; category: string; icon: string; description: string };
	const DEFAULT_FORM: FormData = { name: '', url: 'http://', category: 'Other', icon: 'globe', description: '' };
	let form: FormData = { ...DEFAULT_FORM };

	$: groups = Object.entries(
		allServices.reduce<Record<string, Service[]>>((acc, s) => {
			(acc[s.category] ??= []).push(s);
			return acc;
		}, {})
	).sort(([a], [b]) => a.localeCompare(b));

	// ── Load ──────────────────────────────────────────────────────────
	async function load() {
		loading = true;
		const res = await servicesApi.list();
		allServices = res?.services ?? [];
		loading = false;
		pingAll();
	}

	async function loadHA() {
		const res = await homeAssistant.entities();
		if (res && res.length > 0) haEntities = res;
	}

	function pingAll() {
		for (const s of allServices) {
			if (!s.enabled) continue;
			statuses[s.id] = { online: null, ms: null };
			servicesApi
				.ping(s.url)
				.then((r) => {
					statuses[s.id] = r ? { online: r.online, ms: r.latency_ms } : { online: false, ms: null };
					statuses = { ...statuses };
				})
				.catch(() => {
					statuses[s.id] = { online: false, ms: null };
					statuses = { ...statuses };
				});
		}
	}

	onMount(() => { load(); loadHA(); });

	// ── Form handlers ──────────────────────────────────────────────────
	function openAdd() {
		editingId = null;
		form = { ...DEFAULT_FORM };
		showForm = true;
	}

	function openEdit(s: Service) {
		editingId = s.id;
		form = { name: s.name, url: s.url, category: s.category, icon: s.icon, description: s.description };
		showForm = true;
	}

	function closeForm() {
		showForm = false;
		editingId = null;
	}

	async function saveForm() {
		if (!form.name.trim() || !form.url.trim()) return;
		saving = true;
		const payload: Omit<Service, 'id'> = { ...form, enabled: true };
		if (editingId) {
			await servicesApi.update(editingId, payload);
		} else {
			await servicesApi.create(payload);
		}
		saving = false;
		closeForm();
		load();
	}

	async function deleteService(id: string, name: string) {
		if (!confirm(`Delete "${name}"?`)) return;
		await servicesApi.delete(id);
		load();
	}
</script>

<svelte:head><title>Services · Nexus</title></svelte:head>

<div class="page">

	<!-- ── Header ─────────────────────────────────────────────────── -->
	<div class="page-header">
		<div class="header-left">
			<h1 class="page-title">Services</h1>
			{#if allServices.length > 0}
				<span class="count-badge">{allServices.length}</span>
			{/if}
		</div>
		<div class="header-right">
			<button class="btn-icon" on:click={pingAll} title="Refresh ping status">
				<RefreshCw size={13} strokeWidth={1.8} />
			</button>
			<button class="btn-primary" on:click={openAdd}>
				<Plus size={13} strokeWidth={2} />
				Add service
			</button>
		</div>
	</div>

	<!-- ── Add / Edit form ────────────────────────────────────────── -->
	{#if showForm}
		<div class="form-card">
			<div class="form-header">
				<span class="form-title">{editingId ? 'Edit service' : 'New service'}</span>
				<button class="btn-ghost-sm" on:click={closeForm}>Cancel</button>
			</div>
			<div class="form-grid">
				<label class="field">
					<span class="field-label">Name</span>
					<input class="field-input" type="text" bind:value={form.name} placeholder="Jellyfin" />
				</label>
				<label class="field">
					<span class="field-label">URL</span>
					<input class="field-input" type="url" bind:value={form.url} placeholder="http://192.168.1.10:8096" />
				</label>
				<label class="field">
					<span class="field-label">Category</span>
					<input class="field-input" type="text" bind:value={form.category} placeholder="Media" />
				</label>
				<label class="field">
					<span class="field-label">Icon <span class="field-hint">(lucide name)</span></span>
					<input class="field-input" type="text" bind:value={form.icon} placeholder="play" />
				</label>
				<label class="field field-wide">
					<span class="field-label">Description <span class="field-hint">(optional)</span></span>
					<input class="field-input" type="text" bind:value={form.description} placeholder="My media server" />
				</label>
			</div>
			<div class="form-footer">
				<div class="icon-preview">
					<svelte:component this={getIcon(form.icon)} size={14} strokeWidth={1.6} />
					<span class="icon-preview-name">{form.icon || 'globe'}</span>
				</div>
				<button
					class="btn-primary"
					on:click={saveForm}
					disabled={saving || !form.name.trim() || !form.url.trim()}
				>
					{saving ? 'Saving…' : editingId ? 'Save changes' : 'Add service'}
				</button>
			</div>
		</div>
	{/if}

	<!-- ── Service catalog ────────────────────────────────────────── -->
	{#if loading}
		<div class="loading-hint">Loading…</div>
	{:else if allServices.length === 0 && !showForm}
		<EmptyState
			variant="not-configured"
			title="No services configured"
			body="Add your self-hosted services — media, monitoring, automation, and more."
			primaryAction="Add your first service"
			primaryOnClick={openAdd}
		/>
	{:else}
		{#each groups as [category, svcList]}
			<section class="cat-group">
				<h2 class="cat-heading">{category}</h2>
				<div class="svc-grid">
					{#each svcList as svc (svc.id)}
						{@const st = statuses[svc.id]}
						<div class="svc-card" class:svc-disabled={!svc.enabled}>
							<a href={svc.url} target="_blank" rel="noopener noreferrer" class="svc-main">
								<div class="svc-icon-wrap">
									<svelte:component this={getIcon(svc.icon)} size={16} strokeWidth={1.6} />
								</div>
								<div class="svc-info">
									<span class="svc-name">{svc.name}</span>
									{#if svc.description}
										<span class="svc-desc">{svc.description}</span>
									{/if}
								</div>
								<div class="svc-status-wrap">
									{#if !svc.enabled}
										<span class="svc-dot dot-disabled" title="Disabled"></span>
									{:else if st === undefined || st.online === null}
										<span class="svc-dot dot-checking" title="Checking…"></span>
									{:else if st.online}
										<span class="svc-dot dot-online" title="Online"></span>
										{#if st.ms !== null}
											<span class="svc-latency">{st.ms}ms</span>
										{/if}
									{:else}
										<span class="svc-dot dot-offline" title="Offline"></span>
									{/if}
								</div>
							</a>
							<div class="svc-actions">
								<button class="act-btn" title="Edit" on:click={() => openEdit(svc)}>
									<Pencil size={11} strokeWidth={1.6} />
								</button>
								<button class="act-btn act-btn-danger" title="Delete" on:click={() => deleteService(svc.id, svc.name)}>
									<Trash2 size={11} strokeWidth={1.6} />
								</button>
							</div>
						</div>
					{/each}
				</div>
			</section>
		{/each}
	{/if}

	<!-- ── Home Assistant (only renders when HA_TOKEN is configured) ─ -->
	{#if haEntities.length > 0}
		<section class="cat-group">
			<h2 class="cat-heading">Home Assistant</h2>
			<div class="ha-grid">
				{#each haEntities as entity}
					<div class="ha-entity">
						<span class="ha-name">
							{entity.attributes.friendly_name ?? entity.entity_id}
						</span>
						<span class="ha-state" class:ha-on={entity.state === 'on'}>{entity.state}</span>
					</div>
				{/each}
			</div>
		</section>
	{/if}

</div>

<style>
	/* ── Page wrapper ─────────────────────────────────────────────── */
	.page {
		padding: 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 1.5rem;
		max-width: 900px;
	}

	/* ── Header ───────────────────────────────────────────────────── */
	.page-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: 0.6rem;
	}

	.page-title {
		font-family: var(--font-ui);
		font-size: 1.15rem;
		font-weight: 600;
		color: var(--text0);
		margin: 0;
	}

	.count-badge {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		padding: 2px 7px;
		border-radius: 20px;
		background: var(--bg2);
		border: 1px solid var(--border);
		color: var(--text1);
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	/* ── Buttons ──────────────────────────────────────────────────── */
	.btn-primary {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.35rem 0.75rem;
		background: var(--accent);
		border: 1px solid var(--accent);
		border-radius: var(--radius);
		color: #0d1117;
		font-family: var(--font-ui);
		font-size: 0.78rem;
		font-weight: 600;
		cursor: pointer;
		transition: opacity 0.12s;
	}
	.btn-primary:hover    { opacity: 0.88; }
	.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }

	.btn-icon {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 32px;
		height: 32px;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}
	.btn-icon:hover { color: var(--text0); border-color: var(--text2); }

	.btn-ghost-sm {
		background: none;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-ui);
		font-size: 0.75rem;
		padding: 0.25rem 0.6rem;
		cursor: pointer;
		transition: color 0.1s;
	}
	.btn-ghost-sm:hover { color: var(--text0); }

	/* ── Form card ────────────────────────────────────────────────── */
	.form-card {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-left: 3px solid var(--accent);
		border-radius: 8px;
		padding: 1rem 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.form-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.form-title {
		font-family: var(--font-ui);
		font-size: 0.88rem;
		font-weight: 600;
		color: var(--text0);
	}

	.form-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.75rem;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
	}
	.field-wide { grid-column: 1 / -1; }

	.field-label {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--text1);
	}

	.field-hint {
		color: var(--text2);
		font-size: 0.6rem;
		text-transform: none;
		letter-spacing: 0;
	}

	.field-input {
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 5px;
		padding: 0.35rem 0.6rem;
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text0);
		outline: none;
		transition: border-color 0.1s;
	}
	.field-input:focus        { border-color: var(--accent2); }
	.field-input::placeholder { color: var(--text2); }

	.form-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.icon-preview {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		color: var(--text1);
	}

	.icon-preview-name {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text2);
	}

	/* ── Category group ───────────────────────────────────────────── */
	.cat-group {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
	}

	.cat-heading {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text2);
		margin: 0;
		padding-left: 0.1rem;
	}

	/* ── Service grid ─────────────────────────────────────────────── */
	.svc-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
		gap: 0.5rem;
	}

	/* ── Service card ─────────────────────────────────────────────── */
	.svc-card {
		display: flex;
		align-items: center;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-left: 3px solid var(--accent2);
		border-radius: 8px;
		overflow: hidden;
		transition: background 0.1s;
	}
	.svc-card:hover        { background: var(--bg2); }
	.svc-card.svc-disabled { opacity: 0.45; border-left-color: var(--border); }

	.svc-main {
		flex: 1;
		display: flex;
		align-items: center;
		gap: 0.65rem;
		padding: 0.65rem 0.75rem;
		text-decoration: none;
		min-width: 0;
	}

	.svc-icon-wrap {
		flex-shrink: 0;
		width: 30px;
		height: 30px;
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 6px;
		color: var(--accent2);
	}

	.svc-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}

	.svc-name {
		font-family: var(--font-ui);
		font-size: 0.85rem;
		font-weight: 500;
		color: var(--text0);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.svc-desc {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.svc-status-wrap {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		flex-shrink: 0;
	}

	.svc-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.dot-checking { background: var(--text2); }
	.dot-online   { background: var(--green); box-shadow: 0 0 4px var(--green); }
	.dot-offline  { background: var(--red); }
	.dot-disabled { background: var(--border); }

	.svc-latency {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
	}

	.svc-actions {
		display: flex;
		align-items: center;
		gap: 0.15rem;
		padding-right: 0.4rem;
	}

	.act-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		background: none;
		border: none;
		border-radius: 4px;
		color: var(--text2);
		cursor: pointer;
		transition: color 0.1s, background 0.1s;
	}
	.act-btn:hover          { color: var(--text1); background: var(--bg3); }
	.act-btn-danger:hover   { color: var(--red); }

	/* ── Loading hint ─────────────────────────────────────────────── */
	.loading-hint {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text2);
	}

	/* ── Home Assistant entities ──────────────────────────────────── */
	.ha-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
		gap: 0.4rem;
	}

	.ha-entity {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.45rem 0.65rem;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: 6px;
		gap: 0.5rem;
		overflow: hidden;
	}

	.ha-name {
		font-family: var(--font-ui);
		font-size: 0.8rem;
		color: var(--text0);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.ha-state {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
		flex-shrink: 0;
		text-transform: lowercase;
	}
	.ha-state.ha-on { color: var(--green); }
</style>
