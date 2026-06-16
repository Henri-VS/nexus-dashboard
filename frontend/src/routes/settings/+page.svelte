<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { browser } from '$app/environment';
	import { theme, themes } from '$lib/theme';
	import { dashConfig, WIDGET_DEFS, LAYOUT_PRESETS } from '$lib/stores/dashConfig';
	import LayoutPicker from '$lib/components/LayoutPicker.svelte';
	import { nexusSettings, selectedModel } from '$lib/stores';
	import { ai, rag as ragApi, newsFeeds, type Feed } from '$lib/api';
	import { snippetFiles, themeFiles, reloadSnippets, loadThemes } from '$lib/snippets';
	import {
		Check,
		Database,
		Download,
		Upload,
		RotateCcw,
		Send,
		RefreshCw,
		Trash2,
	} from '@lucide/svelte';

	const APP_VERSION = '1.0.0';
	const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8088';

	// ── Tab state ─────────────────────────────────────────────────────────────
	let activeTab: 'appearance' | 'integrations' | 'notifications' | 'data' | 'about' = 'appearance';

	// ── APPEARANCE ────────────────────────────────────────────────────────────

	let showLayoutPicker = false;

	$: currentLayoutName = $dashConfig.currentLayoutId
		? (LAYOUT_PRESETS.find((p) => p.id === $dashConfig.currentLayoutId)?.name ?? 'Custom')
		: 'Custom';

	$: accentEnabled = !!$dashConfig.accentOverride;

	function toggleAccent(enabled: boolean) {
		dashConfig.setAccentOverride(enabled ? ($dashConfig.accentOverride ?? '#3fb950') : null);
	}

	function onAccentInput(e: Event) {
		const color = (e.currentTarget as HTMLInputElement).value;
		dashConfig.setAccentOverride(color);
		if (browser) document.documentElement.style.setProperty('--accent', color);
	}

	$: fontSize = $dashConfig.fontSize;

	// ── CSS SNIPPETS / THEMES ─────────────────────────────────────────────────

	let snippetReloading = false;
	let themeReloading   = false;

	async function handleReloadSnippets() {
		snippetReloading = true;
		await reloadSnippets();
		snippetReloading = false;
	}

	async function handleReloadThemes() {
		themeReloading = true;
		await loadThemes();
		themeReloading = false;
	}

	function fmtBytes(n: number): string {
		return n < 1024 ? `${n} B` : `${(n / 1024).toFixed(1)} KB`;
	}

	// ── INTEGRATIONS / RAG ───────────────────────────────────────────────────

	let ragStatus: { available: boolean; indexed_chunks: number; collection: string } | null = null;
	let reindexing = false;

	$: ragStatusText = ragStatus === null
		? '✕ unavailable'
		: ragStatus.available && ragStatus.indexed_chunks > 0
			? `● indexed · ${ragStatus.indexed_chunks} chunks`
			: ragStatus.available
				? '● no documents indexed'
				: '✕ unavailable';

	$: ragStatusColor = ragStatus === null || !ragStatus.available
		? '#f85149'
		: ragStatus.indexed_chunks > 0
			? '#3fb950'
			: '#e3b341';

	async function loadRagStatus() {
		const r = await ragApi.status();
		if (r) ragStatus = r;
	}

	async function reindex() {
		reindexing = true;
		await ragApi.ingest();
		await new Promise((r) => setTimeout(r, 2000));
		await loadRagStatus();
		reindexing = false;
	}

	// ── INTEGRATIONS / AI ────────────────────────────────────────────────────

	let aiModel    = $nexusSettings.ai.defaultModel;
	let aiPrompt   = $nexusSettings.ai.systemPrompt;
	let ollamaHost = $nexusSettings.ai.ollamaHost;
	let aiSaved    = false;

	function saveAi() {
		nexusSettings.patch({ ai: { defaultModel: aiModel, systemPrompt: aiPrompt, ollamaHost } });
		selectedModel.set(aiModel);
		aiSaved = true;
		setTimeout(() => { aiSaved = false; }, 1500);
	}

	// ── NOTIFICATIONS ─────────────────────────────────────────────────────────

	let ntfyTopic  = $nexusSettings.ntfy.topic;
	let ntfyServer = $nexusSettings.ntfy.server;
	let ntfyMsg    = '';
	let ntfyOk     = false;

	function saveNtfy() {
		nexusSettings.patch({ ntfy: { topic: ntfyTopic, server: ntfyServer } });
	}

	async function testNotification() {
		saveNtfy();
		if (!ntfyTopic.trim()) { ntfyMsg = 'Set a topic first.'; ntfyOk = false; flash(); return; }
		await syncNotifToBackend();
		try {
			const res = await fetch(`${API_BASE}/api/notifications/test`, { method: 'POST' });
			const d   = await res.json();
			ntfyOk  = d.sent === true;
			ntfyMsg = d.sent ? 'Sent!' : 'Not sent — check server/topic';
		} catch {
			ntfyOk  = false;
			ntfyMsg = 'Network error';
		}
		flash();
	}

	function flash() { setTimeout(() => { ntfyMsg = ''; }, 3000); }

	// ── NOTIFICATION CONFIG ───────────────────────────────────────────────────

	interface NotifConfig {
		master: boolean;
		security:    { onCrit: boolean; onHigh: boolean; onWarn: boolean; threshold: string; };
		heartbeat:   { onDown: boolean; onRecover: boolean; digest: boolean; digestTime: string; };
		docker:      { onCrash: boolean; onRestartThreshold: boolean; restartThreshold: number; };
		automations: { onSuccess: boolean; onFailure: boolean; };
		study:       { onWorkComplete: boolean; onBreakComplete: boolean; reminder: boolean; reminderTime: string; };
		calendar:    { remindersEnabled: boolean; reminderTime: string; };
		news:        { digest: boolean; digestTime: string; };
		system:      { onDiskHigh: boolean; diskThreshold: number; onCpuHigh: boolean; cpuThreshold: number; onRamHigh: boolean; ramThreshold: number; };
	}

	const NOTIF_DEFAULTS: NotifConfig = {
		master:      true,
		security:    { onCrit: true,  onHigh: true,  onWarn: false, threshold: 'HIGH' },
		heartbeat:   { onDown: true,  onRecover: true, digest: false, digestTime: '08:00' },
		docker:      { onCrash: true, onRestartThreshold: false, restartThreshold: 3 },
		automations: { onSuccess: false, onFailure: true },
		study:       { onWorkComplete: false, onBreakComplete: false, reminder: false, reminderTime: '09:00' },
		calendar:    { remindersEnabled: true, reminderTime: '15m' },
		news:        { digest: false, digestTime: '07:00' },
		system:      { onDiskHigh: true, diskThreshold: 85, onCpuHigh: false, cpuThreshold: 85, onRamHigh: false, ramThreshold: 85 },
	};

	const NOTIF_KEY = 'nexus_notifications_config';
	let notifSaved = false;
	let notifSaveTimer: ReturnType<typeof setTimeout>;
	let notif: NotifConfig = structuredClone(NOTIF_DEFAULTS);

	function _buildNotifCfg() {
		return { ...notif, ntfyUrl: ntfyServer, ntfyTopic };
	}

	function loadNotifConfig() {
		if (!browser) return;
		try {
			const raw = localStorage.getItem(NOTIF_KEY);
			if (!raw) return;
			const c = JSON.parse(raw);
			if (c.ntfyUrl)   ntfyServer = c.ntfyUrl;
			if (c.ntfyTopic) ntfyTopic  = c.ntfyTopic;
			notif = {
				master:      c.master                          ?? NOTIF_DEFAULTS.master,
				security: {
					onCrit:    c.security?.onCrit              ?? NOTIF_DEFAULTS.security.onCrit,
					onHigh:    c.security?.onHigh              ?? NOTIF_DEFAULTS.security.onHigh,
					onWarn:    c.security?.onWarn              ?? NOTIF_DEFAULTS.security.onWarn,
					threshold: c.security?.threshold           ?? NOTIF_DEFAULTS.security.threshold,
				},
				heartbeat: {
					onDown:     c.heartbeat?.onDown            ?? NOTIF_DEFAULTS.heartbeat.onDown,
					onRecover:  c.heartbeat?.onRecover         ?? NOTIF_DEFAULTS.heartbeat.onRecover,
					digest:     c.heartbeat?.digest            ?? NOTIF_DEFAULTS.heartbeat.digest,
					digestTime: c.heartbeat?.digestTime        ?? NOTIF_DEFAULTS.heartbeat.digestTime,
				},
				docker: {
					onCrash:            c.docker?.onCrash            ?? NOTIF_DEFAULTS.docker.onCrash,
					onRestartThreshold: c.docker?.onRestartThreshold ?? NOTIF_DEFAULTS.docker.onRestartThreshold,
					restartThreshold:   c.docker?.restartThreshold   ?? NOTIF_DEFAULTS.docker.restartThreshold,
				},
				automations: {
					onSuccess: c.automations?.onSuccess        ?? NOTIF_DEFAULTS.automations.onSuccess,
					onFailure: c.automations?.onFailure        ?? NOTIF_DEFAULTS.automations.onFailure,
				},
				study: {
					onWorkComplete:  c.study?.onWorkComplete   ?? NOTIF_DEFAULTS.study.onWorkComplete,
					onBreakComplete: c.study?.onBreakComplete  ?? NOTIF_DEFAULTS.study.onBreakComplete,
					reminder:        c.study?.reminder         ?? NOTIF_DEFAULTS.study.reminder,
					reminderTime:    c.study?.reminderTime     ?? NOTIF_DEFAULTS.study.reminderTime,
				},
				calendar: {
					remindersEnabled: c.calendar?.remindersEnabled ?? NOTIF_DEFAULTS.calendar.remindersEnabled,
					reminderTime:     c.calendar?.reminderTime     ?? NOTIF_DEFAULTS.calendar.reminderTime,
				},
				news: {
					digest:     c.news?.digest     ?? NOTIF_DEFAULTS.news.digest,
					digestTime: c.news?.digestTime ?? NOTIF_DEFAULTS.news.digestTime,
				},
				system: {
					onDiskHigh:    c.system?.onDiskHigh    ?? NOTIF_DEFAULTS.system.onDiskHigh,
					diskThreshold: c.system?.diskThreshold ?? NOTIF_DEFAULTS.system.diskThreshold,
					onCpuHigh:     c.system?.onCpuHigh     ?? NOTIF_DEFAULTS.system.onCpuHigh,
					cpuThreshold:  c.system?.cpuThreshold  ?? NOTIF_DEFAULTS.system.cpuThreshold,
					onRamHigh:     c.system?.onRamHigh     ?? NOTIF_DEFAULTS.system.onRamHigh,
					ramThreshold:  c.system?.ramThreshold  ?? NOTIF_DEFAULTS.system.ramThreshold,
				},
			};
		} catch { /* ignore */ }
	}

	async function syncNotifToBackend() {
		try {
			await fetch(`${API_BASE}/api/notifications/config`, {
				method:  'POST',
				headers: { 'Content-Type': 'application/json' },
				body:    JSON.stringify(_buildNotifCfg()),
			});
		} catch { /* offline */ }
	}

	async function saveNotifConfig() {
		if (!browser) return;
		localStorage.setItem(NOTIF_KEY, JSON.stringify(_buildNotifCfg()));
		await syncNotifToBackend();
		notifSaved = true;
		setTimeout(() => { notifSaved = false; }, 1500);
	}

	function scheduleNotifSave() {
		if (!browser) return;
		localStorage.setItem(NOTIF_KEY, JSON.stringify(_buildNotifCfg()));
		clearTimeout(notifSaveTimer);
		notifSaveTimer = setTimeout(syncNotifToBackend, 800);
	}

	// ── ABOUT ─────────────────────────────────────────────────────────────────

	type Status = 'checking' | 'online' | 'offline';
	let backendStatus: Status = 'checking';
	let ollamaAboutStatus: Status = 'checking';
	let uptimeStr = '0s';

	const sessionStart = Date.now();
	let uptimeTimer: ReturnType<typeof setInterval>;
	let healthTimer: ReturnType<typeof setInterval>;

	function formatUptime(): string {
		const s = Math.floor((Date.now() - sessionStart) / 1000);
		const m = Math.floor(s / 60);
		const h = Math.floor(m / 60);
		if (h > 0) return `${h}h ${m % 60}m`;
		if (m > 0) return `${m}m ${s % 60}s`;
		return `${s}s`;
	}

	async function checkBackend() {
		try {
			const res = await fetch(`${API_BASE}/healthz`);
			backendStatus = res.ok ? 'online' : 'offline';
		} catch {
			backendStatus = 'offline';
		}
	}

	async function checkOllamaAbout() {
		const data = await ai.health();
		ollamaAboutStatus = data?.status === 'online' ? 'online' : 'offline';
	}

	onMount(() => {
		checkBackend();
		checkOllamaAbout();
		loadRagStatus();
		loadQl();
		loadFeeds();
		loadNotifConfig();
		loadThemes();
		uptimeTimer = setInterval(() => { uptimeStr = formatUptime(); }, 1000);
		healthTimer = setInterval(() => { checkBackend(); checkOllamaAbout(); }, 30_000);
	});
	onDestroy(() => {
		clearInterval(uptimeTimer);
		clearInterval(healthTimer);
	});

	// ── EXPORT / IMPORT ───────────────────────────────────────────────────────

	let importError = '';

	function doExport() {
		if (!browser) return;
		const data = {
			nexus_settings:   $nexusSettings,
			dashboard_config: JSON.parse(localStorage.getItem('dashboard_config') ?? '{}'),
		};
		const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
		const url  = URL.createObjectURL(blob);
		const a    = document.createElement('a');
		a.href     = url;
		a.download = 'nexus_settings.json';
		a.click();
		URL.revokeObjectURL(url);
	}

	function doImport(e: Event) {
		importError = '';
		const file = (e.currentTarget as HTMLInputElement).files?.[0];
		if (!file) return;
		const reader = new FileReader();
		reader.onload = (ev) => {
			try {
				const raw  = ev.target?.result as string;
				const data = JSON.parse(raw);
				if (data.nexus_settings)   nexusSettings.importJson(JSON.stringify(data.nexus_settings));
				if (data.dashboard_config) dashConfig.importJson(JSON.stringify(data.dashboard_config));
				if (!data.nexus_settings && !data.dashboard_config) {
					nexusSettings.importJson(raw);
				}
			} catch {
				importError = 'Invalid file — could not parse JSON.';
			}
		};
		reader.readAsText(file);
	}

	// ── RESET ─────────────────────────────────────────────────────────────────

	let resetConfirm = false;

	function doReset() {
		if (!resetConfirm) { resetConfirm = true; return; }
		nexusSettings.reset();
		dashConfig.reset();
		theme.setById('terminal');
		resetConfirm = false;
	}

	// ── QUICK LINKS ───────────────────────────────────────────────────────────

	const QL_KEY = 'nexus_quicklinks';

	const QL_DEFAULTS = [
		{ id: 'ha',        name: 'Home Assistant', url: 'http://192.168.1.1:8124' },
		{ id: 'portainer', name: 'Portainer',       url: 'http://192.168.1.1:9000' },
		{ id: 'wazuh',     name: 'Wazuh',           url: 'http://192.168.1.1:5601' },
		{ id: 'jellyfin',  name: 'Jellyfin',        url: 'http://192.168.1.1:8096' },
		{ id: 'crafty',    name: 'Crafty',          url: 'http://192.168.1.1:8123' },
		{ id: 'nextcloud', name: 'Nextcloud',       url: 'http://192.168.1.1:8080' },
	];

	let quickLinks: Array<{ id: string; name: string; url: string }> = [];
	let qlNewName = '';
	let qlNewUrl  = '';

	function loadQl() {
		if (!browser) return;
		try {
			const raw = localStorage.getItem(QL_KEY);
			quickLinks = raw ? JSON.parse(raw) : [...QL_DEFAULTS];
		} catch {
			quickLinks = [...QL_DEFAULTS];
		}
	}

	function saveQl() {
		if (!browser) return;
		localStorage.setItem(QL_KEY, JSON.stringify(quickLinks));
		quickLinks = quickLinks;
	}

	function qlAdd() {
		if (!qlNewName.trim() || !qlNewUrl.trim()) return;
		const url = qlNewUrl.trim().startsWith('http') ? qlNewUrl.trim() : `http://${qlNewUrl.trim()}`;
		quickLinks = [...quickLinks, { id: `ql_${Date.now()}`, name: qlNewName.trim(), url }];
		qlNewName = '';
		qlNewUrl  = '';
		saveQl();
	}

	function qlRemove(id: string) {
		quickLinks = quickLinks.filter((l) => l.id !== id);
		saveQl();
	}

	// ── RSS FEEDS ─────────────────────────────────────────────────────────────

	let feeds: Feed[] = [];
	let feedNewUrl      = '';
	let feedNewSource   = '';
	let feedNewCategory = 'general';

	async function loadFeeds() {
		const res = await newsFeeds.list();
		if (res) feeds = res.feeds;
	}

	async function feedAdd() {
		if (!feedNewUrl.trim() || !feedNewSource.trim()) return;
		await newsFeeds.add({ url: feedNewUrl.trim(), source: feedNewSource.trim(), category: feedNewCategory });
		feedNewUrl      = '';
		feedNewSource   = '';
		feedNewCategory = 'general';
		await loadFeeds();
	}

	async function feedRemove(url: string) {
		await newsFeeds.remove(url);
		await loadFeeds();
	}

	async function feedToggle(url: string, enabled: boolean) {
		await newsFeeds.toggle(url, enabled);
		feeds = feeds.map((f) => f.url === url ? { ...f, enabled } : f);
	}

	async function feedReset() {
		if (!confirm('Reset to default feeds? This removes your custom feeds.')) return;
		await newsFeeds.reset();
		await loadFeeds();
	}
</script>

<svelte:head>
	<title>Nexus — Settings</title>
</svelte:head>

<div class="page">
	<h1 class="page-title">Settings</h1>

	<!-- ── Tab bar ─────────────────────────────────────────────────────────── -->
	<div class="tab-bar">
		{#each (['appearance', 'integrations', 'notifications', 'data', 'about'] as const) as tab}
			<button
				class="tab"
				class:active={activeTab === tab}
				on:click={() => (activeTab = tab)}
			>
				{tab.charAt(0).toUpperCase() + tab.slice(1)}
			</button>
		{/each}
	</div>

	<!-- ── APPEARANCE ──────────────────────────────────────────────────────── -->
	{#if activeTab === 'appearance'}
		<section class="card">
			<div class="card-header">Appearance</div>

			<div class="section-group">
				<span class="group-label">Theme</span>
				<div class="theme-grid">
					{#each themes as t}
						<button
							class="theme-card"
							class:active={$theme.id === t.id}
							on:click={() => { theme.set(t); dashConfig.setTheme(t.id); }}
							title={t.label}
						>
							<div class="theme-preview">
								<span class="tp-bg"  style="background:{t.vars['--bg1']}"></span>
								<span class="tp-dot" style="background:{t.vars['--accent']}"></span>
								<span class="tp-dot" style="background:{t.vars['--accent2']}"></span>
								<span class="tp-dot" style="background:{t.vars['--accent3']}"></span>
							</div>
							<span class="theme-name">{t.label}</span>
							{#if $theme.id === t.id}
								<Check size={11} strokeWidth={2.5} class="theme-check" />
							{/if}
						</button>
					{/each}
				</div>
			</div>

			<div class="section-group border-top">
				<span class="group-label">Accent color</span>
				<div class="row">
					<label class="toggle-label">
						<span class="toggle-sw" class:on={accentEnabled}>
							<input
								type="checkbox"
								class="sr-only"
								checked={accentEnabled}
								on:change={(e) => toggleAccent((e.currentTarget as HTMLInputElement).checked)}
							/>
							<span class="track"><span class="thumb"></span></span>
						</span>
						Override theme accent
					</label>
					{#if accentEnabled}
						<input
							class="color-inp"
							type="color"
							value={$dashConfig.accentOverride ?? '#3fb950'}
							on:input={onAccentInput}
						/>
					{/if}
				</div>
			</div>

			<div class="section-group border-top">
				<span class="group-label">Font size</span>
				<div class="row gap">
					<input
						class="range"
						type="range"
						min="12"
						max="16"
						step="1"
						value={fontSize}
						on:input={(e) => dashConfig.setFontSize(parseInt((e.currentTarget as HTMLInputElement).value))}
					/>
					<span class="range-val">{fontSize}px</span>
				</div>
				<div class="range-labels">
					{#each [12, 13, 14, 15, 16] as n}
						<span class="range-tick" class:active={fontSize === n}>{n}</span>
					{/each}
				</div>
			</div>

			<div class="section-group border-top">
				<span class="group-label">Sidebar position</span>
				<div class="btn-group">
					{#each (['left', 'right'] as const) as pos}
						<button
							class="seg-btn"
							class:active={$nexusSettings.sidebarPosition === pos}
							on:click={() => nexusSettings.patch({ sidebarPosition: pos })}
						>
							{pos.charAt(0).toUpperCase() + pos.slice(1)}
						</button>
					{/each}
				</div>
			</div>

			<!-- Layout -->
			<div class="section-group border-top">
				<span class="group-label">Layout</span>
				<div class="row">
					<span class="layout-current-name">{currentLayoutName}</span>
					<button class="action-btn" style="margin-left:auto" on:click={() => (showLayoutPicker = true)}>
						Change layout →
					</button>
				</div>
			</div>

			<!-- CSS Snippets -->
			<div class="section-group border-top">
				<div class="custom-css-header">
					<span class="group-label" style="margin:0">CSS Snippets</span>
					<button
						class="action-btn reload-btn"
						class:spinning={snippetReloading}
						disabled={snippetReloading}
						on:click={handleReloadSnippets}
					>
						<RefreshCw size={12} strokeWidth={1.5} />
						{snippetReloading ? 'Reloading…' : 'Reload'}
					</button>
				</div>

				<p class="custom-css-hint">
					Place <code class="ic">.css</code> files in
					<code class="ic">.nexus/snippets/</code> on disk.
					They are injected into the page automatically on load.
				</p>

				{#if $snippetFiles.length === 0}
					<p class="custom-css-empty">No snippets loaded.</p>
				{:else}
					<div class="css-file-list">
						{#each $snippetFiles as s}
							<div class="css-file-row">
								<span class="css-file-name">{s.filename}</span>
								<span class="css-file-size">{fmtBytes(s.size)}</span>
							</div>
						{/each}
					</div>
				{/if}

				<pre class="snippet-example"><span class="ex-cmt">/* Example: make security widget header red */</span>
.security .card-header &#123; color: var(--red) !important; &#125;</pre>
			</div>

			<!-- Custom Themes -->
			<div class="section-group border-top">
				<div class="custom-css-header">
					<span class="group-label" style="margin:0">Custom Themes</span>
					<button
						class="action-btn reload-btn"
						class:spinning={themeReloading}
						disabled={themeReloading}
						on:click={handleReloadThemes}
					>
						<RefreshCw size={12} strokeWidth={1.5} />
						{themeReloading ? 'Reloading…' : 'Reload'}
					</button>
				</div>

				<p class="custom-css-hint">
					Full theme files replace the entire color system. Place
					<code class="ic">.css</code> files in
					<code class="ic">.nexus/themes/</code> on disk.
				</p>

				{#if $themeFiles.length === 0}
					<p class="custom-css-empty">No custom themes found.</p>
				{:else}
					<div class="css-file-list">
						{#each $themeFiles as name}
							<div class="css-file-row">
								<span class="css-file-name">{name}</span>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		</section>
	{/if}

	<!-- ── INTEGRATIONS ────────────────────────────────────────────────────── -->
	{#if activeTab === 'integrations'}
		<!-- Ollama / AI -->
		<section class="card">
			<div class="card-header">
				<div class="intg-card-title">
					<div class="intg-icon" style="background:color-mix(in srgb,#bc8cff 12%,var(--bg2));border-color:#bc8cff">AI</div>
					<span>Ollama</span>
					<span class="intg-status-badge status-{ollamaAboutStatus}">{ollamaAboutStatus}</span>
				</div>
			</div>

			<div class="section-group">
				<label class="field-label" for="ai-model">Default model</label>
				<input
					id="ai-model"
					class="text-inp"
					type="text"
					placeholder="e.g. qwen3:8b"
					bind:value={aiModel}
				/>
			</div>

			<div class="section-group border-top">
				<label class="field-label" for="ollama-host">Ollama host</label>
				<input
					id="ollama-host"
					class="text-inp"
					type="text"
					placeholder="http://localhost:11434"
					bind:value={ollamaHost}
				/>
			</div>

			<div class="section-group border-top">
				<label class="field-label" for="sys-prompt">System prompt</label>
				<textarea
					id="sys-prompt"
					class="textarea"
					rows="4"
					placeholder="You are a helpful assistant…"
					bind:value={aiPrompt}
				></textarea>
			</div>

			<div class="section-group border-top row">
				<button class="action-btn primary-btn" on:click={saveAi}>
					{#if aiSaved}
						<Check size={13} strokeWidth={2.5} /> Saved
					{:else}
						Save AI settings
					{/if}
				</button>
				<button class="action-btn" style="margin-left:auto" on:click={checkOllamaAbout}>
					<RefreshCw size={12} strokeWidth={1.5} /> Re-check
				</button>
			</div>
		</section>

		<!-- Weather -->
		<section class="card">
			<div class="card-header">
				<div class="intg-card-title">
					<div class="intg-icon" style="background:color-mix(in srgb,#58a6ff 12%,var(--bg2));border-color:#58a6ff">WX</div>
					<span>Weather</span>
					<span class="intg-env-note">configured via backend .env</span>
				</div>
			</div>
			<div class="section-group">
				<p class="intg-hint">
					Set <code class="ic">WEATHER_API_KEY</code>, <code class="ic">WEATHER_LAT</code>,
					and <code class="ic">WEATHER_LON</code> in your <code class="ic">.env</code> file.
					The widget falls back to mock data if unset.
				</p>
			</div>
		</section>

		<!-- TryHackMe -->
		<section class="card">
			<div class="card-header">
				<div class="intg-card-title">
					<div class="intg-icon" style="background:color-mix(in srgb,#e3b341 12%,var(--bg2));border-color:#e3b341">TH</div>
					<span>TryHackMe</span>
					<span class="intg-env-note">configured via backend .env</span>
				</div>
			</div>
			<div class="section-group">
				<p class="intg-hint">
					Set <code class="ic">THM_USERNAME</code> in your <code class="ic">.env</code> file to
					display your rank and recent activity. No API key required.
				</p>
			</div>
		</section>

		<!-- Wazuh -->
		<section class="card">
			<div class="card-header">
				<div class="intg-card-title">
					<div class="intg-icon" style="background:color-mix(in srgb,#f85149 12%,var(--bg2));border-color:#f85149">WZ</div>
					<span>Wazuh</span>
					<span class="intg-env-note">configured via backend .env</span>
				</div>
			</div>
			<div class="section-group">
				<p class="intg-hint">
					Set <code class="ic">WAZUH_HOST</code>, <code class="ic">WAZUH_USER</code>,
					and <code class="ic">WAZUH_PASS</code> in your <code class="ic">.env</code> file.
					The widget falls back to mock alert data if unset.
				</p>
			</div>
		</section>

		<!-- Home Assistant -->
		<section class="card">
			<div class="card-header">
				<div class="intg-card-title">
					<div class="intg-icon" style="background:color-mix(in srgb,#ff7043 12%,var(--bg2));border-color:#ff7043">HA</div>
					<span>Home Assistant</span>
					<span class="intg-env-note">configured via backend .env</span>
				</div>
			</div>
			<div class="section-group">
				<p class="intg-hint">
					Set <code class="ic">HA_URL</code> and <code class="ic">HA_TOKEN</code> (long-lived
					access token) in your <code class="ic">.env</code> file.
				</p>
			</div>
		</section>

		<!-- MQTT -->
		<section class="card">
			<div class="card-header">
				<div class="intg-card-title">
					<div class="intg-icon" style="background:color-mix(in srgb,#3fb950 12%,var(--bg2));border-color:#3fb950">MQ</div>
					<span>MQTT</span>
					<span class="intg-env-note">configured via backend .env</span>
				</div>
			</div>
			<div class="section-group">
				<p class="intg-hint">
					Set <code class="ic">MQTT_HOST</code>, <code class="ic">MQTT_PORT</code>,
					<code class="ic">MQTT_USER</code>, and <code class="ic">MQTT_PASS</code> in your
					<code class="ic">.env</code> file.
				</p>
			</div>
		</section>

		<!-- Knowledge Base (RAG) -->
		<section class="card">
			<div class="card-header">Knowledge Base</div>

			<div class="section-group">
				<div class="rag-row">
					<div class="rag-row-left">
						<Database size={15} strokeWidth={1.5} />
						<span>Local Knowledge Base</span>
					</div>
					<span class="rag-status-text" style="color:{ragStatusColor}">{ragStatusText}</span>
				</div>

				<p class="intg-hint" style="margin-top:8px">
					Indexes your automations and notes so the AI can answer questions about your setup.
				</p>

				<div class="rag-actions">
					<button class="action-btn" disabled={reindexing} on:click={reindex}>
						{reindexing ? 'Indexing…' : 'Re-index now'}
					</button>
					{#if ragStatus?.indexed_chunks && ragStatus.indexed_chunks > 0}
						<p class="rag-sources-note">
							Sources: .nexus/automations/, .nexus/notes/, Obsidian vault (if configured)
						</p>
					{/if}
				</div>
			</div>
		</section>
	{/if}

	<!-- ── NOTIFICATIONS ───────────────────────────────────────────────────── -->
	{#if activeTab === 'notifications'}
		<section class="card">
			<div class="card-header">Notifications</div>

			<div class="section-group">
				<label class="toggle-label">
					<span class="toggle-sw" class:on={notif.master}>
						<input type="checkbox" class="sr-only" bind:checked={notif.master} on:change={scheduleNotifSave} />
						<span class="track"><span class="thumb"></span></span>
					</span>
					Enable notifications
				</label>
				<p class="notif-hint">Master switch — if off, no notifications are sent regardless of individual settings.</p>
			</div>

			<div class="section-group border-top">
				<label class="field-label" for="ntfy-server">Ntfy server URL</label>
				<input
					id="ntfy-server"
					class="text-inp"
					type="text"
					placeholder="https://ntfy.sh"
					bind:value={ntfyServer}
					on:blur={() => { saveNtfy(); scheduleNotifSave(); }}
				/>
			</div>

			<div class="section-group border-top">
				<label class="field-label" for="ntfy-topic">Ntfy topic</label>
				<input
					id="ntfy-topic"
					class="text-inp"
					type="text"
					placeholder="my-dashboard-alerts"
					bind:value={ntfyTopic}
					on:blur={() => { saveNtfy(); scheduleNotifSave(); }}
				/>
			</div>

			<div class="section-group border-top row gap">
				<button class="action-btn" on:click={testNotification}>
					<Send size={13} strokeWidth={1.5} />
					Test notification
				</button>
				{#if ntfyMsg}
					<span class="ntfy-status" class:ntfy-ok={ntfyOk}>{ntfyMsg}</span>
				{/if}
			</div>

			<div class="notif-features" class:notif-disabled={!notif.master}>

				<!-- Security -->
				<div class="notif-sub">
					<div class="notif-sub-header">Security Alerts</div>
					<div class="notif-rows">
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.security.onCrit}>
								<input type="checkbox" class="sr-only" bind:checked={notif.security.onCrit} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify on CRIT alerts
						</label>
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.security.onHigh}>
								<input type="checkbox" class="sr-only" bind:checked={notif.security.onHigh} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify on HIGH alerts
						</label>
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.security.onWarn}>
								<input type="checkbox" class="sr-only" bind:checked={notif.security.onWarn} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify on WARN alerts
						</label>
						<div class="notif-row notif-select-row">
							<span class="notif-select-label">Minimum severity threshold</span>
							<select class="notif-select" bind:value={notif.security.threshold} on:change={scheduleNotifSave} disabled={!notif.master}>
								{#each ['CRIT', 'HIGH', 'WARN', 'INFO'] as s}
									<option value={s}>{s}</option>
								{/each}
							</select>
						</div>
					</div>
				</div>

				<!-- Heartbeat -->
				<div class="notif-sub">
					<div class="notif-sub-header">Heartbeat / Services</div>
					<div class="notif-rows">
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.heartbeat.onDown}>
								<input type="checkbox" class="sr-only" bind:checked={notif.heartbeat.onDown} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify when any service goes down
						</label>
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.heartbeat.onRecover}>
								<input type="checkbox" class="sr-only" bind:checked={notif.heartbeat.onRecover} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify when service recovers
						</label>
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.heartbeat.digest}>
								<input type="checkbox" class="sr-only" bind:checked={notif.heartbeat.digest} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Daily service health digest
						</label>
						{#if notif.heartbeat.digest}
							<div class="notif-row notif-time-row">
								<span class="notif-select-label">Send digest at</span>
								<input type="time" class="notif-time" bind:value={notif.heartbeat.digestTime} on:change={scheduleNotifSave} disabled={!notif.master} />
							</div>
						{/if}
					</div>
				</div>

				<!-- Docker -->
				<div class="notif-sub">
					<div class="notif-sub-header">Docker</div>
					<div class="notif-rows">
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.docker.onCrash}>
								<input type="checkbox" class="sr-only" bind:checked={notif.docker.onCrash} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify when container exits / crashes
						</label>
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.docker.onRestartThreshold}>
								<input type="checkbox" class="sr-only" bind:checked={notif.docker.onRestartThreshold} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify when restart count exceeds threshold
						</label>
						{#if notif.docker.onRestartThreshold}
							<div class="notif-row notif-select-row">
								<span class="notif-select-label">Restart threshold</span>
								<input type="number" class="notif-num" min="1" max="20" bind:value={notif.docker.restartThreshold} on:input={scheduleNotifSave} disabled={!notif.master} />
							</div>
						{/if}
					</div>
				</div>

				<!-- Automations -->
				<div class="notif-sub">
					<div class="notif-sub-header">Automations</div>
					<div class="notif-rows">
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.automations.onSuccess}>
								<input type="checkbox" class="sr-only" bind:checked={notif.automations.onSuccess} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify when automation runs successfully
						</label>
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.automations.onFailure}>
								<input type="checkbox" class="sr-only" bind:checked={notif.automations.onFailure} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify when automation fails
						</label>
					</div>
				</div>

				<!-- Study -->
				<div class="notif-sub">
					<div class="notif-sub-header">Study / Pomodoro</div>
					<div class="notif-rows">
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.study.onWorkComplete}>
								<input type="checkbox" class="sr-only" bind:checked={notif.study.onWorkComplete} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify on work session complete
						</label>
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.study.onBreakComplete}>
								<input type="checkbox" class="sr-only" bind:checked={notif.study.onBreakComplete} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify on break complete
						</label>
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.study.reminder}>
								<input type="checkbox" class="sr-only" bind:checked={notif.study.reminder} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Daily study reminder
						</label>
						{#if notif.study.reminder}
							<div class="notif-row notif-time-row">
								<span class="notif-select-label">Remind at</span>
								<input type="time" class="notif-time" bind:value={notif.study.reminderTime} on:change={scheduleNotifSave} disabled={!notif.master} />
							</div>
						{/if}
					</div>
				</div>

				<!-- Calendar -->
				<div class="notif-sub">
					<div class="notif-sub-header">Calendar</div>
					<div class="notif-rows">
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.calendar.remindersEnabled}>
								<input type="checkbox" class="sr-only" bind:checked={notif.calendar.remindersEnabled} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Event reminders enabled
						</label>
						<div class="notif-row notif-select-row">
							<span class="notif-select-label">Remind before event</span>
							<select class="notif-select" bind:value={notif.calendar.reminderTime} on:change={scheduleNotifSave} disabled={!notif.master || !notif.calendar.remindersEnabled}>
								<option value="5m">5 minutes</option>
								<option value="15m">15 minutes</option>
								<option value="30m">30 minutes</option>
								<option value="1h">1 hour</option>
							</select>
						</div>
					</div>
				</div>

				<!-- News -->
				<div class="notif-sub">
					<div class="notif-sub-header">News</div>
					<div class="notif-rows">
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.news.digest}>
								<input type="checkbox" class="sr-only" bind:checked={notif.news.digest} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Daily news digest notification
						</label>
						{#if notif.news.digest}
							<div class="notif-row notif-time-row">
								<span class="notif-select-label">Send at</span>
								<input type="time" class="notif-time" bind:value={notif.news.digestTime} on:change={scheduleNotifSave} disabled={!notif.master} />
							</div>
						{/if}
					</div>
				</div>

				<!-- System -->
				<div class="notif-sub">
					<div class="notif-sub-header">System</div>
					<div class="notif-rows">
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.system.onDiskHigh}>
								<input type="checkbox" class="sr-only" bind:checked={notif.system.onDiskHigh} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify when disk usage exceeds threshold
						</label>
						{#if notif.system.onDiskHigh}
							<div class="notif-row notif-slider-row">
								<span class="notif-select-label">Disk threshold: {notif.system.diskThreshold}%</span>
								<input type="range" class="range notif-range" min="70" max="95" step="5" bind:value={notif.system.diskThreshold} on:input={scheduleNotifSave} disabled={!notif.master} />
							</div>
						{/if}
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.system.onCpuHigh}>
								<input type="checkbox" class="sr-only" bind:checked={notif.system.onCpuHigh} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify when CPU stays above threshold for 5 min
						</label>
						{#if notif.system.onCpuHigh}
							<div class="notif-row notif-slider-row">
								<span class="notif-select-label">CPU threshold: {notif.system.cpuThreshold}%</span>
								<input type="range" class="range notif-range" min="70" max="95" step="5" bind:value={notif.system.cpuThreshold} on:input={scheduleNotifSave} disabled={!notif.master} />
							</div>
						{/if}
						<label class="notif-row">
							<span class="toggle-sw" class:on={notif.system.onRamHigh}>
								<input type="checkbox" class="sr-only" bind:checked={notif.system.onRamHigh} on:change={scheduleNotifSave} disabled={!notif.master} />
								<span class="track"><span class="thumb"></span></span>
							</span>
							Notify when RAM exceeds threshold
						</label>
						{#if notif.system.onRamHigh}
							<div class="notif-row notif-slider-row">
								<span class="notif-select-label">RAM threshold: {notif.system.ramThreshold}%</span>
								<input type="range" class="range notif-range" min="70" max="95" step="5" bind:value={notif.system.ramThreshold} on:input={scheduleNotifSave} disabled={!notif.master} />
							</div>
						{/if}
					</div>
				</div>

			</div>

			<div class="section-group border-top row">
				<button class="action-btn primary-btn" on:click={saveNotifConfig}>
					{#if notifSaved}
						<Check size={13} strokeWidth={2.5} /> Saved
					{:else}
						Save notification settings
					{/if}
				</button>
			</div>
		</section>
	{/if}

	<!-- ── DATA ────────────────────────────────────────────────────────────── -->
	{#if activeTab === 'data'}
		<!-- Dashboard Layout -->
		<section class="card">
			<div class="card-header">Dashboard Layout</div>

			<div class="section-group">
				<span class="group-label">Column count</span>
				<div class="btn-group">
					{#each ([2, 3, 4] as const) as n}
						<button
							class="seg-btn"
							class:active={$dashConfig.columns === n}
							on:click={() => dashConfig.setColumns(n)}
						>
							{n}
						</button>
					{/each}
				</div>
			</div>

			<div class="section-group border-top">
				<span class="group-label">Compact mode</span>
				<div class="row">
					<label class="toggle-label">
						<span class="toggle-sw" class:on={$nexusSettings.compactMode}>
							<input
								type="checkbox"
								class="sr-only"
								checked={$nexusSettings.compactMode}
								on:change={(e) => nexusSettings.patch({ compactMode: (e.currentTarget as HTMLInputElement).checked })}
							/>
							<span class="track"><span class="thumb"></span></span>
						</span>
						Reduce padding &amp; spacing
					</label>
				</div>
			</div>

			<div class="section-group border-top">
				<span class="group-label">Widget visibility</span>
				<div class="widget-list">
					{#each WIDGET_DEFS as def}
						{@const widget  = $dashConfig.widgets.find((w) => w.id === def.id)}
						{@const enabled = widget?.enabled ?? def.defaultEnabled}
						<label class="widget-row">
							<span class="widget-icon" aria-hidden="true">{def.icon}</span>
							<span class="widget-name">{def.label}</span>
							<span class="toggle-sw" class:on={enabled}>
								<input
									type="checkbox"
									class="sr-only"
									checked={enabled}
									on:change={(e) => dashConfig.updateWidget(def.id, { enabled: (e.currentTarget as HTMLInputElement).checked })}
								/>
								<span class="track"><span class="thumb"></span></span>
							</span>
						</label>
					{/each}
				</div>
			</div>
		</section>

		<!-- Quick Links -->
		<section class="card">
			<div class="card-header">Quick Links</div>

			<div class="section-group">
				<span class="group-label">Services</span>
				{#each quickLinks as link (link.id)}
					<div class="ql-row">
						<span class="ql-name">{link.name}</span>
						<span class="ql-url">{link.url}</span>
						<button class="ql-rm" title="Remove" on:click={() => qlRemove(link.id)}>✕</button>
					</div>
				{/each}
				<div class="ql-add-row">
					<input
						class="text-inp ql-name-input"
						placeholder="Name"
						bind:value={qlNewName}
						on:keydown={(e) => e.key === 'Enter' && qlAdd()}
					/>
					<input
						class="text-inp ql-url-input"
						placeholder="http://…"
						bind:value={qlNewUrl}
						on:keydown={(e) => e.key === 'Enter' && qlAdd()}
					/>
					<button class="action-btn" on:click={qlAdd}>Add</button>
				</div>
			</div>
		</section>

		<!-- RSS Feeds -->
		<section class="card">
			<div class="card-header">RSS Feeds</div>

			<div class="section-group">
				<p class="section-desc">Feeds shown on the News page. Fetched every 60 minutes.</p>

				<div class="feed-list">
					{#each feeds as feed (feed.url)}
						<div class="feed-row">
							<!-- Toggle -->
							<label class="toggle-label" title={feed.enabled ? 'Disable feed' : 'Enable feed'}>
								<span class="toggle-sw" class:on={feed.enabled}>
									<input
										type="checkbox"
										class="sr-only"
										checked={feed.enabled}
										on:change={(e) => feedToggle(feed.url, (e.currentTarget as HTMLInputElement).checked)}
									/>
									<span class="track"><span class="thumb"></span></span>
								</span>
							</label>
							<!-- Source + URL -->
							<div class="feed-info">
								<span class="feed-source">{feed.source}</span>
								<span class="feed-url">{feed.url}</span>
							</div>
							<!-- Category badge -->
							<span class="feed-category">{feed.category}</span>
							<!-- Delete -->
							<button class="feed-rm" title="Remove feed" on:click={() => feedRemove(feed.url)}>
								<Trash2 size={12} strokeWidth={1.6} />
							</button>
						</div>
					{/each}
				</div>

				<!-- Add feed row -->
				<div class="feed-add-row">
					<input
						class="text-inp feed-url-inp"
						type="url"
						placeholder="https://example.com/feed.rss"
						bind:value={feedNewUrl}
						on:keydown={(e) => e.key === 'Enter' && feedAdd()}
					/>
					<input
						class="text-inp feed-src-inp"
						type="text"
						placeholder="Source name"
						bind:value={feedNewSource}
						on:keydown={(e) => e.key === 'Enter' && feedAdd()}
					/>
					<select class="text-inp feed-cat-sel" bind:value={feedNewCategory}>
						<option value="cybersecurity">cybersecurity</option>
						<option value="tech">tech</option>
						<option value="ai">ai</option>
						<option value="selfhosted">selfhosted</option>
						<option value="general">general</option>
					</select>
					<button class="action-btn feed-add-btn" on:click={feedAdd}>Add</button>
				</div>

				<button class="feed-reset-link" on:click={feedReset}>Reset to defaults</button>
			</div>
		</section>

		<!-- Export / Import -->
		<section class="card">
			<div class="card-header">Config Data</div>
			<div class="section-group">
				<div class="action-row">
					<button class="action-btn" on:click={doExport}>
						<Download size={13} strokeWidth={1.5} />
						Export settings
					</button>
					<label class="action-btn" title="Import settings JSON">
						<Upload size={13} strokeWidth={1.5} />
						Import settings
						<input class="sr-only" type="file" accept=".json,application/json" on:change={doImport} />
					</label>
				</div>
				{#if importError}
					<p class="error-msg">{importError}</p>
				{/if}
			</div>
		</section>

		<!-- Danger Zone -->
		<div class="danger-zone">
			<div class="danger-zone-header">Danger Zone</div>
			<div class="danger-zone-body">
				<div>
					<p class="danger-zone-desc">Reset all settings and widget config to factory defaults. This cannot be undone.</p>
				</div>
				<button
					class="action-btn reset-btn"
					class:confirm={resetConfirm}
					on:click={doReset}
					on:blur={() => { resetConfirm = false; }}
				>
					<RotateCcw size={13} strokeWidth={1.5} />
					{resetConfirm ? 'Click again to confirm' : 'Reset all'}
				</button>
			</div>
		</div>
	{/if}

	<LayoutPicker bind:open={showLayoutPicker} on:close={() => (showLayoutPicker = false)} />

	<!-- ── ABOUT ────────────────────────────────────────────────────────────── -->
	{#if activeTab === 'about'}
		<section class="card">
			<div class="card-header">About Nexus</div>

			<div class="about-grid">
				<span class="about-key">Version</span>
				<span class="about-val">{APP_VERSION}</span>

				<span class="about-key">Backend</span>
				<span class="about-val status-{backendStatus}">
					<span class="status-dot"></span>
					{backendStatus}
					<button class="refresh-btn" title="Re-check" on:click={checkBackend}>
						<RefreshCw size={11} strokeWidth={2} />
					</button>
				</span>

				<span class="about-key">Ollama</span>
				<span class="about-val status-{ollamaAboutStatus}">
					<span class="status-dot"></span>
					{ollamaAboutStatus}
					<button class="refresh-btn" title="Re-check" on:click={checkOllamaAbout}>
						<RefreshCw size={11} strokeWidth={2} />
					</button>
				</span>

				<span class="about-key">Session uptime</span>
				<span class="about-val">{uptimeStr}</span>

				<span class="about-key">Stack</span>
				<span class="about-val">SvelteKit + FastAPI + SQLite</span>

				<span class="about-key">Storage</span>
				<span class="about-val">Local — no cloud, no telemetry</span>
			</div>
		</section>
	{/if}
</div>

<style>
	/* ── Page ────────────────────────────────────────────────────────────── */
	.page {
		max-width: 600px;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.page-title {
		font-size: 1rem;
		font-weight: 700;
		color: var(--text0);
		margin: 0 0 0.1rem;
	}

	/* ── Tab bar ─────────────────────────────────────────────────────────── */
	.tab-bar {
		display: flex;
		align-items: stretch;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 0 4px;
		gap: 2px;
		overflow-x: auto;
	}

	.tab {
		height: 40px;
		padding: 0 14px;
		background: none;
		border: none;
		border-bottom: 2px solid transparent;
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		cursor: pointer;
		white-space: nowrap;
		transition: color 0.12s, border-color 0.12s;
		flex-shrink: 0;
	}

	.tab:hover { color: var(--text0); }

	.tab.active {
		color: var(--text0);
		border-bottom-color: var(--accent);
	}

	/* ── Card ────────────────────────────────────────────────────────────── */
	.card {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
	}

	.card-header {
		padding: 0.45rem 0.85rem;
		background: var(--bg2);
		border-bottom: 1px solid var(--border);
		font-size: 0.62rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text2);
	}

	/* ── Section groups ──────────────────────────────────────────────────── */
	.section-group {
		padding: 0.75rem 0.85rem;
	}

	.section-group.border-top {
		border-top: 1px solid var(--border);
	}

	.group-label {
		display: block;
		font-size: 0.68rem;
		font-weight: 600;
		color: var(--text1);
		margin-bottom: 0.55rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}

	.field-label {
		display: block;
		font-size: 0.68rem;
		font-weight: 600;
		color: var(--text1);
		margin-bottom: 0.4rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
	}

	/* ── Theme cards ─────────────────────────────────────────────────────── */
	.theme-grid {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: 0.5rem;
	}

	.theme-card {
		position: relative;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.35rem;
		padding: 0.55rem 0.4rem 0.45rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		cursor: pointer;
		transition: border-color 0.12s, background 0.12s;
	}

	.theme-card:hover { border-color: var(--text1); }

	.theme-card.active {
		border-color: var(--accent);
		background: color-mix(in srgb, var(--accent) 10%, var(--bg2));
	}

	.theme-preview {
		position: relative;
		width: 100%;
		height: 32px;
		border-radius: 3px;
		overflow: hidden;
		display: flex;
		align-items: flex-end;
		gap: 3px;
		padding: 4px;
	}

	.tp-bg {
		position: absolute;
		inset: 0;
		z-index: 0;
	}

	.tp-dot {
		position: relative;
		z-index: 1;
		width: 7px;
		height: 7px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.theme-name {
		font-size: 0.62rem;
		color: var(--text1);
		font-family: var(--font-mono);
		white-space: nowrap;
	}

	.theme-card.active .theme-name { color: var(--accent); }

	:global(.theme-check) {
		position: absolute;
		top: 4px;
		right: 4px;
		color: var(--accent);
	}

	/* ── Toggle switch ───────────────────────────────────────────────────── */
	.sr-only {
		position: absolute;
		width: 1px; height: 1px;
		overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap;
	}

	.toggle-sw { display: inline-flex; }

	.track {
		display: flex;
		align-items: center;
		width: 32px; height: 18px;
		background: var(--bg3);
		border: 1px solid var(--border);
		border-radius: 999px;
		padding: 2px;
		cursor: pointer;
		transition: background 0.15s, border-color 0.15s;
	}

	.toggle-sw.on .track {
		background: color-mix(in srgb, var(--accent) 30%, var(--bg3));
		border-color: var(--accent);
	}

	.thumb {
		width: 12px; height: 12px;
		border-radius: 50%;
		background: var(--text2);
		transition: transform 0.15s, background 0.15s;
	}

	.toggle-sw.on .thumb {
		transform: translateX(14px);
		background: var(--accent);
	}

	/* ── Row helpers ─────────────────────────────────────────────────────── */
	.row {
		display: flex;
		align-items: center;
	}

	.row.gap { gap: 0.6rem; }

	.toggle-label {
		display: flex;
		align-items: center;
		gap: 0.55rem;
		cursor: pointer;
		font-size: 0.75rem;
		color: var(--text1);
		flex: 1;
		user-select: none;
	}

	.color-inp {
		width: 32px; height: 26px;
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 1px;
		background: var(--bg2);
		cursor: pointer;
	}

	/* ── Font size range ─────────────────────────────────────────────────── */
	.range {
		flex: 1;
		accent-color: var(--accent);
		cursor: pointer;
	}

	.range-val {
		font-size: 0.75rem;
		color: var(--text0);
		min-width: 32px;
		text-align: right;
	}

	.range-labels {
		display: flex;
		justify-content: space-between;
		padding: 0.2rem 0 0;
	}

	.range-tick {
		font-size: 0.6rem;
		color: var(--text2);
		transition: color 0.1s;
	}

	.range-tick.active { color: var(--accent); }

	/* ── Segment buttons ─────────────────────────────────────────────────── */
	.btn-group {
		display: flex;
		gap: 0.4rem;
	}

	.seg-btn {
		padding: 0.3rem 0.85rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.75rem;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s, background 0.1s;
	}

	.seg-btn:hover { color: var(--text0); border-color: var(--accent); }

	.seg-btn.active {
		color: var(--accent);
		border-color: var(--accent);
		background: color-mix(in srgb, var(--accent) 15%, var(--bg2));
	}

	/* ── Widget list ─────────────────────────────────────────────────────── */
	.widget-list {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.widget-row {
		display: flex;
		align-items: center;
		gap: 0.55rem;
		padding: 0.38rem 0.4rem;
		border-radius: 4px;
		cursor: pointer;
		transition: background 0.1s;
		user-select: none;
	}

	.widget-row:hover { background: var(--bg2); }

	.widget-icon {
		font-size: 0.9rem;
		width: 1.4rem;
		text-align: center;
		flex-shrink: 0;
	}

	.widget-name {
		flex: 1;
		font-size: 0.75rem;
		color: var(--text0);
	}

	/* ── Text inputs ─────────────────────────────────────────────────────── */
	.text-inp {
		width: 100%;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-size: 0.78rem;
		padding: 0.38rem 0.6rem;
		transition: border-color 0.12s;
		outline: none;
	}

	.text-inp:focus { border-color: var(--accent); }

	.textarea {
		width: 100%;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-size: 0.78rem;
		font-family: var(--font-mono);
		padding: 0.38rem 0.6rem;
		resize: vertical;
		outline: none;
		line-height: 1.55;
		transition: border-color 0.12s;
	}

	.textarea:focus { border-color: var(--accent); }

	/* ── Action buttons ──────────────────────────────────────────────────── */
	.action-row {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.action-btn {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.35rem 0.75rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s, background 0.1s;
	}

	.action-btn:hover { color: var(--text0); border-color: var(--accent); }

	.primary-btn {
		color: var(--accent);
		border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
		background: color-mix(in srgb, var(--accent) 8%, var(--bg2));
	}

	.primary-btn:hover {
		background: color-mix(in srgb, var(--accent) 16%, var(--bg2));
		border-color: var(--accent);
	}

	.reset-btn:hover { border-color: var(--red); color: var(--red); }

	.reset-btn.confirm {
		border-color: var(--red);
		color: var(--red);
		background: color-mix(in srgb, var(--red) 10%, var(--bg2));
	}

	/* ── Integrations ────────────────────────────────────────────────────── */
	.intg-card-title {
		display: flex;
		align-items: center;
		gap: 0.6rem;
	}

	.intg-icon {
		width: 32px;
		height: 32px;
		border: 1px solid;
		border-radius: 6px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		color: var(--text1);
		flex-shrink: 0;
	}

	.intg-status-badge {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		padding: 0.1rem 0.45rem;
		border-radius: 999px;
		border: 1px solid var(--border);
		background: var(--bg2);
		color: var(--text2);
		margin-left: auto;
	}

	.intg-status-badge.status-online  { color: var(--green); border-color: color-mix(in srgb, var(--green) 40%, var(--border)); background: color-mix(in srgb, var(--green) 8%, var(--bg2)); }
	.intg-status-badge.status-offline { color: var(--red);   border-color: color-mix(in srgb, var(--red)   40%, var(--border)); background: color-mix(in srgb, var(--red)   8%, var(--bg2)); }

	.intg-env-note {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		margin-left: auto;
	}

	.intg-hint {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
		line-height: 1.6;
		margin: 0;
	}

	/* ── Ntfy status ─────────────────────────────────────────────────────── */
	.ntfy-status {
		font-size: 0.7rem;
		color: var(--red);
		font-family: var(--font-mono);
	}

	.ntfy-status.ntfy-ok { color: var(--green); }

	/* ── Notification settings ───────────────────────────────────────────── */
	.notif-hint {
		margin: 0.35rem 0 0;
		font-size: 0.68rem;
		color: var(--text2);
		font-family: var(--font-mono);
		line-height: 1.45;
	}

	.notif-features {
		transition: opacity 0.18s;
	}

	.notif-features.notif-disabled {
		opacity: 0.35;
		pointer-events: none;
		user-select: none;
	}

	.notif-sub {
		border-top: 1px solid var(--border);
	}

	.notif-sub-header {
		padding: 0.45rem 0.85rem 0;
		font-size: 0.6rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text2);
	}

	.notif-rows {
		padding: 0.3rem 0.85rem 0.6rem;
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}

	.notif-row {
		display: flex;
		align-items: center;
		gap: 0.55rem;
		cursor: pointer;
		font-size: 0.75rem;
		color: var(--text1);
		user-select: none;
		min-height: 1.6rem;
	}

	.notif-select-row,
	.notif-time-row,
	.notif-slider-row {
		cursor: default;
		padding-left: 0.25rem;
	}

	.notif-select-label {
		flex: 1;
		font-size: 0.7rem;
		color: var(--text2);
	}

	.notif-select {
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		padding: 0.22rem 0.45rem;
		outline: none;
		cursor: pointer;
		transition: border-color 0.12s;
	}

	.notif-select:focus { border-color: var(--accent); }

	.notif-time {
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		padding: 0.22rem 0.4rem;
		outline: none;
		transition: border-color 0.12s;
	}

	.notif-time:focus { border-color: var(--accent); }

	.notif-num {
		width: 56px;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		padding: 0.22rem 0.4rem;
		outline: none;
		text-align: center;
		transition: border-color 0.12s;
	}

	.notif-num:focus { border-color: var(--accent); }

	.notif-range {
		flex: 1;
		max-width: 130px;
	}

	/* ── About grid ──────────────────────────────────────────────────────── */
	.about-grid {
		display: grid;
		grid-template-columns: 130px 1fr;
	}

	.about-key,
	.about-val {
		padding: 0.45rem 0.85rem;
		font-size: 0.75rem;
		font-family: var(--font-mono);
		border-bottom: 1px solid var(--border);
	}

	.about-key {
		color: var(--text2);
		font-size: 0.68rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		background: var(--bg2);
	}

	.about-val {
		color: var(--text0);
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.about-key:last-of-type,
	.about-val:last-of-type { border-bottom: none; }

	.about-val.status-online   { color: var(--green); }
	.about-val.status-offline  { color: var(--red);   }
	.about-val.status-checking { color: var(--yellow); }

	.status-dot {
		width: 6px; height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
		background: currentColor;
	}

	.refresh-btn {
		display: inline-flex;
		align-items: center;
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		padding: 2px;
		border-radius: 3px;
		transition: color 0.1s;
		margin-left: auto;
	}

	.refresh-btn:hover { color: var(--text0); }

	/* ── Quick Links ─────────────────────────────────────────────────────── */
	.ql-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.3rem 0;
		border-bottom: 1px solid var(--border);
	}

	.ql-name {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text0);
		min-width: 100px;
		flex-shrink: 0;
	}

	.ql-url {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.ql-rm {
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		font-size: 0.72rem;
		padding: 0.1rem 0.3rem;
		border-radius: 3px;
		flex-shrink: 0;
		min-height: unset;
		transition: color 0.1s;
	}

	.ql-rm:hover { color: var(--red); }

	.ql-add-row {
		display: flex;
		gap: 0.4rem;
		margin-top: 0.5rem;
		flex-wrap: wrap;
	}

	.ql-name-input { flex: 0 0 120px; }
	.ql-url-input  { flex: 1; min-width: 160px; }

	/* ── RSS Feeds ───────────────────────────────────────────────────────── */
	.section-desc {
		font-size: 11px;
		color: #8b949e;
		margin: 0 0 0.6rem;
	}

	.feed-list {
		display: flex;
		flex-direction: column;
	}

	.feed-row {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 10px 0;
		border-bottom: 1px solid var(--border);
	}

	.feed-info {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: 2px;
		min-width: 0;
	}

	.feed-source {
		font-family: var(--font-ui);
		font-size: 13px;
		color: #e6edf3;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.feed-url {
		font-family: var(--font-mono);
		font-size: 11px;
		color: #484f58;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.feed-category {
		font-family: var(--font-mono);
		font-size: 10px;
		color: var(--text1);
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 2px 6px;
		flex-shrink: 0;
		white-space: nowrap;
	}

	.feed-rm {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
		height: 24px;
		background: none;
		border: none;
		color: #484f58;
		cursor: pointer;
		border-radius: 4px;
		flex-shrink: 0;
		min-height: unset;
		transition: color 0.1s, background 0.1s;
		padding: 0;
	}
	.feed-rm:hover { color: #f85149; background: color-mix(in srgb, #f85149 10%, transparent); }

	.feed-add-row {
		display: flex;
		gap: 0.4rem;
		margin-top: 0.65rem;
		flex-wrap: wrap;
	}

	.feed-url-inp { flex: 1 1 220px; }
	.feed-src-inp { flex: 0 1 140px; }
	.feed-cat-sel { flex: 0 0 110px; }
	.feed-add-btn { flex-shrink: 0; }

	.feed-reset-link {
		display: inline-block;
		margin-top: 0.55rem;
		font-size: 11px;
		color: #484f58;
		background: none;
		border: none;
		padding: 0;
		cursor: pointer;
		transition: color 0.1s;
		min-height: unset;
	}
	.feed-reset-link:hover { color: var(--text1); }

	/* ── Error msg ───────────────────────────────────────────────────────── */
	.error-msg {
		margin-top: 0.65rem;
		font-size: 0.7rem;
		color: var(--red);
		background: color-mix(in srgb, var(--red) 10%, var(--bg1));
		border: 1px solid color-mix(in srgb, var(--red) 25%, var(--border));
		border-radius: 4px;
		padding: 0.35rem 0.5rem;
	}

	/* ── Danger zone ─────────────────────────────────────────────────────── */
	.danger-zone {
		background: #0e0808;
		border: 1px solid #3d1515;
		border-radius: var(--radius);
		overflow: hidden;
	}

	.danger-zone-header {
		padding: 0.45rem 0.85rem;
		background: #150c0c;
		border-bottom: 1px solid #3d1515;
		font-size: 0.62rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--red);
	}

	.danger-zone-body {
		padding: 0.85rem;
		display: flex;
		align-items: center;
		gap: 1rem;
	}

	.danger-zone-desc {
		font-size: 0.7rem;
		color: var(--text2);
		font-family: var(--font-mono);
		margin: 0;
		line-height: 1.5;
	}

	/* ── CSS Snippets / Custom Themes ────────────────────────────────────── */
	.custom-css-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: 0.45rem;
	}

	.custom-css-hint {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
		line-height: 1.55;
		margin: 0 0 0.55rem;
	}

	.ic {
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 3px;
		padding: 0.05em 0.3em;
		font-family: var(--font-mono);
		font-size: 0.9em;
		color: var(--accent3);
	}

	.custom-css-empty {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
		margin: 0 0 0.5rem;
	}

	.css-file-list {
		display: flex;
		flex-direction: column;
		gap: 3px;
		margin-bottom: 0.55rem;
	}

	.css-file-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.28rem 0.5rem;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 4px;
	}

	.css-file-name {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text0);
		flex: 1;
	}

	.css-file-size {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		flex-shrink: 0;
	}

	.snippet-example {
		background: var(--bg0);
		border: 1px solid var(--border);
		border-left: 3px solid var(--accent3);
		border-radius: 4px;
		padding: 0.5rem 0.65rem;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--text1);
		line-height: 1.65;
		margin: 0;
		overflow-x: auto;
		white-space: pre;
	}

	.ex-cmt { color: var(--text2); display: block; }

	.reload-btn :global(svg) { flex-shrink: 0; }
	.reload-btn.spinning :global(svg) { animation: spin 0.8s linear infinite; }
	@keyframes spin { to { transform: rotate(360deg); } }

	/* ── Layout ──────────────────────────────────────────────────────────── */
	.layout-current-name {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--accent);
	}

	/* ── RAG / Knowledge Base ────────────────────────────────────────────── */
	.rag-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.rag-row-left {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		font-size: 0.78rem;
		color: var(--text0);
	}

	.rag-status-text {
		font-family: var(--font-mono);
		font-size: 11px;
		flex-shrink: 0;
	}

	.rag-actions {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		margin-top: 0.65rem;
		align-items: flex-start;
	}

	.rag-sources-note {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text2);
		margin: 0;
		line-height: 1.5;
	}
</style>
