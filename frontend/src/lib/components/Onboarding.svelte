<script lang="ts">
	import { onMount } from 'svelte';
	import { fade, scale } from 'svelte/transition';
	import { CheckCircle2 } from '@lucide/svelte';
	import { nexusSettings } from '$lib/stores';
	import { dashConfig, WIDGET_DEFS } from '$lib/stores/dashConfig';
	import { BASE } from '$lib/api';

	// ── Constants ─────────────────────────────────────────────────
	const ONBOARDING_KEY = 'nexus_onboarding_complete';
	const TOTAL_STEPS = 7;

	const STEP_META = [
		{ title: 'Welcome to Nexus',   sub: "Let's get your homelab dashboard set up. This takes about 2 minutes." },
		{ title: 'AI Assistant',        sub: 'Nexus uses Ollama to run AI locally. Nothing leaves your server.' },
		{ title: 'Weather Location',    sub: 'Powers the weather widget. Your location stays on your server.' },
		{ title: 'Integrations',        sub: 'Connect your services. All optional — configure what you have.' },
		{ title: 'Notifications',       sub: 'Choose which events trigger alerts.' },
		{ title: 'Dashboard Layout',    sub: 'Choose which widgets appear on your dashboard.' },
		{ title: "You're all set",      sub: 'Your data lives in ./data/ on your server. Everything is local — no cloud, no accounts.' },
	] as const;

	// ── Core state ────────────────────────────────────────────────
	let show = false;
	let step = 1;

	// ── Step 2: AI ────────────────────────────────────────────────
	let ollamaHost:   string = 'http://ollama:11434';
	let ollamaModel:  string = '';
	let ollamaStatus: 'unknown' | 'online' | 'offline' = 'unknown';
	let models:       string[] = [];
	let modelsLoading = false;

	// ── Step 3: Weather ───────────────────────────────────────────
	let city = '';
	let lat  = '';
	let lon  = '';

	// ── Step 4: Integrations ──────────────────────────────────────
	let haOn = false;       let haUrl = '';                       let haToken  = '';
	let wazuhOn = false;    let wazuhHost = '';                   let wazuhUser = 'wazuh-wui'; let wazuhPass = '';
	let mqttOn = false;     let mqttHost  = '';                   let mqttPort  = 1883;        let mqttUser = '';  let mqttPass = '';
	let obsidianOn = false; let obsidianPath = '';
	let ntfyOn = false;     let ntfyServer = 'https://ntfy.sh';  let ntfyTopic = '';
	let thmOn = false;      let thmUsername = '';

	// ── Step 5: Notifications ─────────────────────────────────────
	let notifEnabled   = true;
	let notifCritSec   = true;
	let notifContainer = true;
	let notifHeartbeat = true;
	let notifAutoFail  = true;
	let notifVuln      = true;
	let notifDigest    = true;

	// ── Step 6: Layout ────────────────────────────────────────────
	let widgetVisible: Record<string, boolean> = Object.fromEntries(
		WIDGET_DEFS.map((d) => [d.id, true]),
	);
	let gridColumns: 2 | 3 | 4 = 3;

	// ── API helpers ───────────────────────────────────────────────
	function authHeader(): Record<string, string> {
		if (typeof localStorage === 'undefined') return {};
		const key = localStorage.getItem('nexus_api_key');
		return key ? { Authorization: `Bearer ${key}` } : {};
	}

	async function testOllama() {
		ollamaStatus = 'unknown';
		try {
			const res = await fetch(`${BASE}/api/ai/health`, { headers: authHeader() });
			const data = await res.json();
			ollamaStatus = data?.status === 'online' ? 'online' : 'offline';
			if (ollamaStatus === 'online' && models.length === 0) await loadModels();
		} catch {
			ollamaStatus = 'offline';
		}
	}

	async function loadModels() {
		modelsLoading = true;
		try {
			const res  = await fetch(`${BASE}/api/ai/models`, { headers: authHeader() });
			const data = await res.json();
			if (data?.models?.length) {
				models = (data.models as { name: string }[]).map((m) => m.name);
				const preferred = models.find(
					(m) => m.toLowerCase().includes('llama') || m.toLowerCase().includes('mistral'),
				);
				ollamaModel = preferred ?? models[0];
			}
		} catch { /* ignore */ }
		modelsLoading = false;
	}

	// ── Navigation ────────────────────────────────────────────────
	function quickStart() { step = 7; }
	function startFull()  { step = 2; }
	function skipSetup()  { step = 7; }
	function back()       { if (step > 1) step -= 1; }
	function next()       { if (step < TOTAL_STEPS) step += 1; }

	// ── Commit & close ────────────────────────────────────────────
	function commitAndClose() {
		nexusSettings.patch({
			location: { city: city.trim(), lat: lat.trim(), lon: lon.trim() },
			ai:       { ollamaHost: ollamaHost.trim(), defaultModel: ollamaModel },
			ntfy:     { server: ntfyServer.trim(), topic: ntfyTopic.trim() },
		});

		for (const [id, visible] of Object.entries(widgetVisible)) {
			dashConfig.updateWidget(id, { enabled: visible });
		}
		dashConfig.setColumns(gridColumns);

		localStorage.setItem(ONBOARDING_KEY, '1');
		show = false;
	}

	onMount(() => {
		show = !localStorage.getItem(ONBOARDING_KEY);
	});
</script>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
	<div class="backdrop" transition:fade={{ duration: 180 }}>
		<div
			class="card"
			role="dialog"
			aria-modal="true"
			aria-label="Nexus setup wizard"
			in:scale={{ duration: 220, start: 0.96 }}
		>
			<!-- Skip button (steps 2–6) -->
			{#if step >= 2 && step <= 6}
				<button class="skip-btn" on:click={skipSetup}>Skip setup →</button>
			{/if}

			<!-- ── Header ────────────────────────────────────────── -->
			<div class="wiz-header">
				<div class="step-counter">Step {step} / {TOTAL_STEPS}</div>

				{#if step === 1}
					<div class="logo-box" aria-hidden="true">N</div>
				{:else if step === 7}
					<div class="check-wrap" aria-hidden="true">
						<CheckCircle2 size={42} strokeWidth={1.5} color="#3fb950" />
					</div>
				{/if}

				<h2 class="wiz-heading">{STEP_META[step - 1].title}</h2>
				<p class="wiz-sub">{STEP_META[step - 1].sub}</p>
			</div>

			<!-- ── Body ──────────────────────────────────────────── -->
			<div class="wiz-body">

				<!-- ─ Step 1: Welcome ─────────────────────────────── -->
				{#if step === 1}
					<div class="btn-stack">
						<button class="btn-primary btn-full" on:click={startFull}>
							Full Setup →
						</button>
						<button class="btn-secondary btn-full" on:click={quickStart}>
							Quick Start (use defaults)
						</button>
					</div>

				<!-- ─ Step 2: AI ──────────────────────────────────── -->
				{:else if step === 2}
					<div class="field-group">
						<div class="field-label">Ollama host</div>
						<div class="input-row">
							<input
								class="wiz-inp"
								type="text"
								value={ollamaHost}
								on:input={(e) => { ollamaHost = (e.currentTarget as HTMLInputElement).value; }}
								on:blur={testOllama}
								placeholder="http://ollama:11434"
							/>
							{#if ollamaStatus !== 'unknown'}
								<span
									class="ollama-badge"
									style="color:{ollamaStatus === 'online' ? '#3fb950' : '#f85149'}"
								>
									{ollamaStatus === 'online' ? '● Connected' : '✕ Unreachable'}
								</span>
							{/if}
						</div>
					</div>

					<div class="field-group" style="margin-top:14px">
						<div class="field-label">Default model</div>
						{#if models.length > 0}
							<select class="wiz-inp" bind:value={ollamaModel}>
								{#each models as m}
									<option value={m}>{m}</option>
								{/each}
							</select>
						{:else}
							<input
								class="wiz-inp"
								type="text"
								bind:value={ollamaModel}
								placeholder={modelsLoading ? 'Loading models…' : 'e.g. llama3:8b'}
							/>
						{/if}
					</div>

					<p class="field-note" style="margin-top:18px">
						Also run: <code class="ic">ollama pull nomic-embed-text</code> — enables AI knowledge base features
					</p>

					<button class="skip-link" on:click={next} style="margin-top:16px">Skip AI →</button>

				<!-- ─ Step 3: Weather ────────────────────────────── -->
				{:else if step === 3}
					<div class="field-group">
						<div class="field-label">City name</div>
						<input class="wiz-inp" type="text" bind:value={city} placeholder="e.g. Cape Town" />
					</div>
					<div class="field-row" style="margin-top:12px">
						<div class="field-group">
							<div class="field-label">Latitude</div>
							<input class="wiz-inp" type="number" step="0.0001" bind:value={lat} placeholder="-33.9249" />
						</div>
						<div class="field-group">
							<div class="field-label">Longitude</div>
							<input class="wiz-inp" type="number" step="0.0001" bind:value={lon} placeholder="18.4241" />
						</div>
					</div>
					<p class="field-note" style="margin-top:14px">
						Find your coordinates at
						<a href="https://latlong.net" target="_blank" rel="noopener" class="ext-link">latlong.net</a>
					</p>

				<!-- ─ Step 4: Integrations ───────────────────────── -->
				{:else if step === 4}

					<!-- Home Assistant -->
					<div class="intg-block">
						<div class="intg-row">
							<button
								class="toggle" class:on={haOn}
								on:click={() => { haOn = !haOn; }}
								aria-label="Toggle Home Assistant"
							><span class="toggle-knob"></span></button>
							<div class="intg-icon" style="color:#ff7043">HA</div>
							<div class="intg-info">
								<span class="intg-name">Home Assistant</span>
								<span class="intg-desc">Control and monitor your smart home.</span>
							</div>
						</div>
						{#if haOn}
							<div class="intg-fields">
								<div class="field-label-sm">URL</div>
								<input class="wiz-inp" type="text" bind:value={haUrl} placeholder="http://homeassistant.local:8123" />
								<div class="field-label-sm" style="margin-top:8px">Access Token</div>
								<input class="wiz-inp" type="password" bind:value={haToken} placeholder="Long-lived access token" />
							</div>
						{/if}
					</div>

					<!-- Wazuh -->
					<div class="intg-block">
						<div class="intg-row">
							<button
								class="toggle" class:on={wazuhOn}
								on:click={() => { wazuhOn = !wazuhOn; }}
								aria-label="Toggle Wazuh"
							><span class="toggle-knob"></span></button>
							<div class="intg-icon" style="color:#f85149">WZ</div>
							<div class="intg-info">
								<span class="intg-name">Wazuh Security</span>
								<span class="intg-desc">Security event monitoring and alerting.</span>
							</div>
						</div>
						{#if wazuhOn}
							<div class="intg-fields">
								<div class="field-label-sm">Host</div>
								<input class="wiz-inp" type="text" bind:value={wazuhHost} placeholder="https://wazuh.local:55000" />
								<div class="field-row" style="margin-top:8px; gap:8px">
									<div class="field-group">
										<div class="field-label-sm">Username</div>
										<input class="wiz-inp" type="text" bind:value={wazuhUser} />
									</div>
									<div class="field-group">
										<div class="field-label-sm">Password</div>
										<input class="wiz-inp" type="password" bind:value={wazuhPass} />
									</div>
								</div>
							</div>
						{/if}
					</div>

					<!-- MQTT -->
					<div class="intg-block">
						<div class="intg-row">
							<button
								class="toggle" class:on={mqttOn}
								on:click={() => { mqttOn = !mqttOn; }}
								aria-label="Toggle MQTT"
							><span class="toggle-knob"></span></button>
							<div class="intg-icon" style="color:#3fb950">MQ</div>
							<div class="intg-info">
								<span class="intg-name">MQTT</span>
								<span class="intg-desc">For automations and device events.</span>
							</div>
						</div>
						{#if mqttOn}
							<div class="intg-fields">
								<div class="field-row">
									<div class="field-group" style="flex:2">
										<div class="field-label-sm">Broker host</div>
										<input class="wiz-inp" type="text" bind:value={mqttHost} placeholder="mqtt.local" />
									</div>
									<div class="field-group" style="flex:1">
										<div class="field-label-sm">Port</div>
										<input class="wiz-inp" type="number" bind:value={mqttPort} />
									</div>
								</div>
								<div class="field-row" style="margin-top:8px">
									<div class="field-group">
										<div class="field-label-sm">Username</div>
										<input class="wiz-inp" type="text" bind:value={mqttUser} />
									</div>
									<div class="field-group">
										<div class="field-label-sm">Password</div>
										<input class="wiz-inp" type="password" bind:value={mqttPass} />
									</div>
								</div>
							</div>
						{/if}
					</div>

					<!-- Obsidian -->
					<div class="intg-block">
						<div class="intg-row">
							<button
								class="toggle" class:on={obsidianOn}
								on:click={() => { obsidianOn = !obsidianOn; }}
								aria-label="Toggle Obsidian"
							><span class="toggle-knob"></span></button>
							<div class="intg-icon" style="color:#bc8cff">OB</div>
							<div class="intg-info">
								<span class="intg-name">Obsidian Vault</span>
								<span class="intg-desc">Index your notes for the AI knowledge base.</span>
							</div>
						</div>
						{#if obsidianOn}
							<div class="intg-fields">
								<div class="field-label-sm">Vault path inside container</div>
								<input class="wiz-inp" type="text" bind:value={obsidianPath} placeholder="/data/vault" />
							</div>
						{/if}
					</div>

					<!-- ntfy -->
					<div class="intg-block">
						<div class="intg-row">
							<button
								class="toggle" class:on={ntfyOn}
								on:click={() => { ntfyOn = !ntfyOn; }}
								aria-label="Toggle ntfy"
							><span class="toggle-knob"></span></button>
							<div class="intg-icon" style="color:#58a6ff">NT</div>
							<div class="intg-info">
								<span class="intg-name">ntfy Notifications</span>
								<span class="intg-desc">Push alerts to your phone.</span>
							</div>
						</div>
						{#if ntfyOn}
							<div class="intg-fields">
								<div class="field-label-sm">Server</div>
								<input class="wiz-inp" type="text" bind:value={ntfyServer} />
								<div class="field-label-sm" style="margin-top:8px">Topic</div>
								<input class="wiz-inp" type="text" bind:value={ntfyTopic} placeholder="nexus-alerts" />
							</div>
						{/if}
					</div>

					<!-- TryHackMe -->
					<div class="intg-block">
						<div class="intg-row">
							<button
								class="toggle" class:on={thmOn}
								on:click={() => { thmOn = !thmOn; }}
								aria-label="Toggle TryHackMe"
							><span class="toggle-knob"></span></button>
							<div class="intg-icon" style="color:#e3b341">TH</div>
							<div class="intg-info">
								<span class="intg-name">TryHackMe</span>
								<span class="intg-desc">Track learning progress.</span>
							</div>
						</div>
						{#if thmOn}
							<div class="intg-fields">
								<div class="field-label-sm">Username</div>
								<input class="wiz-inp" type="text" bind:value={thmUsername} placeholder="your-thm-username" />
							</div>
						{/if}
					</div>

					<p class="field-note" style="margin-top:18px">
						Settings saved to <code class="ic">.nexus/config.yml</code> on your server.
						Change anytime in Settings → Integrations.
					</p>

				<!-- ─ Step 5: Notifications ──────────────────────── -->
				{:else if step === 5}

					<!-- Master toggle -->
					<div class="notif-master">
						<button
							class="toggle" class:on={notifEnabled}
							on:click={() => { notifEnabled = !notifEnabled; }}
							aria-label="Toggle all notifications"
						><span class="toggle-knob"></span></button>
						<span class="notif-master-label">Enable notifications</span>
					</div>

					<div class="notif-rows" class:notif-disabled={!notifEnabled}>
						{#each [
							{ key: 'critSec',    label: 'Critical security alerts',   desc: 'Wazuh CRIT/HIGH events' },
							{ key: 'container',  label: 'Container goes down',        desc: 'Docker container stops unexpectedly' },
							{ key: 'heartbeat',  label: 'Heartbeat failure',          desc: 'Monitored host becomes unreachable' },
							{ key: 'autoFail',   label: 'Automation run failure',     desc: 'An automation errors' },
							{ key: 'vuln',       label: 'New vulnerability detected', desc: 'Security scanner finds issue' },
							{ key: 'digest',     label: 'Daily digest (08:00)',       desc: 'Morning summary' },
						] as item}
							<div class="notif-row">
								<button
									class="toggle toggle-sm" class:on={
										item.key === 'critSec'   ? notifCritSec   :
										item.key === 'container' ? notifContainer  :
										item.key === 'heartbeat' ? notifHeartbeat  :
										item.key === 'autoFail'  ? notifAutoFail   :
										item.key === 'vuln'      ? notifVuln       :
										                           notifDigest
									}
									on:click={() => {
										if      (item.key === 'critSec')   notifCritSec   = !notifCritSec;
										else if (item.key === 'container') notifContainer = !notifContainer;
										else if (item.key === 'heartbeat') notifHeartbeat = !notifHeartbeat;
										else if (item.key === 'autoFail')  notifAutoFail  = !notifAutoFail;
										else if (item.key === 'vuln')      notifVuln      = !notifVuln;
										else                               notifDigest    = !notifDigest;
									}}
									disabled={!notifEnabled}
									aria-label="Toggle {item.label}"
								><span class="toggle-knob"></span></button>
								<div class="notif-text">
									<span class="notif-label">{item.label}</span>
									<span class="notif-desc">{item.desc}</span>
								</div>
							</div>
						{/each}
					</div>

					{#if ntfyOn && ntfyTopic}
						<p class="field-note ntfy-ok" style="margin-top:18px">
							● Alerts → ntfy / {ntfyTopic}
						</p>
					{:else}
						<p class="field-note" style="margin-top:18px">
							Configure ntfy in the previous step to enable push notifications.
						</p>
					{/if}

				<!-- ─ Step 6: Layout ─────────────────────────────── -->
				{:else if step === 6}

					<div class="section-label">Widgets</div>
					<div class="widget-grid">
						{#each WIDGET_DEFS as def}
							<label class="widget-check-row">
								<input
									type="checkbox"
									checked={widgetVisible[def.id]}
									on:change={(e) => {
										widgetVisible = {
											...widgetVisible,
											[def.id]: (e.currentTarget as HTMLInputElement).checked,
										};
									}}
								/>
								<span class="widget-check-icon">{def.icon}</span>
								<span class="widget-check-label">{def.label}</span>
							</label>
						{/each}
					</div>

					<div class="section-label" style="margin-top:24px">Grid columns</div>
					<div class="col-picker">
						{#each ([2, 3, 4] as const) as n}
							<button
								class="col-btn"
								class:active={gridColumns === n}
								on:click={() => { gridColumns = n; }}
							>{n} columns</button>
						{/each}
					</div>

				<!-- ─ Step 7: Done ───────────────────────────────── -->
				{:else if step === 7}
					<a href="/settings" class="settings-link" on:click={commitAndClose}>
						→ Open Settings to change anything
					</a>
				{/if}

			</div><!-- /wiz-body -->

			<!-- ── Footer ────────────────────────────────────────── -->
			<div class="wiz-footer">
				<div class="dots" aria-label="Step {step} of {TOTAL_STEPS}" role="status">
					{#each Array(TOTAL_STEPS) as _, i}
						<span class="dot" class:active={step === i + 1}></span>
					{/each}
				</div>

				<div class="footer-btns">
					{#if step > 1}
						<button class="btn-back" on:click={back}>← Back</button>
					{/if}
					{#if step === 1}
						<!-- CTAs are in body -->
					{:else if step === TOTAL_STEPS}
						<button class="btn-next" on:click={commitAndClose}>Open Nexus →</button>
					{:else}
						<button class="btn-next" on:click={next}>Next →</button>
					{/if}
				</div>
			</div>

		</div><!-- /card -->
	</div><!-- /backdrop -->
{/if}

<style>
	/* ── Backdrop ─────────────────────────────────────────────── */
	.backdrop {
		position: fixed;
		inset: 0;
		background: rgba(13, 17, 23, 0.92);
		backdrop-filter: blur(3px);
		z-index: 1000;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 1rem;
	}

	/* ── Card ─────────────────────────────────────────────────── */
	.card {
		position: relative;
		width: 540px;
		max-width: 100%;
		max-height: 88vh;
		display: flex;
		flex-direction: column;
		background: #161b22;
		border: 1px solid #30363d;
		border-radius: 8px;
		overflow: hidden;
	}

	/* ── Skip button ──────────────────────────────────────────── */
	.skip-btn {
		position: absolute;
		top: 16px;
		right: 20px;
		background: none;
		border: none;
		color: #484f58;
		font-family: var(--font-mono);
		font-size: 10px;
		cursor: pointer;
		padding: 2px 0;
		z-index: 10;
		transition: color 0.1s;
	}
	.skip-btn:hover { color: #8b949e; }

	/* ── Header ───────────────────────────────────────────────── */
	.wiz-header {
		padding: 28px 32px 20px;
		border-bottom: 1px solid #30363d;
		flex-shrink: 0;
	}

	.step-counter {
		font-family: var(--font-mono);
		font-size: 10px;
		color: #484f58;
		text-align: right;
		margin-bottom: 12px;
	}

	.logo-box {
		width: 52px;
		height: 52px;
		background: #3fb950;
		border-radius: 12px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-mono);
		font-size: 1.5rem;
		font-weight: 800;
		color: #0d1117;
		margin: 0 auto 16px;
	}

	.check-wrap {
		display: flex;
		justify-content: center;
		margin-bottom: 14px;
	}

	.wiz-heading {
		font-family: var(--font-ui);
		font-size: 20px;
		font-weight: 700;
		color: #e6edf3;
		letter-spacing: -0.3px;
		margin: 0 0 6px;
		text-align: center;
	}

	.wiz-sub {
		font-family: var(--font-ui);
		font-size: 13px;
		color: #8b949e;
		margin: 0;
		text-align: center;
		line-height: 1.55;
	}

	/* ── Body (scrollable) ────────────────────────────────────── */
	.wiz-body {
		flex: 1;
		overflow-y: auto;
		scrollbar-width: thin;
		padding: 24px 32px;
		display: flex;
		flex-direction: column;
	}

	/* ── Step 1 CTAs ──────────────────────────────────────────── */
	.btn-stack {
		display: flex;
		flex-direction: column;
		gap: 10px;
		margin-top: 8px;
	}

	.btn-full { width: 100%; }

	.btn-primary {
		background: #3fb950;
		color: #0d1117;
		border: none;
		border-radius: 5px;
		padding: 11px 20px;
		font-family: var(--font-ui);
		font-size: 0.9rem;
		font-weight: 700;
		cursor: pointer;
		transition: opacity 0.1s, transform 0.1s;
		text-align: center;
	}
	.btn-primary:hover  { opacity: 0.88; transform: translateY(-1px); }
	.btn-primary:active { transform: translateY(0); }

	.btn-secondary {
		background: transparent;
		color: #8b949e;
		border: 1px solid #30363d;
		border-radius: 5px;
		padding: 10px 20px;
		font-family: var(--font-ui);
		font-size: 0.88rem;
		font-weight: 500;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
		text-align: center;
	}
	.btn-secondary:hover { color: #e6edf3; border-color: #8b949e; }

	/* ── Inputs ───────────────────────────────────────────────── */
	.wiz-inp {
		width: 100%;
		box-sizing: border-box;
		background: #21262d;
		border: 1px solid #30363d;
		border-radius: 5px;
		padding: 8px 12px;
		font-family: var(--font-mono);
		font-size: 13px;
		color: #e6edf3;
		outline: none;
		transition: border-color 0.12s;
	}
	.wiz-inp:focus { border-color: #3fb950; }
	.wiz-inp::placeholder { color: #484f58; }

	/* ── Field group ──────────────────────────────────────────── */
	.field-group {
		display: flex;
		flex-direction: column;
		gap: 5px;
		flex: 1;
	}

	.field-row {
		display: flex;
		gap: 12px;
	}

	.field-label {
		font-family: var(--font-ui);
		font-size: 13px;
		font-weight: 500;
		color: #e6edf3;
		margin-bottom: 5px;
	}

	.field-label-sm {
		font-family: var(--font-ui);
		font-size: 11px;
		font-weight: 500;
		color: #8b949e;
		margin-bottom: 4px;
	}

	/* ── Ollama badge ─────────────────────────────────────────── */
	.input-row {
		display: flex;
		align-items: center;
		gap: 10px;
	}

	.input-row .wiz-inp { flex: 1; }

	.ollama-badge {
		font-family: var(--font-mono);
		font-size: 10px;
		white-space: nowrap;
		flex-shrink: 0;
	}

	/* ── Field notes & links ──────────────────────────────────── */
	.field-note {
		font-family: var(--font-mono);
		font-size: 11px;
		color: #484f58;
		margin: 0;
		line-height: 1.55;
	}

	.ntfy-ok { color: #3fb950 !important; }

	.ext-link { color: #58a6ff; text-decoration: none; }
	.ext-link:hover { text-decoration: underline; }

	.ic {
		background: #21262d;
		border: 1px solid #30363d;
		border-radius: 3px;
		padding: 1px 4px;
		font-size: 0.9em;
		color: #8b949e;
	}

	.skip-link {
		background: none;
		border: none;
		color: #484f58;
		font-family: var(--font-mono);
		font-size: 10px;
		cursor: pointer;
		padding: 0;
		text-align: left;
		transition: color 0.1s;
		align-self: flex-start;
	}
	.skip-link:hover { color: #8b949e; }

	/* ── Toggle switch ────────────────────────────────────────── */
	.toggle {
		position: relative;
		width: 36px;
		height: 20px;
		flex-shrink: 0;
		border-radius: 10px;
		background: #484f58;
		border: none;
		cursor: pointer;
		padding: 0;
		transition: background 0.15s;
	}

	.toggle.on { background: #3fb950; }
	.toggle:disabled { opacity: 0.4; cursor: not-allowed; }

	.toggle-knob {
		position: absolute;
		top: 2px;
		left: 2px;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		background: white;
		transition: transform 0.15s;
	}

	.toggle.on .toggle-knob { transform: translateX(16px); }

	.toggle-sm {
		width: 30px;
		height: 16px;
	}

	.toggle-sm .toggle-knob {
		width: 12px;
		height: 12px;
	}

	.toggle-sm.on .toggle-knob { transform: translateX(14px); }

	/* ── Integration rows ─────────────────────────────────────── */
	.intg-block {
		border: 1px solid #21262d;
		border-radius: 6px;
		overflow: hidden;
		margin-bottom: 8px;
	}

	.intg-row {
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 12px 14px;
	}

	.intg-icon {
		width: 28px;
		height: 28px;
		background: #21262d;
		border-radius: 6px;
		display: flex;
		align-items: center;
		justify-content: center;
		font-family: var(--font-mono);
		font-size: 9px;
		font-weight: 700;
		flex-shrink: 0;
	}

	.intg-info {
		display: flex;
		flex-direction: column;
		gap: 2px;
		flex: 1;
		min-width: 0;
	}

	.intg-name {
		font-family: var(--font-ui);
		font-size: 13px;
		font-weight: 500;
		color: #e6edf3;
	}

	.intg-desc {
		font-family: var(--font-mono);
		font-size: 10px;
		color: #484f58;
	}

	.intg-fields {
		padding: 0 14px 14px;
		border-top: 1px solid #21262d;
		background: #0d1117;
	}

	.intg-fields .field-label-sm:first-child {
		margin-top: 12px;
	}

	/* ── Notification rows ────────────────────────────────────── */
	.notif-master {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 16px;
	}

	.notif-master-label {
		font-family: var(--font-ui);
		font-size: 14px;
		font-weight: 600;
		color: #e6edf3;
	}

	.notif-rows {
		display: flex;
		flex-direction: column;
		gap: 10px;
		transition: opacity 0.18s;
	}

	.notif-rows.notif-disabled {
		opacity: 0.35;
		pointer-events: none;
	}

	.notif-row {
		display: flex;
		align-items: center;
		gap: 12px;
	}

	.notif-text {
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.notif-label {
		font-family: var(--font-ui);
		font-size: 13px;
		font-weight: 500;
		color: #e6edf3;
	}

	.notif-desc {
		font-family: var(--font-mono);
		font-size: 10px;
		color: #484f58;
	}

	/* ── Section label ────────────────────────────────────────── */
	.section-label {
		font-family: var(--font-mono);
		font-size: 11px;
		font-weight: 600;
		color: #8b949e;
		text-transform: uppercase;
		letter-spacing: 0.8px;
		margin-bottom: 14px;
	}

	/* ── Widget grid ──────────────────────────────────────────── */
	.widget-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 6px;
	}

	.widget-check-row {
		display: flex;
		align-items: center;
		gap: 8px;
		padding: 7px 10px;
		border-radius: 5px;
		cursor: pointer;
		transition: background 0.1s;
		user-select: none;
	}

	.widget-check-row:hover { background: #21262d; }

	.widget-check-row input[type="checkbox"] {
		width: 14px;
		height: 14px;
		accent-color: #3fb950;
		flex-shrink: 0;
		cursor: pointer;
	}

	.widget-check-icon { font-size: 14px; }

	.widget-check-label {
		font-family: var(--font-ui);
		font-size: 13px;
		color: #e6edf3;
	}

	/* ── Column picker ────────────────────────────────────────── */
	.col-picker {
		display: flex;
		gap: 8px;
	}

	.col-btn {
		flex: 1;
		padding: 8px;
		background: #21262d;
		border: 1px solid #30363d;
		border-radius: 5px;
		color: #8b949e;
		font-family: var(--font-mono);
		font-size: 12px;
		cursor: pointer;
		transition: border-color 0.1s, color 0.1s, background 0.1s;
	}

	.col-btn.active {
		border-color: #3fb950;
		color: #e6edf3;
		background: color-mix(in srgb, #3fb950 10%, #21262d);
	}

	.col-btn:hover:not(.active) { color: #e6edf3; border-color: #8b949e; }

	/* ── Step 7 settings link ─────────────────────────────────── */
	.settings-link {
		display: block;
		font-family: var(--font-mono);
		font-size: 11px;
		color: #484f58;
		text-decoration: none;
		text-align: center;
		margin-top: 4px;
		transition: color 0.1s;
	}
	.settings-link:hover { color: #8b949e; }

	/* ── Footer ───────────────────────────────────────────────── */
	.wiz-footer {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 32px;
		border-top: 1px solid #30363d;
		flex-shrink: 0;
	}

	.dots {
		display: flex;
		align-items: center;
		gap: 5px;
	}

	.dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		background: #30363d;
		transition: background 0.2s, width 0.2s, height 0.2s;
	}

	.dot.active {
		width: 8px;
		height: 8px;
		background: #3fb950;
	}

	.footer-btns {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	.btn-back {
		background: transparent;
		border: 1px solid #30363d;
		border-radius: 5px;
		color: #8b949e;
		font-family: var(--font-mono);
		font-size: 12px;
		padding: 8px 16px;
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}
	.btn-back:hover { color: #e6edf3; border-color: #8b949e; }

	.btn-next {
		background: #3fb950;
		border: none;
		border-radius: 5px;
		color: #0d1117;
		font-family: var(--font-mono);
		font-size: 12px;
		font-weight: 700;
		padding: 8px 18px;
		cursor: pointer;
		transition: opacity 0.1s, transform 0.1s;
	}
	.btn-next:hover  { opacity: 0.88; transform: translateY(-1px); }
	.btn-next:active { transform: translateY(0); }
</style>
