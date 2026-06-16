import { writable } from 'svelte/store';
import { browser } from '$app/environment';
import { BASE } from '$lib/api';

export interface SnippetMeta {
	filename: string;
	size: number; // UTF-8 byte length
}

export const snippetFiles = writable<SnippetMeta[]>([]);
export const themeFiles   = writable<string[]>([]);

function authHeaders(): Record<string, string> {
	if (!browser) return {};
	const key = localStorage.getItem('nexus_api_key');
	return key ? { Authorization: `Bearer ${key}` } : {};
}

function styleId(filename: string): string {
	return `nexus-snippet-${filename.replace(/[^a-z0-9]/gi, '-')}`;
}

function removeAllSnippetTags(): void {
	document.querySelectorAll('style[id^="nexus-snippet-"]').forEach((el) => el.remove());
}

async function fetchAndInject(filename: string): Promise<SnippetMeta | null> {
	try {
		const res = await fetch(
			`${BASE}/api/nexus/snippets/${encodeURIComponent(filename)}`,
			{ headers: authHeaders() },
		);
		if (!res.ok) return null;
		const css = await res.text();
		const id  = styleId(filename);

		let tag = document.getElementById(id) as HTMLStyleElement | null;
		if (!tag) {
			tag    = document.createElement('style');
			tag.id = id;
			document.head.appendChild(tag);
		}
		tag.textContent = css;

		return { filename, size: new TextEncoder().encode(css).length };
	} catch {
		return null;
	}
}

export async function loadSnippets(): Promise<void> {
	if (!browser) return;
	try {
		const res = await fetch(`${BASE}/api/nexus/snippets`, { headers: authHeaders() });
		if (!res.ok) return;
		const files: string[] = await res.json();
		const results = await Promise.all(files.map(fetchAndInject));
		snippetFiles.set(results.filter((r): r is SnippetMeta => r !== null));
	} catch { /* backend unreachable — no snippets applied */ }
}

export async function reloadSnippets(): Promise<void> {
	if (!browser) return;
	removeAllSnippetTags();
	snippetFiles.set([]);
	await loadSnippets();
}

export async function loadThemes(): Promise<void> {
	if (!browser) return;
	try {
		const res = await fetch(`${BASE}/api/nexus/themes`, { headers: authHeaders() });
		if (!res.ok) return;
		const files: string[] = await res.json();
		themeFiles.set(files);
	} catch { /* ignore */ }
}
