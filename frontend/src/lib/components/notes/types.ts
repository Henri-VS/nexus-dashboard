// Shared types and utilities for the Notes system

export type FileType = 'md' | 'pdf' | 'excalidraw' | 'pptx' | 'image' | 'other';

export interface StoredFile {
	path: string;
	content: string; // text for md/excalidraw; data URL (base64) for binary
	type: FileType;
	created: number;
	modified: number;
}

export interface StoredVault {
	id: string;
	name: string;
	files: Record<string, StoredFile>; // path → file
}

export interface TreeNode {
	name: string;
	path: string;
	kind: 'folder' | 'file';
	fileType?: FileType;
	children: TreeNode[];
}

export interface DisplayNode {
	name: string;
	path: string;
	kind: 'folder' | 'file';
	fileType?: FileType;
	depth: number;
	collapsed?: boolean; // folders only
}

export interface Tab {
	path: string;
	vaultId: string;
	name: string;
	fileType: FileType;
}

// ── Utilities ──────────────────────────────────────────────────────────────

export function getFileType(name: string): FileType {
	const ext = (name.split('.').pop() ?? '').toLowerCase();
	if (ext === 'md') return 'md';
	if (ext === 'pdf') return 'pdf';
	if (ext === 'excalidraw') return 'excalidraw';
	if (ext === 'pptx' || ext === 'ppt') return 'pptx';
	if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext)) return 'image';
	return 'other';
}

function buildTreeNodes(files: Record<string, StoredFile>): TreeNode[] {
	const folderMap = new Map<string, TreeNode>();
	const root: TreeNode[] = [];

	for (const filePath of Object.keys(files).sort()) {
		const parts = filePath.split('/');
		const fileName = parts[parts.length - 1];

		if (parts.length === 1) {
			root.push({ name: fileName, path: filePath, kind: 'file', fileType: getFileType(fileName), children: [] });
		} else {
			let siblings = root;
			let current = '';
			for (let i = 0; i < parts.length - 1; i++) {
				const seg = parts[i];
				current = current ? `${current}/${seg}` : seg;
				let folder = folderMap.get(current);
				if (!folder) {
					folder = { name: seg, path: current, kind: 'folder', children: [] };
					folderMap.set(current, folder);
					siblings.push(folder);
				}
				siblings = folder.children;
			}
			siblings.push({ name: fileName, path: filePath, kind: 'file', fileType: getFileType(fileName), children: [] });
		}
	}

	return sortNodes(root);
}

function sortNodes(nodes: TreeNode[]): TreeNode[] {
	return nodes
		.sort((a, b) => (a.kind === b.kind ? a.name.localeCompare(b.name) : a.kind === 'folder' ? -1 : 1))
		.map((n) => ({ ...n, children: sortNodes(n.children) }));
}

function flattenNodes(nodes: TreeNode[], depth: number, collapsed: Set<string>): DisplayNode[] {
	const result: DisplayNode[] = [];
	for (const n of nodes) {
		const isCollapsed = n.kind === 'folder' && collapsed.has(n.path);
		result.push({ name: n.name, path: n.path, kind: n.kind, fileType: n.fileType, depth, collapsed: isCollapsed });
		if (n.kind === 'folder' && !isCollapsed) {
			result.push(...flattenNodes(n.children, depth + 1, collapsed));
		}
	}
	return result;
}

export function buildDisplayTree(files: Record<string, StoredFile>, collapsed: Set<string>): DisplayNode[] {
	return flattenNodes(buildTreeNodes(files), 0, collapsed);
}

// ── Frontmatter ────────────────────────────────────────────────────────────

export function parseFrontmatter(content: string): { fields: Record<string, string>; body: string } {
	if (!content.startsWith('---')) return { fields: {}, body: content };
	const end = content.indexOf('\n---', 3);
	if (end === -1) return { fields: {}, body: content };
	const yaml = content.slice(4, end);
	const body = content.slice(end + 4).replace(/^\n/, '');
	const fields: Record<string, string> = {};
	for (const line of yaml.split('\n')) {
		const colon = line.indexOf(':');
		if (colon < 1) continue;
		const key = line.slice(0, colon).trim();
		const val = line.slice(colon + 1).trim();
		if (key) fields[key] = val;
	}
	return { fields, body };
}

export function serializeFrontmatter(fields: Record<string, string>, body: string): string {
	const keys = Object.keys(fields);
	if (keys.length === 0) return body;
	const yaml = keys.map((k) => `${k}: ${fields[k]}`).join('\n');
	return `---\n${yaml}\n---\n${body}`;
}

// ── Templates ──────────────────────────────────────────────────────────────

function j(...lines: string[]): string {
	return lines.join('\n');
}

export const TEMPLATES: Array<{ id: string; label: string; content: () => string }> = [
	{ id: 'blank', label: 'Blank', content: () => '' },
	{
		id: 'thm-room',
		label: 'THM Room',
		content: () => j(
			'---',
			`date: ${new Date().toISOString().slice(0, 10)}`,
			'difficulty: ',
			'tags: [thm, room]',
			'---',
			'# Room Name',
			'',
			'## Objectives',
			'- ',
			'',
			'## Notes',
			'',
			'## Commands Used',
			'```bash',
			'',
			'```',
			'',
			'## Flags',
		),
	},
	{
		id: 'tool',
		label: 'Tool',
		content: () => j(
			'---',
			`date: ${new Date().toISOString().slice(0, 10)}`,
			'tags: [tool]',
			'---',
			'# Tool Name',
			'',
			'## What it does',
			'',
			'## Install',
			'```bash',
			'',
			'```',
			'',
			'## Usage',
			'```bash',
			'',
			'```',
		),
	},
	{
		id: 'uni-lecture',
		label: 'Uni Lecture',
		content: () => j(
			'---',
			`date: ${new Date().toISOString().slice(0, 10)}`,
			'module: ',
			'tags: []',
			'---',
			'# Lecture: ',
			'',
			'## References',
			'- ',
			'',
			'## Class Notes',
		),
	},
	{
		id: 'blog-draft',
		label: 'Blog Draft',
		content: () => j(
			'---',
			`date: ${new Date().toISOString().slice(0, 10)}`,
			'tags: [blog, draft]',
			'---',
			'# Title',
			'',
			'## Intro',
			'',
			'## Main',
			'',
			'## Conclusion',
		),
	},
	{
		id: 'concept',
		label: 'Concept',
		content: () => j(
			'---',
			`date: ${new Date().toISOString().slice(0, 10)}`,
			'tags: []',
			'---',
			'# Concept Name',
			'',
			'## Definition',
			'',
			'## How it works',
			'',
			'## Examples',
			'',
			'## Related',
			'- ',
		),
	},
];

// ── Default vaults ────────────────────────────────────────────────────────

export function createDefaultVaults(): Record<string, StoredVault> {
	return {
		main: {
			id: 'main',
			name: 'My vault',
			files: {},
		},
	};
}
