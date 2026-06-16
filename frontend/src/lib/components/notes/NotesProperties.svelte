<script lang="ts">
	import { X, Plus } from '@lucide/svelte';
	import { type StoredFile, parseFrontmatter, serializeFrontmatter } from './types';

	// ── Props ───────────────────────────────────────────────────────────────
	export let file: StoredFile | null = null;
	export let allFiles: Record<string, StoredFile> = {};
	export let open: boolean = true;

	export let onFrontmatterChange: (path: string, newContent: string) => void = () => {};
	export let onOpenFile: (path: string) => void = () => {};

	// ── Derived ──────────────────────────────────────────────────────────────
	interface FMField { key: string; value: string }

	let fields: FMField[] = [];
	let bodyWordCount = 0;
	let bodyCharCount = 0;
	let backlinks: string[] = [];
	let newKey = '';
	let newVal = '';

	$: if (file?.type === 'md') {
		const { fields: fm, body } = parseFrontmatter(file.content);
		fields = Object.entries(fm).map(([key, value]) => ({ key, value }));
		bodyWordCount = body.trim() ? body.trim().split(/\s+/).length : 0;
		bodyCharCount = body.length;
		backlinks = findBacklinks(file.path, allFiles);
	} else {
		fields = [];
		bodyWordCount = 0;
		bodyCharCount = 0;
		backlinks = [];
	}

	function findBacklinks(targetPath: string, files: Record<string, StoredFile>): string[] {
		const target = targetPath.split('/').pop()?.replace(/\.md$/, '') ?? '';
		const results: string[] = [];
		for (const [path, f] of Object.entries(files)) {
			if (path === targetPath) continue;
			if (f.type !== 'md') continue;
			const pattern = new RegExp(`\\[\\[${target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, 'i');
			if (pattern.test(f.content)) {
				results.push(path);
			}
		}
		return results;
	}

	// ── Parse tags from frontmatter value ────────────────────────────────────
	function parseTags(val: string): string[] {
		const inner = val.trim();
		if (inner.startsWith('[') && inner.endsWith(']')) {
			return inner
				.slice(1, -1)
				.split(',')
				.map((s) => s.trim())
				.filter(Boolean);
		}
		return inner ? [inner] : [];
	}

	function serializeTags(tags: string[]): string {
		return `[${tags.join(', ')}]`;
	}

	// ── Field updates ─────────────────────────────────────────────────────
	function updateField(index: number, val: string) {
		fields[index] = { ...fields[index], value: val };
		flush();
	}

	function removeTag(fIndex: number, tagIndex: number) {
		const tags = parseTags(fields[fIndex].value);
		tags.splice(tagIndex, 1);
		fields[fIndex] = { ...fields[fIndex], value: serializeTags(tags) };
		flush();
	}

	function addTag(fIndex: number, tag: string) {
		const tags = parseTags(fields[fIndex].value);
		if (tag && !tags.includes(tag)) tags.push(tag);
		fields[fIndex] = { ...fields[fIndex], value: serializeTags(tags) };
		flush();
	}

	function removeField(index: number) {
		fields = fields.filter((_, i) => i !== index);
		flush();
	}

	function addField() {
		if (!newKey.trim()) return;
		fields = [...fields, { key: newKey.trim(), value: newVal.trim() }];
		newKey = '';
		newVal = '';
		flush();
	}

	function flush() {
		if (!file) return;
		const fm: Record<string, string> = {};
		for (const f of fields) fm[f.key] = f.value;
		const { body } = parseFrontmatter(file.content);
		const newContent = serializeFrontmatter(fm, body);
		onFrontmatterChange(file.path, newContent);
	}

	// ── Date formatter ────────────────────────────────────────────────────
	function fmtDate(ts: number): string {
		return new Date(ts).toLocaleString('en-ZA', {
			year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
		});
	}
</script>

<div class="props-panel" class:closed={!open}>
	{#if file && open}
		<div class="props-inner">
			<div class="section-label">Properties</div>

			{#if file.type === 'md'}
				<!-- ── Frontmatter fields ────────────────────────────── -->
				{#each fields as field, i}
					<div class="field-row">
						<span class="field-key">{field.key}</span>

						{#if field.key === 'date'}
							<input
								class="field-input date-input"
								type="date"
								value={field.value}
								on:change={(e) => updateField(i, (e.currentTarget as HTMLInputElement).value)}
							/>
						{:else if field.key === 'tags'}
							<div class="tags-wrap">
								{#each parseTags(field.value) as tag, ti}
									<span class="tag-pill">
										{tag}
										<button class="tag-rm" on:click={() => removeTag(i, ti)} title="Remove tag">
											<X size={9} strokeWidth={3} />
										</button>
									</span>
								{/each}
								<form
									class="tag-add-form"
									on:submit|preventDefault={(e) => {
										const inp = (e.currentTarget as HTMLFormElement).querySelector('input') as HTMLInputElement;
										addTag(i, inp.value.trim());
										inp.value = '';
									}}
								>
									<input
										class="tag-input"
										type="text"
										placeholder="+ tag"
										on:blur={(e) => {
											const val = (e.currentTarget as HTMLInputElement).value.trim();
											if (val) { addTag(i, val); (e.currentTarget as HTMLInputElement).value = ''; }
										}}
									/>
								</form>
							</div>
						{:else}
							<div class="field-input-row">
								<input
									class="field-input"
									type="text"
									value={field.value}
									on:change={(e) => updateField(i, (e.currentTarget as HTMLInputElement).value)}
								/>
								<button class="field-rm" on:click={() => removeField(i)} title="Remove field">
									<X size={10} strokeWidth={2.5} />
								</button>
							</div>
						{/if}
					</div>
				{/each}

				<!-- Add property row -->
				<div class="add-prop-row">
					<input
						class="add-key-input"
						type="text"
						placeholder="key"
						bind:value={newKey}
						on:keydown={(e) => e.key === 'Enter' && addField()}
					/>
					<input
						class="add-val-input"
						type="text"
						placeholder="value"
						bind:value={newVal}
						on:keydown={(e) => e.key === 'Enter' && addField()}
					/>
					<button class="add-prop-btn" on:click={addField} title="Add property">
						<Plus size={11} strokeWidth={2.5} />
					</button>
				</div>
			{/if}

			<!-- ── Stats ──────────────────────────────────────────── -->
			<div class="section-label" style="margin-top: 0.75rem">Stats</div>
			<div class="stat-grid">
				<div class="stat-item">
					<span class="stat-k">Words</span>
					<span class="stat-v">{bodyWordCount}</span>
				</div>
				<div class="stat-item">
					<span class="stat-k">Chars</span>
					<span class="stat-v">{bodyCharCount}</span>
				</div>
				<div class="stat-item">
					<span class="stat-k">Backlinks</span>
					<span class="stat-v">{backlinks.length}</span>
				</div>
				<div class="stat-item">
					<span class="stat-k">Type</span>
					<span class="stat-v">{file.type}</span>
				</div>
			</div>

			{#if backlinks.length}
				<div class="backlinks-list">
					{#each backlinks as bl}
						<!-- svelte-ignore a11y-click-events-have-key-events -->
						<!-- svelte-ignore a11y-no-static-element-interactions -->
						<div class="backlink-item" on:click={() => onOpenFile(bl)} title={bl}>
							{bl.split('/').pop()}
						</div>
					{/each}
				</div>
			{/if}

			<div class="date-row">
				<span class="date-k">Created</span>
				<span class="date-v">{fmtDate(file.created)}</span>
			</div>
			<div class="date-row">
				<span class="date-k">Modified</span>
				<span class="date-v">{fmtDate(file.modified)}</span>
			</div>
		</div>
	{/if}
</div>

<style>
	.props-panel {
		width: 260px;
		flex-shrink: 0;
		background: var(--bg1);
		border-left: 1px solid var(--border);
		overflow: hidden;
		transition: width 0.2s ease;
	}

	.props-panel.closed {
		width: 0;
		border-left-width: 0;
	}

	.props-inner {
		width: 260px;
		height: 100%;
		overflow-y: auto;
		padding: 0.75rem 0.8rem 1.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.45rem;
	}

	/* ── Section label ────────────────────────────────────────────── */
	.section-label {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text2);
		padding-bottom: 0.3rem;
		border-bottom: 1px solid var(--border);
	}

	/* ── Frontmatter fields ───────────────────────────────────────── */
	.field-row {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}

	.field-key {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		text-transform: lowercase;
		letter-spacing: 0.04em;
	}

	.field-input-row {
		display: flex;
		gap: 0.25rem;
		align-items: center;
	}

	.field-input {
		flex: 1;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text0);
		font-family: var(--font-mono);
		font-size: 0.73rem;
		padding: 0.25rem 0.4rem;
		width: 100%;
	}

	.field-input:focus { outline: 1px solid var(--accent3); border-color: var(--accent3); }

	.date-input { width: 100%; }

	.field-rm {
		display: flex;
		align-items: center;
		justify-content: center;
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		padding: 2px;
		border-radius: 3px;
		flex-shrink: 0;
	}

	.field-rm:hover { color: var(--red); background: color-mix(in srgb, var(--red) 12%, transparent); }

	/* ── Tags ─────────────────────────────────────────────────────── */
	.tags-wrap {
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem;
		align-items: center;
	}

	.tag-pill {
		display: inline-flex;
		align-items: center;
		gap: 0.2rem;
		padding: 0.1rem 0.4rem;
		background: color-mix(in srgb, var(--accent3) 15%, var(--bg2));
		border: 1px solid color-mix(in srgb, var(--accent3) 30%, transparent);
		border-radius: 999px;
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--accent3);
	}

	.tag-rm {
		display: flex;
		align-items: center;
		background: none;
		border: none;
		color: var(--accent3);
		cursor: pointer;
		padding: 0;
		opacity: 0.6;
	}

	.tag-rm:hover { opacity: 1; }

	.tag-add-form { display: inline-flex; }

	.tag-input {
		background: none;
		border: 1px dashed var(--border);
		border-radius: 999px;
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.65rem;
		padding: 0.08rem 0.4rem;
		width: 50px;
		transition: width 0.2s, border-color 0.1s;
	}

	.tag-input:focus {
		outline: none;
		width: 80px;
		border-color: var(--accent3);
		color: var(--text0);
	}

	/* ── Add property ─────────────────────────────────────────────── */
	.add-prop-row {
		display: flex;
		gap: 0.25rem;
		align-items: center;
		margin-top: 0.1rem;
	}

	.add-key-input, .add-val-input {
		background: var(--bg2);
		border: 1px dashed var(--border);
		border-radius: var(--radius);
		color: var(--text1);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		padding: 0.22rem 0.35rem;
	}

	.add-key-input { width: 70px; }
	.add-val-input { flex: 1; }

	.add-key-input:focus, .add-val-input:focus {
		outline: none;
		border-color: var(--accent3);
		border-style: solid;
	}

	.add-prop-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text2);
		cursor: pointer;
		padding: 0.22rem 0.35rem;
		flex-shrink: 0;
		transition: color 0.1s, border-color 0.1s;
	}

	.add-prop-btn:hover { color: var(--accent3); border-color: var(--accent3); }

	/* ── Stats ────────────────────────────────────────────────────── */
	.stat-grid {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 0.35rem;
	}

	.stat-item {
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 0.35rem 0.5rem;
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}

	.stat-k {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--text2);
	}

	.stat-v {
		font-family: var(--font-mono);
		font-size: 0.82rem;
		color: var(--text0);
	}

	/* ── Backlinks ────────────────────────────────────────────────── */
	.backlinks-list {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}

	.backlink-item {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--accent3);
		padding: 0.15rem 0.3rem;
		background: color-mix(in srgb, var(--accent3) 8%, transparent);
		border-radius: 3px;
		cursor: pointer;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		transition: background 0.1s;
	}

	.backlink-item:hover {
		background: color-mix(in srgb, var(--accent3) 18%, transparent);
	}

	/* ── Dates ────────────────────────────────────────────────────── */
	.date-row {
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}

	.date-k {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		color: var(--text2);
	}

	.date-v {
		font-family: var(--font-mono);
		font-size: 0.66rem;
		color: var(--text1);
	}
</style>
