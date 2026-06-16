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

// ── Default vaults (mock data) ─────────────────────────────────────────────

export function createDefaultVaults(): Record<string, StoredVault> {
	const now = Date.now();
	const day = 86_400_000;

	return {
		main: {
			id: 'main',
			name: 'Main vault',
			files: {
				'00 Inbox/getting-started.md': {
					path: '00 Inbox/getting-started.md',
					content: j(
						'---',
						'date: 2026-05-01',
						'tags: [inbox]',
						'---',
						'# Getting Started',
						'',
						'Inbox — dump notes here before filing.',
						'',
						'## Today',
						'- [ ] Review nmap room notes',
						'- [ ] Write homelab blog post',
						'- [x] Set up Wazuh on lab server',
						'- [x] Configure Ollama on LOQ laptop',
					),
					type: 'md', created: now - day * 30, modified: now - day * 2,
				},
				'10 Learning/TryHackMe/nmap-room.md': {
					path: '10 Learning/TryHackMe/nmap-room.md',
					content: j(
						'---',
						'date: 2026-05-15',
						'difficulty: easy',
						'tags: [thm, room, nmap, scanning]',
						'---',
						'# Nmap — THM Room',
						'',
						'## Objectives',
						'- Understand TCP/UDP port scanning',
						'- Learn Nmap switch options',
						'- Perform service and OS detection',
						'',
						'## Notes',
						'',
						'Nmap (Network Mapper) is the industry-standard tool for network reconnaissance.',
						'',
						'### Core Scan Types',
						'',
						'| Switch | Scan Type | Notes |',
						'|--------|-----------|-------|',
						'| `-sS` | SYN stealth | Default if root |',
						'| `-sT` | TCP connect | Non-root |',
						'| `-sU` | UDP | Slow, specify ports |',
						'| `-sV` | Version detection | Fingerprints services |',
						'| `-sC` | Default scripts | NSE scripts |',
						'| `-A` | Aggressive | OS + version + scripts |',
						'',
						'### Common Commands',
						'',
						'```bash',
						'# Full scan — all ports, version, scripts',
						'nmap -sV -sC -p- --open -T4 <target>',
						'',
						'# OS detection (needs root)',
						'sudo nmap -O <target>',
						'',
						'# Top 1000 UDP ports',
						'sudo nmap -sU --top-ports 1000 <target>',
						'',
						'# Output to all formats',
						'nmap -sV -oA scan_results <target>',
						'```',
						'',
						'> Always run a quick `-F` scan first, then full `-p-` scan in background.',
						'',
						'## Flags',
						'- Task 2: `THM{nmap_scan_complete}`',
					),
					type: 'md', created: now - day * 23, modified: now - day * 20,
				},
				'10 Learning/TryHackMe/linux-priv-esc.md': {
					path: '10 Learning/TryHackMe/linux-priv-esc.md',
					content: j(
						'---',
						'date: 2026-05-22',
						'difficulty: medium',
						'tags: [thm, room, linux, privesc]',
						'---',
						'# Linux Privilege Escalation',
						'',
						'## Objectives',
						'- Enumerate priv esc vectors',
						'- Exploit SUID binaries, cron jobs, writable paths',
						'',
						'## Enumeration Checklist',
						'',
						'```bash',
						'# User context',
						'id && whoami && groups',
						'',
						'# Sudo permissions',
						'sudo -l',
						'',
						'# SUID/SGID binaries',
						'find / -perm -4000 -type f 2>/dev/null',
						'find / -perm -2000 -type f 2>/dev/null',
						'',
						'# World-writable dirs',
						'find / -writable -type d 2>/dev/null',
						'',
						'# Cron jobs',
						'cat /etc/crontab',
						'ls -la /etc/cron.*',
						'crontab -l',
						'',
						'# Listening services',
						'ss -tulnp',
						'```',
						'',
						'## Common Vectors',
						'',
						'### SUID Binaries',
						'Check [[Tools & Commands/nmap]] and [GTFObins](https://gtfobins.github.io) for paths.',
						'',
						'### Writable /etc/passwd',
						'',
						'```bash',
						'openssl passwd -1 -salt hack password123',
						"echo 'hack:HASH:0:0::/root:/bin/bash' >> /etc/passwd",
						'su hack',
						'```',
						'',
						'> **GTFObins** first — always check before manual exploitation.',
					),
					type: 'md', created: now - day * 16, modified: now - day * 14,
				},
				'10 Learning/network-diagram.excalidraw': {
					path: '10 Learning/network-diagram.excalidraw',
					content: JSON.stringify({
						type: 'excalidraw', version: 2, source: 'dashboard',
						elements: [], appState: { viewBackgroundColor: '#1e1e2e', currentItemFontFamily: 1 }, files: {},
					}, null, 2),
					type: 'excalidraw', created: now - day * 5, modified: now - day * 1,
				},
				'10 Learning/Networking/osi-model.md': {
					path: '10 Learning/Networking/osi-model.md',
					content: j(
						'---',
						'date: 2026-05-10',
						'tags: [networking, osi, fundamentals]',
						'---',
						'# OSI Model',
						'',
						'## The 7 Layers',
						'',
						'| # | Layer | PDU | Protocols | Device |',
						'|---|-------|-----|-----------|--------|',
						'| 7 | Application | Data | HTTP, DNS, FTP, SSH | — |',
						'| 6 | Presentation | Data | SSL/TLS, JPEG | — |',
						'| 5 | Session | Data | NetBIOS, RPC | — |',
						'| 4 | Transport | Segment | TCP, UDP | — |',
						'| 3 | Network | Packet | IP, ICMP, OSPF | Router |',
						'| 2 | Data Link | Frame | Ethernet, 802.11 | Switch |',
						'| 1 | Physical | Bit | Copper, Fiber | Hub |',
						'',
						'> Mnemonic (top→bottom): **"All People Seem To Need Data Processing"**',
						'',
						'## TCP vs UDP',
						'',
						'| Feature | TCP | UDP |',
						'|---------|-----|-----|',
						'| Connection | 3-way handshake | Connectionless |',
						'| Reliability | Guaranteed | Best effort |',
						'| Order | In-order | Not guaranteed |',
						'| Use case | HTTP, SSH | DNS, streaming |',
					),
					type: 'md', created: now - day * 28, modified: now - day * 25,
				},
				'10 Learning/Tools & Commands/nmap.md': {
					path: '10 Learning/Tools & Commands/nmap.md',
					content: j(
						'---',
						'date: 2026-05-12',
						'tags: [tool, nmap, scanning]',
						'---',
						'# nmap',
						'',
						'## What it does',
						'Network scanner — host discovery, port scanning, service fingerprinting, OS detection.',
						'',
						'## Install',
						'```bash',
						'sudo apt install nmap        # Debian/Ubuntu',
						'sudo pacman -S nmap          # Arch/CachyOS',
						'```',
						'',
						'## Usage',
						'```bash',
						'# Quick scan (top 100 ports)',
						'nmap -F <target>',
						'',
						'# Full TCP scan',
						'nmap -p- -T4 <target>',
						'',
						'# Service + scripts',
						'nmap -sV -sC <target>',
						'',
						'# Aggressive',
						'nmap -A <target>',
						'',
						'# UDP (slow)',
						'sudo nmap -sU --top-ports 100 <target>',
						'',
						'# Output all formats',
						'nmap -oA results <target>',
						'```',
						'',
						'## NSE Scripts',
						'```bash',
						'nmap --script vuln <target>',
						'nmap --script http-enum <target>',
						'nmap --script smb-enum-shares <target>',
						'```',
					),
					type: 'md', created: now - day * 25, modified: now - day * 22,
				},
				'20 Blog/homelab-build.md': {
					path: '20 Blog/homelab-build.md',
					content: j(
						'---',
						'date: 2026-06-01',
						'tags: [blog, homelab, docker]',
						'status: draft',
						'---',
						'# Building a Self-Hosted Homelab Dashboard',
						'',
						'## Intro',
						'I wanted a single pane of glass for my homelab — system stats, security alerts,',
						'AI chat, and notes. Dark terminal UI, fully self-hosted.',
						'',
						'## Stack',
						'- **Frontend**: SvelteKit + TypeScript',
						'- **Backend**: FastAPI (Python)',
						'- **AI**: Ollama on LOQ laptop (RTX 5060)',
						'- **Deploy**: Docker Compose on Ubuntu Server',
						'',
						'## Main',
						'',
						'### Why SvelteKit?',
						'Reactive by default, tiny bundle, no VDOM overhead. Perfect for a dashboard',
						'that polls data every 10 seconds.',
						'',
						'### Ollama Setup',
						'The RTX 5060 runs `qwen3.5:9b` at ~35 t/s. Fast enough for real-time chat.',
						'Exposed on `0.0.0.0:11434` so the lab server can reach it.',
						'',
						'```powershell',
						'$env:OLLAMA_HOST = "0.0.0.0:11434"',
						'ollama serve',
						'```',
						'',
						'## Conclusion',
						'_[TODO: write after polishing the UI]_',
					),
					type: 'md', created: now - day * 6, modified: now - day * 1,
				},
				'_Templates/THM Room.md': {
					path: '_Templates/THM Room.md',
					content: j(
						'---',
						'date: ',
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
					type: 'md', created: now - day * 60, modified: now - day * 60,
				},
				'_Templates/Tool.md': {
					path: '_Templates/Tool.md',
					content: j(
						'---',
						'date: ',
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
					type: 'md', created: now - day * 60, modified: now - day * 60,
				},
				'_Templates/Blog Draft.md': {
					path: '_Templates/Blog Draft.md',
					content: j(
						'---',
						'date: ',
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
					type: 'md', created: now - day * 60, modified: now - day * 60,
				},
			},
		},
		uni: {
			id: 'uni',
			name: 'Uni vault',
			files: {
				'000_Index/index.md': {
					path: '000_Index/index.md',
					content: j(
						'---',
						'date: 2026-02-10',
						'tags: [index]',
						'---',
						'# Course Index',
						'',
						'## Modules',
						'- [[001_PFA1-11/lecture-01|PFA1]] — Programming Fundamentals',
						'- [[002_CNA1-12/lecture-01|CNA1]] — Computer Networks',
						'',
						'## Upcoming',
						'- [ ] PFA1 Assignment 2 — due 2026-06-20',
						'- [ ] CNA1 Lab report — due 2026-06-18',
						'- [x] Register for exam period',
					),
					type: 'md', created: now - day * 120, modified: now - day * 3,
				},
				'001_PFA1-11/lecture-01.md': {
					path: '001_PFA1-11/lecture-01.md',
					content: j(
						'---',
						'date: 2026-02-10',
						'module: PFA1',
						'tags: [pfa1, lecture, programming]',
						'---',
						'# Lecture 1: Introduction to Programming',
						'',
						'## References',
						'- Textbook: *Programming in C* — Kernighan & Ritchie',
						'- [CS50x](https://cs50.harvard.edu/x/)',
						'',
						'## Class Notes',
						'',
						'### Variables',
						'```c',
						'int age = 20;',
						'float gpa = 3.8;',
						'char grade = \'A\';',
						'```',
						'',
						'### Control Flow',
						'```c',
						'if (age >= 18) {',
						'    printf("Adult\\n");',
						'} else {',
						'    printf("Minor\\n");',
						'}',
						'',
						'for (int i = 0; i < 10; i++) {',
						'    printf("%d\\n", i);',
						'}',
						'```',
						'',
						'> Exam: know the difference between `==` (compare) and `=` (assign).',
					),
					type: 'md', created: now - day * 120, modified: now - day * 118,
				},
				'002_CNA1-12/lecture-01.md': {
					path: '002_CNA1-12/lecture-01.md',
					content: j(
						'---',
						'date: 2026-02-12',
						'module: CNA1',
						'tags: [cna1, lecture, networking]',
						'---',
						'# Lecture 1: Introduction to Computer Networks',
						'',
						'## References',
						'- Textbook: *Computer Networks* — Tanenbaum',
						'- See also: [[000_Index/index]]',
						'',
						'## Class Notes',
						'',
						'### Network Types',
						'',
						'| Type | Range | Example |',
						'|------|-------|---------|',
						'| PAN | ~1m | Bluetooth |',
						'| LAN | Building | Office WiFi |',
						'| MAN | City | Metro fiber |',
						'| WAN | Global | Internet |',
						'',
						'### Protocols',
						'A set of rules for communication:',
						'- **HTTP** — web browsing (port 80/443)',
						'- **TCP** — reliable, ordered delivery',
						'- **UDP** — fast, unreliable (streaming)',
						'',
						'See [[../../10 Learning/Networking/osi-model]] for OSI breakdown.',
					),
					type: 'md', created: now - day * 118, modified: now - day * 116,
				},
				'998_Calendar_Notes/2026-06-07.md': {
					path: '998_Calendar_Notes/2026-06-07.md',
					content: j(
						'---',
						'date: 2026-06-07',
						'tags: [daily]',
						'---',
						'# 2026-06-07',
						'',
						'## Today',
						'- [x] Work on dashboard notes system',
						'- [ ] Study for CNA1 exam',
						'- [ ] Review PFA1 assignment',
						'',
						'## Notes',
						'Dashboard coming along. Deploying to lab server.',
					),
					type: 'md', created: now, modified: now,
				},
				'999_Templates/Lecture.md': {
					path: '999_Templates/Lecture.md',
					content: j(
						'---',
						'date: ',
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
					type: 'md', created: now - day * 120, modified: now - day * 120,
				},
			},
		},
	};
}
