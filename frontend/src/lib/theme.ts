import { browser } from '$app/environment';
import { writable } from 'svelte/store';

// ── Types ─────────────────────────────────────────────────────

export interface Theme {
	id: string;
	label: string;
	/** Maps CSS custom property name → value, e.g. '--bg0': '#0d1117' */
	vars: Record<string, string>;
}

// ── Preset themes ─────────────────────────────────────────────

export const themes: Theme[] = [
	{
		id: 'terminal',
		label: 'Terminal',
		vars: {
			'--bg0':    '#0d1117',
			'--bg1':    '#161b22',
			'--bg2':    '#21262d',
			'--bg3':    '#2d333b',
			'--border': '#30363d',
			'--text0':  '#e6edf3',
			'--text1':  '#8b949e',
			'--text2':  '#484f58',
			'--red':    '#f85149',
			'--yellow': '#e3b341',
			'--green':  '#3fb950',
			'--teal':   '#2bbc8a',
			'--accent':  '#3fb950',
			'--accent2': '#58a6ff',
			'--accent3': '#bc8cff',
			'--accent4': '#f78166',
		},
	},
	{
		id: 'nord',
		label: 'Nord',
		vars: {
			'--bg0':    '#2e3440',
			'--bg1':    '#3b4252',
			'--bg2':    '#434c5e',
			'--bg3':    '#4c566a',
			'--border': '#4c566a',
			'--text0':  '#eceff4',
			'--text1':  '#d8dee9',
			'--text2':  '#7b889a',
			'--red':    '#bf616a',
			'--yellow': '#ebcb8b',
			'--green':  '#a3be8c',
			'--teal':   '#8fbcbb',
			'--accent':  '#88c0d0',
			'--accent2': '#81a1c1',
			'--accent3': '#b48ead',
			'--accent4': '#d08770',
		},
	},
	{
		id: 'catppuccin',
		label: 'Catppuccin',
		vars: {
			'--bg0':    '#1e1e2e',
			'--bg1':    '#181825',
			'--bg2':    '#313244',
			'--bg3':    '#45475a',
			'--border': '#45475a',
			'--text0':  '#cdd6f4',
			'--text1':  '#bac2de',
			'--text2':  '#6c7086',
			'--red':    '#f38ba8',
			'--yellow': '#f9e2af',
			'--green':  '#a6e3a1',
			'--teal':   '#94e2d5',
			'--accent':  '#cba6f7',
			'--accent2': '#89b4fa',
			'--accent3': '#f5c2e7',
			'--accent4': '#fab387',
		},
	},
	{
		id: 'light',
		label: 'Light',
		vars: {
			'--bg0':    '#ffffff',
			'--bg1':    '#f6f8fa',
			'--bg2':    '#eaeef2',
			'--bg3':    '#d0d7de',
			'--border': '#d0d7de',
			'--text0':  '#1f2328',
			'--text1':  '#656d76',
			'--text2':  '#9198a1',
			'--red':    '#d1242f',
			'--yellow': '#9a6700',
			'--green':  '#1a7f37',
			'--teal':   '#0969da',
			'--accent':  '#1a7f37',
			'--accent2': '#0969da',
			'--accent3': '#8250df',
			'--accent4': '#bc4c00',
		},
	},
	{
		id: 'embers',
		label: 'Embers',
		vars: {
			'--bg0':    '#0f0e17',
			'--bg1':    '#1a1825',
			'--bg2':    '#241f35',
			'--bg3':    '#2e2845',
			'--border': '#2e2845',
			'--text0':  '#fffffe',
			'--text1':  '#a7a9be',
			'--text2':  '#5c5f7a',
			'--red':    '#ff6b6b',
			'--yellow': '#ffd166',
			'--green':  '#06d6a0',
			'--teal':   '#06d6a0',
			'--accent':  '#ff6b6b',
			'--accent2': '#ff8c42',
			'--accent3': '#ffd166',
			'--accent4': '#c77dff',
		},
	},
	{
		id: 'starry-night',
		label: 'Starry Night',
		vars: {
			'--bg0':    '#0a0e1a',
			'--bg1':    '#0d1220',
			'--bg2':    '#111827',
			'--bg3':    '#1a2235',
			'--border': '#1e293b',
			'--text0':  '#e2e8f0',
			'--text1':  '#94a3b8',
			'--text2':  '#475569',
			'--red':    '#f87171',
			'--yellow': '#c6f135',
			'--green':  '#39d353',
			'--teal':   '#22d3ee',
			'--accent':  '#c6f135',
			'--accent2': '#39d353',
			'--accent3': '#c6f135',
			'--accent4': '#818cf8',
		},
	},
	{
		id: 'hacker-red',
		label: 'Hacker Red',
		vars: {
			'--bg0':    '#000000',
			'--bg1':    '#0a0a0a',
			'--bg2':    '#111111',
			'--bg3':    '#1a1a1a',
			'--border': '#222222',
			'--text0':  '#ffffff',
			'--text1':  '#888888',
			'--text2':  '#444444',
			'--red':    '#ff0040',
			'--yellow': '#ff6600',
			'--green':  '#00ff41',
			'--teal':   '#00ff41',
			'--accent':  '#ff0040',
			'--accent2': '#ff4444',
			'--accent3': '#ff6600',
			'--accent4': '#cc0033',
		},
	},
	{
		id: 'ocean-dark',
		label: 'Ocean Dark',
		vars: {
			'--bg0':    '#020b18',
			'--bg1':    '#041428',
			'--bg2':    '#071e38',
			'--bg3':    '#0a2848',
			'--border': '#0a2848',
			'--text0':  '#e0f4ff',
			'--text1':  '#7eb8d4',
			'--text2':  '#3a6b8a',
			'--red':    '#ff6b6b',
			'--yellow': '#ffd166',
			'--green':  '#00ff88',
			'--teal':   '#00d4ff',
			'--accent':  '#00d4ff',
			'--accent2': '#00ff88',
			'--accent3': '#0099cc',
			'--accent4': '#7c3aed',
		},
	},
];

// ── Apply to DOM ──────────────────────────────────────────────

function applyTheme(vars: Record<string, string>): void {
	if (!browser) return;
	const root = document.documentElement;
	for (const [prop, val] of Object.entries(vars)) {
		root.style.setProperty(prop, val);
	}
}

// ── Store factory ─────────────────────────────────────────────

const STORAGE_KEY = 'dashboard-theme';

function createThemeStore() {
	// Read persisted preference; fall back to terminal
	const storedId = browser ? localStorage.getItem(STORAGE_KEY) : null;
	const initial = themes.find((t) => t.id === storedId) ?? themes[0];

	// Apply immediately so there's no flash of default vars on load
	applyTheme(initial.vars);

	const { subscribe, set: _set } = writable<Theme>(initial);

	return {
		subscribe,

		/** Switch to a theme object and persist the choice. */
		set(t: Theme): void {
			applyTheme(t.vars);
			if (browser) localStorage.setItem(STORAGE_KEY, t.id);
			_set(t);
		},

		/** Convenience: switch by id string. No-op if id is unknown. */
		setById(id: string): void {
			const t = themes.find((th) => th.id === id);
			if (t) this.set(t);
		},
	};
}

export const theme = createThemeStore();
