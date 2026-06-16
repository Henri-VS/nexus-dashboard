<script lang="ts">
	import { onMount } from 'svelte';
	import { notes as notesApi } from '$lib/api';
	import type { NoteFile } from '$lib/types';
	import Card from '$lib/components/Card.svelte';

	// ── Mock — shown only when the API itself is unreachable ─────
	const MOCK: NoteFile[] = [
		{
			path: 'Security/THM-notes.md',
			name: 'THM-notes',
			modified: new Date(Date.now() - 2 * 3_600_000).toISOString(),
			content: `# TryHackMe Notes

## Completed rooms
- [x] Linux Fundamentals 1-3
- [x] Nmap
- [x] Burp Suite basics
- [ ] Metasploit
- [ ] Active Directory basics

## Commands
\`nmap -sV -sC -oN scan.txt $IP\`
\`gobuster dir -u http://$IP -w /usr/share/wordlists/dirb/common.txt\`

## Resources
→ https://tryhackme.com/path/outline/presecurity
→ https://book.hacktricks.xyz`,
		},
		{
			path: 'Projects/homelab.md',
			name: 'homelab',
			modified: new Date(Date.now() - 18 * 3_600_000).toISOString(),
		},
		{
			path: 'Daily/2026-06-07.md',
			name: '2026-06-07',
			modified: new Date(Date.now() - 5 * 3_600_000).toISOString(),
		},
		{
			path: 'Security/wazuh-setup.md',
			name: 'wazuh-setup',
			modified: new Date(Date.now() - 2 * 86_400_000).toISOString(),
		},
		{
			path: 'Certs/security-plus.md',
			name: 'security-plus',
			modified: new Date(Date.now() - 3 * 86_400_000).toISOString(),
		},
	];

	// ── State ─────────────────────────────────────────────────────
	let list: NoteFile[] = [];
	let selected: NoteFile | null = null;
	let loading = true;
	let mocked = false;

	async function load() {
		const res = await notesApi.recent();
		if (res && res.length > 0) {
			list = res.slice(0, 5);
			mocked = false;
		} else {
			list = MOCK;
			mocked = true;
		}
		// Select top note (content might already be inline, else fetch)
		if (list[0]) {
			if (list[0].content) {
				selected = list[0];
			} else {
				const full = await notesApi.file(list[0].path);
				selected = full ?? list[0];
			}
		}
		loading = false;
	}

	async function selectNote(note: NoteFile) {
		selected = note;
		if (!note.content) {
			const full = await notesApi.file(note.path);
			if (full) {
				selected = full;
				// Update in list too
				list = list.map((n) => (n.path === full.path ? full : n));
			}
		}
	}

	onMount(load);

	function relTime(ts: string | number): string {
		const d = new Date(typeof ts === 'number' ? ts * 1000 : ts);
		const diff = Date.now() - d.getTime();
		const m = Math.floor(diff / 60_000);
		if (m < 60)  return `${m}m`;
		const h = Math.floor(m / 60);
		if (h < 24)  return `${h}h`;
		return `${Math.floor(h / 24)}d`;
	}

	// Truncate preview to a reasonable line count
	function previewLines(content: string, maxLines = 16): string {
		return content.split('\n').slice(0, maxLines).join('\n');
	}
</script>

<Card
	label="notes"
	accentColor="var(--accent3)"
	{loading}
	{mocked}
>
	<div class="notes-layout">

		<!-- File list -->
		<ul class="file-list">
			{#each list as note (note.path)}
				<li>
					<button
						class="file-item"
						class:active={selected?.path === note.path}
						on:click={() => selectNote(note)}
					>
						<span class="file-name">{note.name}</span>
						<span class="file-time">{relTime(note.modified)}</span>
					</button>
				</li>
			{/each}
		</ul>

		<!-- Raw markdown preview — intentionally NOT rendered to HTML -->
		{#if selected?.content}
			<div class="divider"></div>
			<pre class="md-preview" aria-label="Note preview">{previewLines(selected.content)}</pre>
		{/if}

	</div>
</Card>

<style>
	.notes-layout {
		display: flex;
		flex-direction: column;
		gap: 0;
	}

	/* ── File list ──────────────────────────────────────────── */
	.file-list {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 1px;
	}

	.file-item {
		display: flex;
		align-items: center;
		justify-content: space-between;
		width: 100%;
		padding: 0.3rem 0.4rem;
		background: none;
		border: none;
		border-radius: 3px;
		cursor: pointer;
		text-align: left;
		transition: background 0.1s;
	}

	.file-item:hover {
		background: var(--bg2);
	}

	.file-item.active {
		background: color-mix(in srgb, var(--accent3) 10%, transparent);
		border-left: 2px solid var(--accent3);
		padding-left: 0.25rem;
	}

	.file-name {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text0);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.file-item.active .file-name {
		color: var(--accent3);
	}

	.file-time {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		color: var(--text2);
		flex-shrink: 0;
		margin-left: 0.5rem;
	}

	/* ── Divider ────────────────────────────────────────────── */
	.divider {
		height: 1px;
		background: var(--border);
		margin: 0.6rem 0;
	}

	/* ── Raw markdown preview ───────────────────────────────── */
	/*
	   Intentionally unstyled / not parsed — shows raw .md text
	   exactly as the user wrote it: # headings, [x] boxes, → links.
	*/
	.md-preview {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		line-height: 1.6;
		color: var(--text1);
		background: var(--bg0);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 0.6rem 0.75rem;
		overflow-x: auto;
		white-space: pre;
		/* Limit visible height — user scrolls if needed */
		max-height: 14rem;
		overflow-y: auto;
	}

	/* Highlight markdown syntax characters with subtle color */
	.md-preview :global(span.heading)  { color: var(--accent3); }
</style>
