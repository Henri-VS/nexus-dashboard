<script lang="ts">
	import { X } from '@lucide/svelte';
	import { dashConfig } from '$lib/stores/dashConfig';
	import type { WidgetSettings } from '$lib/stores/dashConfig';

	export let widgetId: string;
	export let onClose: () => void;

	$: widget = $dashConfig.widgets.find((w) => w.id === widgetId);
	$: s      = widget?.settings ?? {};

	function set(patch: Partial<WidgetSettings>) {
		dashConfig.updateWidgetSettings(widgetId, patch);
	}

	function certsFromStr(val: string): string[] {
		return val.split(',').map((v) => v.trim()).filter(Boolean);
	}

	function entitiesToStr(arr: string[] | undefined): string {
		return (arr ?? []).join(', ');
	}
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="popover" role="dialog" aria-label="Widget settings">
	<div class="pop-header">
		<span class="pop-title">Widget Settings</span>
		<button class="pop-close" on:click={onClose} title="Close">
			<X size={13} strokeWidth={2} />
		</button>
	</div>

	<div class="pop-body">
		<!-- ── Common ──────────────────────────────────────────── -->
		<section class="section">
			<label class="field">
				<span class="field-label">Title</span>
				<input
					class="inp"
					type="text"
					placeholder="(default)"
					value={s.customTitle ?? ''}
					on:input={(e) => set({ customTitle: (e.currentTarget as HTMLInputElement).value || undefined })}
				/>
			</label>

			<label class="field">
				<span class="field-label">Accent</span>
				<div class="color-row">
					<input
						class="inp-color"
						type="color"
						value={s.accentOverride ?? '#3fb950'}
						on:input={(e) => set({ accentOverride: (e.currentTarget as HTMLInputElement).value })}
					/>
					{#if s.accentOverride}
						<button class="clear-btn" on:click={() => set({ accentOverride: undefined })} title="Clear override">clear</button>
					{/if}
				</div>
			</label>
		</section>

		<!-- ── Weather ────────────────────────────────────────── -->
		{#if widgetId === 'weather'}
			<section class="section">
				<div class="section-title">Location</div>
				<label class="field">
					<span class="field-label">Name</span>
					<input class="inp" type="text" placeholder="Cape Town" value={s.locationName ?? ''}
						on:input={(e) => set({ locationName: (e.currentTarget as HTMLInputElement).value })} />
				</label>
				<label class="field">
					<span class="field-label">Lat</span>
					<input class="inp" type="number" step="0.0001" placeholder="-33.9249"
						value={s.lat ?? ''}
						on:input={(e) => { const v = parseFloat((e.currentTarget as HTMLInputElement).value); if (!isNaN(v)) set({ lat: v }); }} />
				</label>
				<label class="field">
					<span class="field-label">Lon</span>
					<input class="inp" type="number" step="0.0001" placeholder="18.4241"
						value={s.lon ?? ''}
						on:input={(e) => { const v = parseFloat((e.currentTarget as HTMLInputElement).value); if (!isNaN(v)) set({ lon: v }); }} />
				</label>
				<label class="field">
					<span class="field-label">Units</span>
					<select class="inp" value={s.units ?? 'C'} on:change={(e) => set({ units: (e.currentTarget as HTMLSelectElement).value as 'C'|'F' })}>
						<option value="C">Celsius</option>
						<option value="F">Fahrenheit</option>
					</select>
				</label>
				<label class="field">
					<span class="field-label">Wind</span>
					<select class="inp" value={s.windUnit ?? 'kts'} on:change={(e) => set({ windUnit: (e.currentTarget as HTMLSelectElement).value as 'kts'|'kmh' })}>
						<option value="kts">Knots</option>
						<option value="kmh">km/h</option>
					</select>
				</label>
			</section>
		{/if}

		<!-- ── System ─────────────────────────────────────────── -->
		{#if widgetId === 'system'}
			<section class="section">
				<div class="section-title">System</div>
				<label class="field">
					<span class="field-label">Poll (s)</span>
					<input class="inp" type="number" min="1" max="60" value={s.pollInterval ?? 5}
						on:input={(e) => { const v = parseInt((e.currentTarget as HTMLInputElement).value); if (!isNaN(v)) set({ pollInterval: v }); }} />
				</label>
				<div class="section-title" style="margin-top:.4rem">Show</div>
				{#each [['showCpu','CPU'],['showMemory','Memory'],['showDisk','Disk'],['showNetwork','Network']] as [key, lbl]}
					<label class="field-check">
						<input type="checkbox"
							checked={s[key as keyof WidgetSettings] !== false}
							on:change={(e) => set({ [key]: (e.currentTarget as HTMLInputElement).checked } as Partial<WidgetSettings>)} />
						<span>{lbl}</span>
					</label>
				{/each}
			</section>
		{/if}

		<!-- ── Security ───────────────────────────────────────── -->
		{#if widgetId === 'security'}
			<section class="section">
				<div class="section-title">Security</div>
				<label class="field">
					<span class="field-label">Max alerts</span>
					<input class="inp" type="number" min="1" max="50" value={s.maxAlerts ?? 10}
						on:input={(e) => { const v = parseInt((e.currentTarget as HTMLInputElement).value); if (!isNaN(v)) set({ maxAlerts: v }); }} />
				</label>
				<label class="field">
					<span class="field-label">Severity</span>
					<input class="inp" type="text" placeholder="high,critical"
						value={s.severityFilter ?? ''}
						on:input={(e) => set({ severityFilter: (e.currentTarget as HTMLInputElement).value })} />
				</label>
			</section>
		{/if}

		<!-- ── Docker ─────────────────────────────────────────── -->
		{#if widgetId === 'docker'}
			<section class="section">
				<div class="section-title">Docker</div>
				<label class="field">
					<span class="field-label">Poll (s)</span>
					<input class="inp" type="number" min="2" max="120" value={s.dockerPollInterval ?? 10}
						on:input={(e) => { const v = parseInt((e.currentTarget as HTMLInputElement).value); if (!isNaN(v)) set({ dockerPollInterval: v }); }} />
				</label>
				<label class="field-check">
					<input type="checkbox" checked={s.showExited ?? false}
						on:change={(e) => set({ showExited: (e.currentTarget as HTMLInputElement).checked })} />
					<span>Show exited containers</span>
				</label>
			</section>
		{/if}

		<!-- ── Learning ───────────────────────────────────────── -->
		{#if widgetId === 'learning'}
			<section class="section">
				<div class="section-title">Learning</div>
				<label class="field">
					<span class="field-label">THM user</span>
					<input class="inp" type="text" placeholder="username"
						value={s.thmUsername ?? ''}
						on:input={(e) => set({ thmUsername: (e.currentTarget as HTMLInputElement).value })} />
				</label>
				<label class="field">
					<span class="field-label">Certs</span>
					<input class="inp" type="text" placeholder="OSCP, CEH"
						value={entitiesToStr(s.certs)}
						on:input={(e) => set({ certs: certsFromStr((e.currentTarget as HTMLInputElement).value) })} />
				</label>
			</section>
		{/if}

		<!-- ── Home ───────────────────────────────────────────── -->
		{#if widgetId === 'home'}
			<section class="section">
				<div class="section-title">Home Assistant</div>
				<label class="field">
					<span class="field-label">Entities</span>
					<textarea class="inp inp-ta" rows="3" placeholder="sensor.cpu_temp, light.living"
						value={entitiesToStr(s.entities)}
						on:input={(e) => set({ entities: certsFromStr((e.currentTarget as HTMLTextAreaElement).value) })}></textarea>
				</label>
			</section>
		{/if}

		<!-- ── Notes ──────────────────────────────────────────── -->
		{#if widgetId === 'notes'}
			<section class="section">
				<div class="section-title">Notes</div>
				<label class="field">
					<span class="field-label">Vault</span>
					<input class="inp" type="text" placeholder="default"
						value={s.previewVault ?? ''}
						on:input={(e) => set({ previewVault: (e.currentTarget as HTMLInputElement).value })} />
				</label>
			</section>
		{/if}
	</div>
</div>

<style>
	.popover {
		position: absolute;
		top: 2.2rem;
		right: 0;
		z-index: 80;
		width: 230px;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		box-shadow: 0 8px 32px rgba(0,0,0,0.5);
		overflow: hidden;
	}

	/* ── Header ──────────────────────────────────────── */
	.pop-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.5rem 0.7rem;
		border-bottom: 1px solid var(--border);
		background: var(--bg2);
	}

	.pop-title {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text2);
	}

	.pop-close {
		display: flex; align-items: center; justify-content: center;
		background: none; border: none;
		color: var(--text2); cursor: pointer;
		padding: 2px; border-radius: 3px;
		transition: color 0.1s, background 0.1s;
	}
	.pop-close:hover { color: var(--text0); background: var(--bg3); }

	/* ── Body ────────────────────────────────────────── */
	.pop-body {
		max-height: 420px;
		overflow-y: auto;
		padding: 0.4rem;
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
	}

	.section {
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}

	.section-title {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--accent);
		margin-top: 0.2rem;
	}

	/* ── Fields ──────────────────────────────────────── */
	.field {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.field-label {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
		flex-shrink: 0;
		width: 52px;
	}

	.inp {
		flex: 1;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.72rem;
		padding: 0.22rem 0.4rem;
		min-width: 0;
		outline: none;
		transition: border-color 0.1s;
	}
	.inp:focus { border-color: var(--accent); }

	.inp-ta { resize: vertical; line-height: 1.4; }

	.field-check {
		display: flex;
		align-items: center;
		gap: 0.45rem;
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--text1);
		cursor: pointer;
		padding: 0.05rem 0;
	}

	/* ── Color row ───────────────────────────────────── */
	.color-row {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		flex: 1;
	}

	.inp-color {
		width: 28px; height: 22px;
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 1px;
		background: var(--bg2);
		cursor: pointer;
	}

	.clear-btn {
		background: none; border: none;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.62rem;
		cursor: pointer;
		padding: 1px 4px;
		border-radius: 3px;
		transition: color 0.1s, background 0.1s;
	}
	.clear-btn:hover { color: var(--red); background: var(--bg3); }

</style>
