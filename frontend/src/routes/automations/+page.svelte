<script lang="ts">
	import { onMount } from 'svelte';
	import { Zap, Play, Trash2, Plus, CheckCircle, XCircle } from '@lucide/svelte';

	const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8088';

	// ── Types ─────────────────────────────────────────────────────────────────

	interface Automation {
		id:             number;
		name:           string;
		description:    string;
		enabled:        boolean;
		trigger_type:   string;
		trigger_config: Record<string, any>;
		action_type:    string;
		action_config:  Record<string, any>;
		last_run:       string | null;
		run_count:      number;
		created_at:     string;
	}

	interface RunLog {
		id:            number;
		automation_id: number;
		ran_at:        string;
		success:       boolean;
		result:        string;
	}

	// ── State ─────────────────────────────────────────────────────────────────

	let automations: Automation[] = [];
	let selectedId:  number | null = null;
	let runLogs:     RunLog[] = [];
	let running      = false;
	let saving       = false;
	let dirty        = false;
	let runResult:   { success: boolean; result: string } | null = null;

	// Available services / containers from heartbeat
	let hbServices: string[] = [];
	let dockerContainers: string[] = [];

	// ── Form state ────────────────────────────────────────────────────────────

	let formName        = '';
	let formDesc        = '';
	let formEnabled     = true;
	let formTrigger     = 'schedule';
	let formAction      = 'ntfy_notify';

	// Trigger fields
	let schedInterval   = '1h';
	let schedTime       = '08:00';
	let wazuhSeverity   = 'CRIT';
	let svcName         = '';
	let dockerContainer = '';
	let dockerThreshold = 3;

	// Action fields
	let ntfyTitle    = '';
	let ntfyMessage  = '';
	let ntfyPriority = 3;
	let restartContainer = '';
	let webhookUrl     = '';
	let webhookMethod  = 'POST';
	let webhookHeaders = '';
	let webhookBody    = '';
	let logLevel    = 'INFO';
	let logMessage  = '';
	let bashCommand = '';

	// ── Trigger / action option lists ─────────────────────────────────────────

	const TRIGGER_OPTS = [
		{ value: 'schedule',       label: 'Schedule' },
		{ value: 'wazuh_alert',    label: 'Wazuh Alert' },
		{ value: 'service_down',   label: 'Service Down' },
		{ value: 'service_up',     label: 'Service Up' },
		{ value: 'docker_restart', label: 'Docker Restart' },
	];

	const ACTION_OPTS = [
		{ value: 'ntfy_notify',    label: 'Send Notification' },
		{ value: 'docker_restart', label: 'Restart Container' },
		{ value: 'webhook',        label: 'Webhook' },
		{ value: 'log_entry',      label: 'Log Entry' },
		{ value: 'bash_script',    label: 'Run Script' },
	];

	const SEV_OPTS   = ['CRIT', 'HIGH', 'WARN', 'INFO'];
	const LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
	const INTERVALS  = [
		{ value: '15m',   label: 'Every 15 minutes' },
		{ value: '1h',    label: 'Every hour' },
		{ value: '6h',    label: 'Every 6 hours' },
		{ value: 'daily', label: 'Daily' },
	];

	// ── Templates ─────────────────────────────────────────────────────────────

	const TEMPLATES = [
		{
			label: 'Alert me on CRIT security alert',
			icon: '🚨',
			apply() {
				formName    = 'Critical Security Alert';
				formDesc    = 'Send push notification when Wazuh detects a critical alert';
				formTrigger = 'wazuh_alert';
				wazuhSeverity = 'CRIT';
				formAction  = 'ntfy_notify';
				ntfyTitle   = '🚨 Critical Security Alert';
				ntfyMessage = 'Wazuh detected a CRITICAL security event on your homelab.';
				ntfyPriority = 5;
			},
		},
		{
			label: 'Daily system report',
			icon: '📊',
			apply() {
				formName    = 'Daily System Report';
				formDesc    = 'Send a daily notification at 08:00';
				formTrigger = 'schedule';
				schedInterval = 'daily';
				schedTime   = '08:00';
				formAction  = 'ntfy_notify';
				ntfyTitle   = '📊 Daily System Report';
				ntfyMessage = 'Your homelab dashboard daily report is ready.';
				ntfyPriority = 2;
			},
		},
		{
			label: 'Restart container on crash',
			icon: '🔄',
			apply() {
				formName    = 'Auto-Restart Crashed Container';
				formDesc    = 'Restart a container when it exceeds restart threshold';
				formTrigger = 'docker_restart';
				dockerThreshold = 3;
				formAction  = 'docker_restart';
			},
		},
		{
			label: 'Service down alert',
			icon: '📡',
			apply() {
				formName    = 'Service Down Alert';
				formDesc    = 'Notify when a monitored service goes offline';
				formTrigger = 'service_down';
				formAction  = 'ntfy_notify';
				ntfyTitle   = '📡 Service Down';
				ntfyMessage = 'A monitored service has gone offline.';
				ntfyPriority = 4;
			},
		},
	];

	// ── API helpers ───────────────────────────────────────────────────────────

	async function fetchAll() {
		try {
			const r = await fetch(`${BASE}/api/automations`);
			if (r.ok) automations = await r.json();
		} catch { /* offline */ }
	}

	async function fetchLogs(id: number) {
		try {
			const r = await fetch(`${BASE}/api/automations/${id}/logs`);
			if (r.ok) runLogs = await r.json();
		} catch { runLogs = []; }
	}

	async function fetchHeartbeat() {
		try {
			const r = await fetch(`${BASE}/api/heartbeat/status`);
			if (!r.ok) return;
			const d = await r.json();
			const names: string[] = Object.keys(d.services ?? {});
			hbServices = names.filter((n) => !n.startsWith('docker/'));
			dockerContainers = names
				.filter((n) => n.startsWith('docker/'))
				.map((n) => n.slice(7));
		} catch { /* offline */ }
	}

	function applyTemplate(t: typeof TEMPLATES[number]) {
		clearForm();
		t.apply();
		dirty = true;
		selectedId = null;
	}

	// ── Form sync ─────────────────────────────────────────────────────────────

	function clearForm() {
		formName = ''; formDesc = ''; formEnabled = true;
		formTrigger = 'schedule'; formAction = 'ntfy_notify';
		schedInterval = '1h'; schedTime = '08:00';
		wazuhSeverity = 'CRIT'; svcName = ''; dockerContainer = ''; dockerThreshold = 3;
		ntfyTitle = ''; ntfyMessage = ''; ntfyPriority = 3;
		restartContainer = ''; webhookUrl = ''; webhookMethod = 'POST';
		webhookHeaders = ''; webhookBody = '';
		logLevel = 'INFO'; logMessage = ''; bashCommand = '';
		dirty = false; runResult = null; runLogs = [];
	}

	function loadIntoForm(a: Automation) {
		formName    = a.name;
		formDesc    = a.description;
		formEnabled = a.enabled;
		formTrigger = a.trigger_type;
		formAction  = a.action_type;

		const tc = a.trigger_config;
		schedInterval   = tc.interval   ?? '1h';
		schedTime       = tc.time       ?? '08:00';
		wazuhSeverity   = tc.min_severity ?? 'CRIT';
		svcName         = tc.service    ?? '';
		dockerContainer = tc.container  ?? '';
		dockerThreshold = tc.threshold  ?? 3;

		const ac = a.action_config;
		ntfyTitle        = ac.title     ?? '';
		ntfyMessage      = ac.message   ?? '';
		ntfyPriority     = ac.priority  ?? 3;
		restartContainer = ac.container ?? '';
		webhookUrl       = ac.url       ?? '';
		webhookMethod    = ac.method    ?? 'POST';
		webhookHeaders   = typeof ac.headers === 'string' ? ac.headers : JSON.stringify(ac.headers ?? {}, null, 2);
		webhookBody      = ac.body      ?? '';
		logLevel         = ac.level     ?? 'INFO';
		logMessage       = ac.message   ?? '';
		bashCommand      = ac.command   ?? '';

		dirty = false; runResult = null;
	}

	async function selectAutomation(a: Automation) {
		selectedId = a.id;
		loadIntoForm(a);
		await fetchLogs(a.id);
	}

	function newAutomation() {
		selectedId = null;
		clearForm();
	}

	// ── Build config objects from form ────────────────────────────────────────

	function buildTriggerConfig(): Record<string, any> {
		if (formTrigger === 'schedule')
			return { interval: schedInterval, time: schedTime };
		if (formTrigger === 'wazuh_alert')
			return { min_severity: wazuhSeverity };
		if (formTrigger === 'service_down' || formTrigger === 'service_up')
			return { service: svcName };
		if (formTrigger === 'docker_restart')
			return { container: dockerContainer, threshold: dockerThreshold };
		return {};
	}

	function buildActionConfig(): Record<string, any> {
		if (formAction === 'ntfy_notify')
			return { title: ntfyTitle, message: ntfyMessage, priority: ntfyPriority };
		if (formAction === 'docker_restart')
			return { container: restartContainer };
		if (formAction === 'webhook') {
			let h: any = webhookHeaders;
			try { h = JSON.parse(webhookHeaders); } catch { /* keep as string */ }
			return { url: webhookUrl, method: webhookMethod, headers: h, body: webhookBody };
		}
		if (formAction === 'log_entry')
			return { level: logLevel, message: logMessage };
		if (formAction === 'bash_script')
			return { command: bashCommand };
		return {};
	}

	// ── Save ──────────────────────────────────────────────────────────────────

	async function save() {
		if (!formName.trim()) return;
		saving = true;
		const body = {
			name:           formName.trim(),
			description:    formDesc,
			enabled:        formEnabled,
			trigger_type:   formTrigger,
			trigger_config: buildTriggerConfig(),
			action_type:    formAction,
			action_config:  buildActionConfig(),
		};
		try {
			let r: Response;
			if (selectedId !== null) {
				r = await fetch(`${BASE}/api/automations/${selectedId}`, {
					method: 'PUT',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(body),
				});
			} else {
				r = await fetch(`${BASE}/api/automations`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(body),
				});
			}
			if (r.ok) {
				const saved: Automation = await r.json();
				selectedId = saved.id;
				dirty = false;
				await fetchAll();
				await fetchLogs(saved.id);
			}
		} catch { /* offline */ }
		saving = false;
	}

	// ── Delete ────────────────────────────────────────────────────────────────

	async function deleteSelected() {
		if (selectedId === null) return;
		if (!confirm('Delete this automation?')) return;
		await fetch(`${BASE}/api/automations/${selectedId}`, { method: 'DELETE' });
		selectedId = null;
		clearForm();
		await fetchAll();
	}

	// ── Run now ───────────────────────────────────────────────────────────────

	async function runNow() {
		if (selectedId === null) return;
		running = true; runResult = null;
		try {
			const r = await fetch(`${BASE}/api/automations/${selectedId}/run`, { method: 'POST' });
			if (r.ok) {
				runResult = await r.json();
				await fetchLogs(selectedId);
				await fetchAll();
			}
		} catch { /* offline */ }
		running = false;
	}

	// ── Toggle enabled from list ───────────────────────────────────────────────

	async function toggleEnabled(a: Automation, e: Event) {
		e.stopPropagation();
		const checked = (e.target as HTMLInputElement).checked;
		await fetch(`${BASE}/api/automations/${a.id}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ enabled: checked }),
		});
		await fetchAll();
	}

	// ── Helpers ───────────────────────────────────────────────────────────────

	function timeAgo(iso: string | null): string {
		if (!iso) return 'never';
		const diff = Date.now() - new Date(iso).getTime();
		const m = Math.floor(diff / 60_000);
		if (m < 1)  return 'just now';
		if (m < 60) return `${m}m ago`;
		const h = Math.floor(m / 60);
		if (h < 24) return `${h}h ago`;
		return `${Math.floor(h / 24)}d ago`;
	}

	function triggerLabel(t: string): string {
		return TRIGGER_OPTS.find((o) => o.value === t)?.label ?? t;
	}
	function actionLabel(t: string): string {
		return ACTION_OPTS.find((o) => o.value === t)?.label ?? t;
	}

	// ── Mount ─────────────────────────────────────────────────────────────────

	onMount(() => {
		fetchAll();
		fetchHeartbeat();
	});
</script>

<svelte:head>
	<title>Nexus — Automations</title>
</svelte:head>

<div class="page">

	<!-- ── Left list panel ───────────────────────────────────────────────────── -->
	<div class="list-panel">

		<div class="list-header">
			<span class="list-title"><Zap size={14} strokeWidth={2} /> Automations</span>
			<button class="new-btn" on:click={newAutomation}>
				<Plus size={13} strokeWidth={2} /> New
			</button>
		</div>

		<!-- Templates -->
		<div class="template-section">
			<div class="template-label">Templates</div>
			{#each TEMPLATES as tpl}
				<button class="template-btn" on:click={() => applyTemplate(tpl)}>
					<span class="tpl-icon">{tpl.icon}</span>
					<span class="tpl-label">{tpl.label}</span>
				</button>
			{/each}
		</div>

		<div class="list-divider"></div>

		<!-- Automation list -->
		<div class="auto-list">
			{#each automations as a (a.id)}
				<button
					class="auto-item"
					class:selected={selectedId === a.id}
					on:click={() => selectAutomation(a)}
				>
					<div class="auto-item-top">
						<span class="auto-name">{a.name}</span>
						<!-- svelte-ignore a11y-click-events-have-key-events -->
						<input
							type="checkbox"
							class="enabled-check"
							checked={a.enabled}
							on:change={(e) => toggleEnabled(a, e)}
							title={a.enabled ? 'Enabled' : 'Disabled'}
						/>
					</div>
					<div class="auto-item-badges">
						<span class="badge badge-trigger">{triggerLabel(a.trigger_type)}</span>
						<span class="badge badge-action">{actionLabel(a.action_type)}</span>
					</div>
					<div class="auto-item-meta">
						<span>{timeAgo(a.last_run)}</span>
						<span>{a.run_count} runs</span>
					</div>
				</button>
			{:else}
				<div class="list-empty">No automations yet.<br/>Use a template or click New.</div>
			{/each}
		</div>
	</div>

	<!-- ── Right editor panel ─────────────────────────────────────────────────── -->
	<div class="editor-panel">

		{#if selectedId === null && !dirty}
			<div class="empty-state">
				<Zap size={36} strokeWidth={1} />
				<div class="empty-title">Automations</div>
				<div class="empty-hint">Select an automation or create a new one</div>
			</div>

		{:else}
			<!-- ── Form ────────────────────────────────────────────── -->
			<div class="form-scroll">
				<div class="form-section">
					<div class="field-row">
						<div class="field flex-2">
							<label class="field-label" for="f-name">Name</label>
							<input
								id="f-name"
								class="field-input"
								type="text"
								placeholder="Automation name"
								bind:value={formName}
								on:input={() => (dirty = true)}
							/>
						</div>
						<div class="field field-toggle">
							<label class="field-label" for="f-enabled">Enabled</label>
							<label class="toggle">
								<input id="f-enabled" type="checkbox" bind:checked={formEnabled} on:change={() => (dirty = true)} />
								<span class="toggle-track"></span>
							</label>
						</div>
					</div>
					<div class="field">
						<label class="field-label" for="f-desc">Description</label>
						<input
							id="f-desc"
							class="field-input"
							type="text"
							placeholder="Optional description"
							bind:value={formDesc}
							on:input={() => (dirty = true)}
						/>
					</div>
				</div>

				<!-- ── TRIGGER ──────────────────────────────────── -->
				<div class="form-section">
					<div class="section-heading">
						<span class="section-bar" style="background: var(--accent2)"></span>
						<span class="section-title">Trigger</span>
					</div>

					<div class="field">
						<label class="field-label" for="f-trigger">Type</label>
						<select id="f-trigger" class="field-select" bind:value={formTrigger} on:change={() => (dirty = true)}>
							{#each TRIGGER_OPTS as o}
								<option value={o.value}>{o.label}</option>
							{/each}
						</select>
					</div>

					{#if formTrigger === 'schedule'}
						<div class="field-row">
							<div class="field flex-2">
								<label class="field-label" for="f-interval">Interval</label>
								<select id="f-interval" class="field-select" bind:value={schedInterval} on:change={() => (dirty = true)}>
									{#each INTERVALS as iv}
										<option value={iv.value}>{iv.label}</option>
									{/each}
								</select>
							</div>
							{#if schedInterval === 'daily'}
								<div class="field">
									<label class="field-label" for="f-time">Time (24h)</label>
									<input id="f-time" class="field-input" type="time" bind:value={schedTime} on:input={() => (dirty = true)} />
								</div>
							{/if}
						</div>

					{:else if formTrigger === 'wazuh_alert'}
						<div class="field">
							<label class="field-label" for="f-sev">Minimum Severity</label>
							<select id="f-sev" class="field-select" bind:value={wazuhSeverity} on:change={() => (dirty = true)}>
								{#each SEV_OPTS as s}
									<option value={s}>{s}</option>
								{/each}
							</select>
						</div>

					{:else if formTrigger === 'service_down' || formTrigger === 'service_up'}
						<div class="field">
							<label class="field-label" for="f-svcname">Service</label>
							{#if hbServices.length}
								<select id="f-svcname" class="field-select" bind:value={svcName} on:change={() => (dirty = true)}>
									<option value="">— select service —</option>
									{#each hbServices as s}<option value={s}>{s}</option>{/each}
								</select>
							{:else}
								<input id="f-svcname" class="field-input" type="text" placeholder="service name" bind:value={svcName} on:input={() => (dirty = true)} />
							{/if}
						</div>

					{:else if formTrigger === 'docker_restart'}
						<div class="field-row">
							<div class="field flex-2">
								<label class="field-label" for="f-dkr-name">Container</label>
								{#if dockerContainers.length}
									<select id="f-dkr-name" class="field-select" bind:value={dockerContainer} on:change={() => (dirty = true)}>
										<option value="">— select container —</option>
										{#each dockerContainers as c}<option value={c}>{c}</option>{/each}
									</select>
								{:else}
									<input id="f-dkr-name" class="field-input" type="text" placeholder="container name" bind:value={dockerContainer} on:input={() => (dirty = true)} />
								{/if}
							</div>
							<div class="field">
								<label class="field-label" for="f-dkr-thresh">Restart threshold</label>
								<input id="f-dkr-thresh" class="field-input field-num" type="number" min="1" max="20" bind:value={dockerThreshold} on:input={() => (dirty = true)} />
							</div>
						</div>
					{/if}
				</div>

				<!-- ── ACTION ────────────────────────────────────── -->
				<div class="form-section">
					<div class="section-heading">
						<span class="section-bar" style="background: var(--accent4)"></span>
						<span class="section-title">Action</span>
					</div>

					<div class="field">
						<label class="field-label" for="f-action">Type</label>
						<select id="f-action" class="field-select" bind:value={formAction} on:change={() => (dirty = true)}>
							{#each ACTION_OPTS as o}
								<option value={o.value}>{o.label}</option>
							{/each}
						</select>
					</div>

					{#if formAction === 'ntfy_notify'}
						<div class="field">
							<label class="field-label" for="f-ntfy-title">Title</label>
							<input id="f-ntfy-title" class="field-input" type="text" placeholder="Notification title" bind:value={ntfyTitle} on:input={() => (dirty = true)} />
						</div>
						<div class="field">
							<label class="field-label" for="f-ntfy-msg">Message</label>
							<textarea id="f-ntfy-msg" class="field-textarea" rows="2" placeholder="Notification body" bind:value={ntfyMessage} on:input={() => (dirty = true)}></textarea>
						</div>
						<div class="field">
							<label class="field-label" for="f-ntfy-pri">Priority: {ntfyPriority}</label>
							<input id="f-ntfy-pri" class="field-range" type="range" min="1" max="5" bind:value={ntfyPriority} on:input={() => (dirty = true)} />
							<div class="range-labels"><span>min</span><span>default</span><span>urgent</span></div>
						</div>

					{:else if formAction === 'docker_restart'}
						<div class="field">
							<label class="field-label" for="f-rst-ctr">Container</label>
							{#if dockerContainers.length}
								<select id="f-rst-ctr" class="field-select" bind:value={restartContainer} on:change={() => (dirty = true)}>
									<option value="">— select container —</option>
									{#each dockerContainers as c}<option value={c}>{c}</option>{/each}
								</select>
							{:else}
								<input id="f-rst-ctr" class="field-input" type="text" placeholder="container name" bind:value={restartContainer} on:input={() => (dirty = true)} />
							{/if}
						</div>

					{:else if formAction === 'webhook'}
						<div class="field-row">
							<div class="field flex-2">
								<label class="field-label" for="f-wh-url">URL</label>
								<input id="f-wh-url" class="field-input" type="url" placeholder="https://..." bind:value={webhookUrl} on:input={() => (dirty = true)} />
							</div>
							<div class="field">
								<label class="field-label" for="f-wh-method">Method</label>
								<select id="f-wh-method" class="field-select" bind:value={webhookMethod} on:change={() => (dirty = true)}>
									{#each ['POST', 'GET', 'PUT', 'PATCH'] as m}<option>{m}</option>{/each}
								</select>
							</div>
						</div>
						<div class="field">
							<label class="field-label" for="f-wh-headers">Headers (JSON)</label>
							<textarea id="f-wh-headers" class="field-textarea field-mono" rows="2" placeholder="Content-Type: application/json" bind:value={webhookHeaders} on:input={() => (dirty = true)}></textarea>
						</div>
						<div class="field">
							<label class="field-label" for="f-wh-body">Body</label>
							<textarea id="f-wh-body" class="field-textarea field-mono" rows="3" placeholder="Request body…" bind:value={webhookBody} on:input={() => (dirty = true)}></textarea>
						</div>

					{:else if formAction === 'log_entry'}
						<div class="field-row">
							<div class="field">
								<label class="field-label" for="f-log-level">Level</label>
								<select id="f-log-level" class="field-select" bind:value={logLevel} on:change={() => (dirty = true)}>
									{#each LOG_LEVELS as l}<option>{l}</option>{/each}
								</select>
							</div>
							<div class="field flex-2">
								<label class="field-label" for="f-log-msg">Message</label>
								<input id="f-log-msg" class="field-input" type="text" placeholder="Log message" bind:value={logMessage} on:input={() => (dirty = true)} />
							</div>
						</div>

					{:else if formAction === 'bash_script'}
						<div class="field">
							<label class="field-label" for="f-bash">Command</label>
							<textarea id="f-bash" class="field-textarea field-mono" rows="3" placeholder="echo hello" bind:value={bashCommand} on:input={() => (dirty = true)}></textarea>
						</div>
						<div class="bash-warn">⚠ Requires <code>ALLOW_BASH_AUTOMATION=true</code> in backend environment</div>
					{/if}
				</div>

				<!-- ── Buttons ───────────────────────────────────── -->
				<div class="action-bar">
					<button
						class="btn btn-primary"
						disabled={saving || !formName.trim()}
						on:click={save}
					>
						{saving ? 'Saving…' : 'Save'}
					</button>

					{#if selectedId !== null}
						<button
							class="btn btn-run"
							disabled={running}
							on:click={runNow}
						>
							<Play size={12} strokeWidth={2} />
							{running ? 'Running…' : 'Run now'}
						</button>

						<button class="btn btn-delete" on:click={deleteSelected}>
							<Trash2 size={12} strokeWidth={2} /> Delete
						</button>
					{/if}
				</div>

				{#if runResult !== null}
					<div class="run-result" class:run-ok={runResult.success} class:run-fail={!runResult.success}>
						{#if runResult.success}
							<CheckCircle size={13} strokeWidth={2} />
						{:else}
							<XCircle size={13} strokeWidth={2} />
						{/if}
						{runResult.result}
					</div>
				{/if}

				<!-- ── Run log ─────────────────────────────────── -->
				{#if runLogs.length > 0}
					<div class="form-section">
						<div class="section-heading">
							<span class="section-bar" style="background: var(--text2)"></span>
							<span class="section-title">Run Log</span>
						</div>
						<div class="run-log">
							{#each runLogs as log}
								<div class="log-row" class:log-ok={log.success} class:log-fail={!log.success}>
									<span class="log-dot"></span>
									<span class="log-ts">{new Date(log.ran_at).toLocaleTimeString()} {new Date(log.ran_at).toLocaleDateString()}</span>
									<span class="log-result">{log.result}</span>
								</div>
							{/each}
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</div>
</div>

<style>
	.page {
		display: flex;
		height: calc(100vh - 52px);
		margin: -1.5rem;
		width: calc(100% + 3rem);
		overflow: hidden;
	}

	/* ── List panel ───────────────────────────────────────────── */
	.list-panel {
		width: 300px;
		flex-shrink: 0;
		border-right: 1px solid var(--border);
		background: var(--bg1);
		display: flex;
		flex-direction: column;
		overflow: hidden;
	}

	.list-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.list-title {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		font-family: var(--font-mono);
		font-size: 0.78rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text1);
	}

	.new-btn {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		padding: 0.2rem 0.6rem;
		background: none;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}
	.new-btn:hover { color: var(--accent); border-color: var(--accent); }

	/* ── Templates ────────────────────────────────────────────── */
	.template-section {
		padding: 0.5rem 0.75rem;
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.template-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text2);
		margin-bottom: 0.35rem;
	}

	.template-btn {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		width: 100%;
		padding: 0.28rem 0.4rem;
		background: none;
		border: none;
		border-radius: var(--radius);
		cursor: pointer;
		text-align: left;
		transition: background 0.1s;
	}
	.template-btn:hover { background: var(--bg2); }

	.tpl-icon { font-size: 0.85rem; flex-shrink: 0; }

	.tpl-label {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--text1);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.list-divider {
		height: 1px;
		background: var(--border);
		flex-shrink: 0;
	}

	/* ── Auto list ────────────────────────────────────────────── */
	.auto-list {
		flex: 1;
		overflow-y: auto;
		padding: 0.35rem 0;
		scrollbar-width: thin;
		scrollbar-color: var(--border) transparent;
	}

	.auto-item {
		display: flex;
		flex-direction: column;
		gap: 0.28rem;
		width: 100%;
		padding: 0.6rem 1rem;
		background: none;
		border: none;
		border-left: 2px solid transparent;
		cursor: pointer;
		text-align: left;
		transition: background 0.1s, border-color 0.1s;
	}
	.auto-item:hover { background: var(--bg2); }
	.auto-item.selected {
		background: color-mix(in srgb, var(--yellow) 8%, var(--bg1));
		border-left-color: var(--yellow);
	}

	.auto-item-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.auto-name {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		font-weight: 600;
		color: var(--text0);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.enabled-check {
		accent-color: var(--accent);
		flex-shrink: 0;
		cursor: pointer;
	}

	.auto-item-badges {
		display: flex;
		gap: 0.3rem;
		flex-wrap: wrap;
	}

	.badge {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		font-weight: 600;
		letter-spacing: 0.05em;
		padding: 0.05rem 0.35rem;
		border-radius: 3px;
		border: 1px solid;
	}

	.badge-trigger {
		color: var(--accent2);
		border-color: color-mix(in srgb, var(--accent2) 35%, var(--border));
		background: color-mix(in srgb, var(--accent2) 8%, transparent);
	}

	.badge-action {
		color: var(--accent4);
		border-color: color-mix(in srgb, var(--accent4) 35%, var(--border));
		background: color-mix(in srgb, var(--accent4) 8%, transparent);
	}

	.auto-item-meta {
		display: flex;
		gap: 0.75rem;
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
	}

	.list-empty {
		padding: 1.5rem 1rem;
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text2);
		text-align: center;
		line-height: 1.6;
	}

	/* ── Editor panel ─────────────────────────────────────────── */
	.editor-panel {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		background: var(--bg0);
		overflow: hidden;
	}

	.empty-state {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 0.75rem;
		color: var(--text2);
	}

	.empty-title {
		font-family: var(--font-mono);
		font-size: 1rem;
		font-weight: 700;
		color: var(--text1);
	}

	.empty-hint {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text2);
	}

	.form-scroll {
		flex: 1;
		overflow-y: auto;
		padding: 1.25rem 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 0;
		scrollbar-width: thin;
		scrollbar-color: var(--border) transparent;
	}

	/* ── Form sections ────────────────────────────────────────── */
	.form-section {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 1rem 1.25rem;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		margin-bottom: 0.85rem;
	}

	.section-heading {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		margin-bottom: 0.1rem;
	}

	.section-bar {
		width: 3px;
		height: 1rem;
		border-radius: 2px;
		flex-shrink: 0;
	}

	.section-title {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text1);
	}

	/* ── Fields ───────────────────────────────────────────────── */
	.field {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
		min-width: 0;
	}

	.field-row {
		display: flex;
		gap: 0.75rem;
		align-items: flex-end;
	}

	.flex-2 { flex: 2; min-width: 0; }

	.field-toggle {
		flex-shrink: 0;
		align-items: flex-start;
	}

	.field-label {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 600;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--text2);
	}

	.field-input,
	.field-select,
	.field-textarea {
		background: var(--bg0);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.78rem;
		padding: 0.35rem 0.6rem;
		outline: none;
		width: 100%;
		transition: border-color 0.12s;
	}

	.field-input:focus,
	.field-select:focus,
	.field-textarea:focus {
		border-color: var(--accent);
	}

	.field-textarea { resize: vertical; line-height: 1.5; }
	.field-mono { font-size: 0.72rem; }
	.field-num { width: 80px; }

	.field-range {
		width: 100%;
		accent-color: var(--accent4);
	}

	.range-labels {
		display: flex;
		justify-content: space-between;
		font-family: var(--font-mono);
		font-size: 0.58rem;
		color: var(--text2);
		margin-top: -0.15rem;
	}

	/* ── Toggle switch ────────────────────────────────────────── */
	.toggle {
		position: relative;
		display: inline-block;
		width: 36px;
		height: 20px;
		cursor: pointer;
	}

	.toggle input { opacity: 0; width: 0; height: 0; }

	.toggle-track {
		position: absolute;
		inset: 0;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 20px;
		transition: background 0.15s, border-color 0.15s;
	}

	.toggle-track::after {
		content: '';
		position: absolute;
		top: 2px;
		left: 2px;
		width: 14px;
		height: 14px;
		border-radius: 50%;
		background: var(--text2);
		transition: transform 0.15s, background 0.15s;
	}

	.toggle input:checked + .toggle-track {
		background: color-mix(in srgb, var(--accent) 25%, var(--bg2));
		border-color: var(--accent);
	}

	.toggle input:checked + .toggle-track::after {
		transform: translateX(16px);
		background: var(--accent);
	}

	/* ── Bash warning ─────────────────────────────────────────── */
	.bash-warn {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--yellow);
		background: color-mix(in srgb, var(--yellow) 8%, var(--bg0));
		border: 1px solid color-mix(in srgb, var(--yellow) 25%, var(--border));
		border-radius: var(--radius);
		padding: 0.4rem 0.65rem;
	}
	.bash-warn code { color: var(--yellow); font-size: 0.85em; }

	/* ── Action bar ───────────────────────────────────────────── */
	.action-bar {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		margin-bottom: 0.75rem;
	}

	.btn {
		display: flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.38rem 0.9rem;
		border-radius: var(--radius);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		font-weight: 600;
		cursor: pointer;
		border: 1px solid;
		transition: color 0.1s, background 0.1s, border-color 0.1s;
	}

	.btn:disabled { opacity: 0.5; cursor: not-allowed; }

	.btn-primary {
		background: var(--accent);
		border-color: var(--accent);
		color: var(--bg0);
	}
	.btn-primary:not(:disabled):hover { opacity: 0.85; }

	.btn-run {
		background: none;
		border-color: var(--accent2);
		color: var(--accent2);
	}
	.btn-run:not(:disabled):hover {
		background: color-mix(in srgb, var(--accent2) 10%, transparent);
	}

	.btn-delete {
		background: none;
		border-color: var(--red);
		color: var(--red);
		margin-left: auto;
	}
	.btn-delete:hover { background: color-mix(in srgb, var(--red) 10%, transparent); }

	/* ── Run result ───────────────────────────────────────────── */
	.run-result {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		padding: 0.45rem 0.75rem;
		border-radius: var(--radius);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		border: 1px solid;
		margin-bottom: 0.75rem;
	}

	.run-ok   { color: var(--green); border-color: color-mix(in srgb, var(--green) 30%, var(--border)); background: color-mix(in srgb, var(--green) 8%, transparent); }
	.run-fail { color: var(--red);   border-color: color-mix(in srgb, var(--red)   30%, var(--border)); background: color-mix(in srgb, var(--red)   8%, transparent); }

	/* ── Run log ──────────────────────────────────────────────── */
	.run-log {
		display: flex;
		flex-direction: column;
		gap: 0;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
	}

	.log-row {
		display: grid;
		grid-template-columns: 8px auto 1fr;
		align-items: center;
		gap: 0.6rem;
		padding: 0.28rem 0.75rem;
		border-bottom: 1px solid color-mix(in srgb, var(--border) 50%, transparent);
		font-family: var(--font-mono);
		font-size: 0.68rem;
	}
	.log-row:last-child { border-bottom: none; }

	.log-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.log-ok   .log-dot { background: var(--green); }
	.log-fail .log-dot { background: var(--red); }

	.log-ts     { color: var(--text2); white-space: nowrap; font-size: 0.62rem; }
	.log-result { color: var(--text1); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

	/* ── Mobile ───────────────────────────────────────────────── */
	@media (max-width: 700px) {
		.page { flex-direction: column; height: auto; }
		.list-panel { width: 100%; border-right: none; border-bottom: 1px solid var(--border); max-height: 320px; }
	}
</style>
