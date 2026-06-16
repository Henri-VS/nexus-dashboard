import { browser } from '$app/environment';
import { derived, writable } from 'svelte/store';

// ── Types ─────────────────────────────────────────────────────────────────

export interface WidgetSettings {
	// Common (all widgets)
	customTitle?: string;
	accentOverride?: string;
	// Weather
	locationName?: string;
	lat?: number;
	lon?: number;
	units?: 'C' | 'F';
	windUnit?: 'kts' | 'kmh';
	// System
	pollInterval?: number;
	showCpu?: boolean;
	showMemory?: boolean;
	showDisk?: boolean;
	showNetwork?: boolean;
	// Security
	maxAlerts?: number;
	severityFilter?: string;
	// Docker
	dockerPollInterval?: number;
	showExited?: boolean;
	// Learning
	certs?: string[];
	thmUsername?: string;
	// Home
	entities?: string[];
	// Notes
	previewVault?: string;
}

export interface WidgetItem {
	id: string;
	enabled: boolean;
	size: 1 | 2 | 3;
	height: number;
	settings: WidgetSettings;
}

export interface DashConfig {
	widgets: WidgetItem[];
	themeId: string;
	accentOverride: string | null;
	fontSize: number; // 12–18
	columns: 2 | 3 | 4;
	currentLayoutId: string | null;
}

// ── Widget registry ────────────────────────────────────────────────────────

export type WidgetId = 'weather' | 'system' | 'security' | 'docker' | 'notes' | 'learning' | 'home' | 'calendar' | 'pomodoro' | 'news' | 'quicklinks' | 'heartbeat' | 'logs';

export interface LayoutPreset {
	id:          string;
	name:        string;
	description: string;
	columns:     2 | 3 | 4;
	icon:        string;
	widgets: Array<{
		id: WidgetId;
		enabled: boolean;
		size: 1 | 2 | 3;
		height: number;
	}>;
}

export const WIDGET_DEFS: Array<{
	id: WidgetId;
	label: string;
	icon: string;
	defaultSize: 1 | 2 | 3;
	defaultHeight: number;
	defaultEnabled: boolean;
}> = [
	{ id: 'weather',    label: 'Weather',     icon: '🌤', defaultSize: 2, defaultHeight: 340, defaultEnabled: true },
	{ id: 'system',     label: 'System',      icon: '💻', defaultSize: 2, defaultHeight: 520, defaultEnabled: true },
	{ id: 'security',   label: 'Security',    icon: '🔒', defaultSize: 2, defaultHeight: 340, defaultEnabled: true },
	{ id: 'docker',     label: 'Docker',      icon: '🐳', defaultSize: 2, defaultHeight: 340, defaultEnabled: true },
	{ id: 'notes',      label: 'Notes',       icon: '📝', defaultSize: 1, defaultHeight: 340, defaultEnabled: true },
	{ id: 'learning',   label: 'Learning',    icon: '📚', defaultSize: 1, defaultHeight: 340, defaultEnabled: true },
	{ id: 'home',       label: 'Home',        icon: '🏠', defaultSize: 2, defaultHeight: 340, defaultEnabled: true },
	{ id: 'calendar',   label: 'Calendar',    icon: '📅', defaultSize: 1, defaultHeight: 340, defaultEnabled: true },
	{ id: 'pomodoro',   label: 'Pomodoro',    icon: '🍅', defaultSize: 1, defaultHeight: 220, defaultEnabled: true },
	{ id: 'news',       label: 'News',        icon: '📰', defaultSize: 3, defaultHeight: 340, defaultEnabled: true },
	{ id: 'quicklinks', label: 'Quick Links', icon: '🔗', defaultSize: 1, defaultHeight: 220, defaultEnabled: true },
	{ id: 'heartbeat',  label: 'Heartbeat',   icon: '💓', defaultSize: 2, defaultHeight: 520, defaultEnabled: true },
	{ id: 'logs',       label: 'Logs',        icon: '📋', defaultSize: 3, defaultHeight: 340, defaultEnabled: true },
];

export const LAYOUT_PRESETS: LayoutPreset[] = [
	{
		id:          'overview',
		name:        'Overview',
		description: 'Everything at a glance — all widgets, balanced layout.',
		columns:     3,
		icon:        '◻',
		widgets: [
			{ id: 'weather',    enabled: true,  size: 2, height: 340 },
			{ id: 'system',     enabled: true,  size: 2, height: 520 },
			{ id: 'security',   enabled: true,  size: 2, height: 340 },
			{ id: 'docker',     enabled: true,  size: 2, height: 340 },
			{ id: 'notes',      enabled: true,  size: 1, height: 340 },
			{ id: 'learning',   enabled: true,  size: 1, height: 340 },
			{ id: 'home',       enabled: true,  size: 2, height: 340 },
			{ id: 'calendar',   enabled: true,  size: 1, height: 340 },
			{ id: 'pomodoro',   enabled: true,  size: 1, height: 220 },
			{ id: 'quicklinks', enabled: true,  size: 1, height: 220 },
			{ id: 'news',       enabled: true,  size: 3, height: 340 },
			{ id: 'heartbeat',  enabled: true,  size: 2, height: 520 },
			{ id: 'logs',       enabled: true,  size: 3, height: 340 },
		],
	},
	{
		id:          'security',
		name:        'Security Ops',
		description: 'Security-first layout. Threats, containers, and system health.',
		columns:     3,
		icon:        '⬛',
		widgets: [
			{ id: 'security',   enabled: true,  size: 2, height: 520 },
			{ id: 'system',     enabled: true,  size: 2, height: 340 },
			{ id: 'docker',     enabled: true,  size: 2, height: 340 },
			{ id: 'heartbeat',  enabled: true,  size: 2, height: 520 },
			{ id: 'logs',       enabled: true,  size: 3, height: 400 },
			{ id: 'weather',    enabled: true,  size: 1, height: 220 },
			{ id: 'quicklinks', enabled: true,  size: 1, height: 220 },
			{ id: 'news',       enabled: true,  size: 3, height: 340 },
			{ id: 'notes',      enabled: false, size: 1, height: 340 },
			{ id: 'learning',   enabled: false, size: 1, height: 340 },
			{ id: 'home',       enabled: false, size: 2, height: 340 },
			{ id: 'calendar',   enabled: false, size: 1, height: 340 },
			{ id: 'pomodoro',   enabled: false, size: 1, height: 220 },
		],
	},
	{
		id:          'minimal',
		name:        'Minimal',
		description: 'Clean and focused. Just the essentials.',
		columns:     2,
		icon:        '▫',
		widgets: [
			{ id: 'weather',    enabled: true,  size: 1, height: 340 },
			{ id: 'system',     enabled: true,  size: 2, height: 340 },
			{ id: 'calendar',   enabled: true,  size: 1, height: 340 },
			{ id: 'quicklinks', enabled: true,  size: 1, height: 220 },
			{ id: 'pomodoro',   enabled: true,  size: 1, height: 220 },
			{ id: 'notes',      enabled: true,  size: 2, height: 340 },
			{ id: 'security',   enabled: false, size: 2, height: 340 },
			{ id: 'docker',     enabled: false, size: 2, height: 340 },
			{ id: 'learning',   enabled: false, size: 1, height: 340 },
			{ id: 'home',       enabled: false, size: 2, height: 340 },
			{ id: 'news',       enabled: false, size: 3, height: 340 },
			{ id: 'heartbeat',  enabled: false, size: 2, height: 520 },
			{ id: 'logs',       enabled: false, size: 3, height: 340 },
		],
	},
	{
		id:          'developer',
		name:        'Developer',
		description: 'Containers, logs, and system resources front and center.',
		columns:     3,
		icon:        '▣',
		widgets: [
			{ id: 'docker',     enabled: true,  size: 2, height: 520 },
			{ id: 'system',     enabled: true,  size: 2, height: 520 },
			{ id: 'logs',       enabled: true,  size: 3, height: 400 },
			{ id: 'heartbeat',  enabled: true,  size: 2, height: 340 },
			{ id: 'quicklinks', enabled: true,  size: 1, height: 220 },
			{ id: 'security',   enabled: true,  size: 2, height: 340 },
			{ id: 'weather',    enabled: true,  size: 1, height: 220 },
			{ id: 'notes',      enabled: true,  size: 1, height: 340 },
			{ id: 'news',       enabled: false, size: 3, height: 340 },
			{ id: 'home',       enabled: false, size: 2, height: 340 },
			{ id: 'learning',   enabled: false, size: 1, height: 340 },
			{ id: 'calendar',   enabled: false, size: 1, height: 340 },
			{ id: 'pomodoro',   enabled: false, size: 1, height: 220 },
		],
	},
	{
		id:          'homelab',
		name:        'Homelab',
		description: 'Services, home automation, and media. Homarr-style.',
		columns:     3,
		icon:        '⬜',
		widgets: [
			{ id: 'home',       enabled: true,  size: 2, height: 340 },
			{ id: 'weather',    enabled: true,  size: 1, height: 220 },
			{ id: 'quicklinks', enabled: true,  size: 1, height: 220 },
			{ id: 'docker',     enabled: true,  size: 2, height: 340 },
			{ id: 'heartbeat',  enabled: true,  size: 2, height: 340 },
			{ id: 'calendar',   enabled: true,  size: 1, height: 340 },
			{ id: 'news',       enabled: true,  size: 3, height: 340 },
			{ id: 'system',     enabled: true,  size: 2, height: 340 },
			{ id: 'notes',      enabled: true,  size: 1, height: 340 },
			{ id: 'security',   enabled: false, size: 2, height: 340 },
			{ id: 'learning',   enabled: false, size: 1, height: 340 },
			{ id: 'pomodoro',   enabled: false, size: 1, height: 220 },
			{ id: 'logs',       enabled: false, size: 3, height: 340 },
		],
	},
];

// ── Defaults ───────────────────────────────────────────────────────────────

export const DEFAULT_CONFIG: DashConfig = {
	widgets: WIDGET_DEFS.map((w) => ({
		id: w.id,
		enabled: w.defaultEnabled,
		size: w.defaultSize,
		height: w.defaultHeight,
		settings: {},
	})),
	themeId: 'terminal',
	accentOverride: null,
	fontSize: 14,
	columns: 3,
	currentLayoutId: 'overview',
};

const STORAGE_KEY = 'dashboard_config';

// ── Persistence helpers ────────────────────────────────────────────────────

function load(): DashConfig {
	if (!browser) return { ...DEFAULT_CONFIG };
	try {
		const raw = localStorage.getItem(STORAGE_KEY);
		if (!raw) return { ...DEFAULT_CONFIG };
		const parsed: any = JSON.parse(raw);

		const savedWidgets: any[] = parsed.widgets ?? [];
		const savedMap = new Map(savedWidgets.map((w: any) => [w.id, w]));

		const savedOrdered = savedWidgets
			.filter((w: any) => WIDGET_DEFS.some((d) => d.id === w.id))
			.map((w: any): WidgetItem => {
				// Convert from preset format if stored in the previous implementation
				let size: 1 | 2 | 3 = (w.size ?? 1) as 1 | 2 | 3;
				let height: number = w.height ?? 340;
				if (typeof w.preset === 'string') {
					const fromPreset: Record<string, { size: 1|2|3; height: number }> = {
						S: { size: 1, height: 220 },
						M: { size: 1, height: 340 },
						W: { size: 2, height: 340 },
						L: { size: 2, height: 520 },
						F: { size: 3, height: 340 },
					};
					const mapped = fromPreset[w.preset];
					if (mapped) { size = mapped.size; height = mapped.height; }
				}
				return { id: w.id, enabled: w.enabled ?? true, size, height, settings: w.settings ?? {} };
			});

		const newWidgets = WIDGET_DEFS
			.filter((d) => !savedMap.has(d.id))
			.map((d): WidgetItem => ({
				id: d.id,
				enabled: d.defaultEnabled,
				size: d.defaultSize,
				height: d.defaultHeight,
				settings: {},
			}));

		return {
			...DEFAULT_CONFIG,
			themeId:         parsed.themeId         ?? DEFAULT_CONFIG.themeId,
			accentOverride:  parsed.accentOverride   ?? DEFAULT_CONFIG.accentOverride,
			fontSize:        parsed.fontSize         ?? DEFAULT_CONFIG.fontSize,
			columns:         parsed.columns          ?? DEFAULT_CONFIG.columns,
			currentLayoutId: parsed.currentLayoutId  ?? null,
			widgets: [...savedOrdered, ...newWidgets],
		};
	} catch {
		return { ...DEFAULT_CONFIG };
	}
}

function persist(cfg: DashConfig) {
	if (!browser) return;
	try { localStorage.setItem(STORAGE_KEY, JSON.stringify(cfg)); } catch { /* full */ }
}

function applyToDom(cfg: DashConfig) {
	if (!browser) return;
	document.documentElement.style.fontSize = `${cfg.fontSize}px`;
	if (cfg.accentOverride) {
		document.documentElement.style.setProperty('--accent', cfg.accentOverride);
	} else {
		document.documentElement.style.removeProperty('--accent');
	}
}

// ── Store ─────────────────────────────────────────────────────────────────

function createDashConfigStore() {
	let current: DashConfig = load();
	applyToDom(current);

	const { subscribe, update, set } = writable<DashConfig>(current);

	// Keep `current` in sync for exportJson
	subscribe((v) => { current = v; });

	const store = {
		subscribe,

		updateWidget(id: string, changes: Partial<WidgetItem>) {
			update((cfg) => {
				const next = {
					...cfg,
					currentLayoutId: null,
					widgets: cfg.widgets.map((w) => (w.id === id ? { ...w, ...changes } : w)),
				};
				persist(next);
				return next;
			});
		},

		updateWidgetSettings(id: string, settings: Partial<WidgetSettings>) {
			update((cfg) => {
				const next = {
					...cfg,
					widgets: cfg.widgets.map((w) =>
						w.id === id ? { ...w, settings: { ...w.settings, ...settings } } : w,
					),
				};
				persist(next);
				return next;
			});
		},

		applyLayoutPreset(presetId: string) {
			const preset = LAYOUT_PRESETS.find((p) => p.id === presetId);
			if (!preset) return;
			update((cfg) => {
				const oldSettings = Object.fromEntries(cfg.widgets.map((w) => [w.id, w.settings]));
				const presetWidgets = preset.widgets.map((pw) => ({
					id:       pw.id,
					enabled:  pw.enabled,
					size:     pw.size,
					height:   pw.height,
					settings: oldSettings[pw.id] ?? {},
				}));
				const presetIds = new Set<string>(preset.widgets.map((w) => w.id));
				const extras = cfg.widgets
					.filter((w) => !presetIds.has(w.id))
					.map((w) => ({ ...w, enabled: false }));
				const next = {
					...cfg,
					columns:         preset.columns,
					currentLayoutId: presetId,
					widgets:         [...presetWidgets, ...extras],
				};
				persist(next);
				return next;
			});
		},

		setTheme(themeId: string) {
			update((cfg) => {
				const next = { ...cfg, themeId };
				persist(next);
				return next;
			});
		},

		setAccentOverride(color: string | null) {
			update((cfg) => {
				const next = { ...cfg, accentOverride: color };
				persist(next);
				applyToDom(next);
				return next;
			});
		},

		setFontSize(size: number) {
			update((cfg) => {
				const next = { ...cfg, fontSize: size };
				persist(next);
				applyToDom(next);
				return next;
			});
		},

		setColumns(cols: 2 | 3 | 4) {
			update((cfg) => {
				const next = { ...cfg, columns: cols };
				persist(next);
				return next;
			});
		},

		exportJson(): string {
			return JSON.stringify(current, null, 2);
		},

		importJson(json: string) {
			const parsed = JSON.parse(json) as DashConfig; // throws on bad input — caller handles
			set(parsed);
			persist(parsed);
			applyToDom(parsed);
		},

		reset() {
			const fresh = { ...DEFAULT_CONFIG };
			set(fresh);
			persist(fresh);
			applyToDom(fresh);
		},
	};

	return store;
}

export const dashConfig = createDashConfigStore();

/** Derived: only the enabled widgets in their configured order */
export const activeWidgets = derived(dashConfig, ($cfg) =>
	$cfg.widgets.filter((w) => w.enabled),
);

/** Widget settings overlay — shows gear icon on each widget when true */
export const editMode = writable(false);

/** Clears all per-page layout preferences saved under dashboard_config.* */
export function resetAllPageConfigs() {
	if (typeof localStorage === 'undefined') return;
	const keys = Object.keys(localStorage).filter((k) => k.startsWith('dashboard_config.'));
	for (const k of keys) localStorage.removeItem(k);
}
