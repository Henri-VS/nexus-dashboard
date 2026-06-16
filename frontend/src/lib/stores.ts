import { browser } from '$app/environment';
import { writable } from 'svelte/store';

// ── NexusSettings ─────────────────────────────────────────────────────────────

export interface NexusSettings {
	sidebarPosition: 'left' | 'right';
	compactMode: boolean;
	location: {
		city: string;
		lat:  string;
		lon:  string;
	};
	ai: {
		defaultModel: string;
		systemPrompt: string;
		ollamaHost: string;
	};
	ntfy: {
		topic: string;
		server: string;
	};
}

const NEXUS_KEY = 'nexus_settings';

export const DEFAULT_NEXUS: NexusSettings = {
	sidebarPosition: 'left',
	compactMode: false,
	location: { city: '', lat: '', lon: '' },
	ai: {
		defaultModel: 'qwen3.5:9b',
		systemPrompt: '',
		ollamaHost: 'http://localhost:11434',
	},
	ntfy: {
		topic: '',
		server: 'https://ntfy.sh',
	},
};

function loadNexus(): NexusSettings {
	if (!browser) return { ...DEFAULT_NEXUS, ai: { ...DEFAULT_NEXUS.ai }, ntfy: { ...DEFAULT_NEXUS.ntfy } };
	try {
		const raw = localStorage.getItem(NEXUS_KEY);
		if (!raw) return { ...DEFAULT_NEXUS, ai: { ...DEFAULT_NEXUS.ai }, ntfy: { ...DEFAULT_NEXUS.ntfy } };
		const parsed = JSON.parse(raw) as Partial<NexusSettings>;
		return {
			...DEFAULT_NEXUS,
			...parsed,
			location: { ...DEFAULT_NEXUS.location, ...(parsed.location ?? {}) },
			ai:       { ...DEFAULT_NEXUS.ai,        ...(parsed.ai       ?? {}) },
			ntfy:     { ...DEFAULT_NEXUS.ntfy,      ...(parsed.ntfy     ?? {}) },
		};
	} catch {
		return { ...DEFAULT_NEXUS, ai: { ...DEFAULT_NEXUS.ai }, ntfy: { ...DEFAULT_NEXUS.ntfy } };
	}
}

const _nexusInitial = loadNexus();

function createNexusSettingsStore() {
	const { subscribe, update, set: _set } = writable<NexusSettings>(_nexusInitial);

	function save(v: NexusSettings) {
		if (browser) {
			try { localStorage.setItem(NEXUS_KEY, JSON.stringify(v)); } catch { /* storage full */ }
		}
	}

	return {
		subscribe,

		patch(partial: {
			sidebarPosition?: 'left' | 'right';
			compactMode?: boolean;
			location?: Partial<NexusSettings['location']>;
			ai?: Partial<NexusSettings['ai']>;
			ntfy?: Partial<NexusSettings['ntfy']>;
		}) {
			update((v) => {
				const next: NexusSettings = {
					...v,
					...(partial.sidebarPosition !== undefined ? { sidebarPosition: partial.sidebarPosition } : {}),
					...(partial.compactMode     !== undefined ? { compactMode: partial.compactMode }         : {}),
					location: { ...v.location, ...(partial.location ?? {}) },
					ai:       { ...v.ai,       ...(partial.ai       ?? {}) },
					ntfy:     { ...v.ntfy,     ...(partial.ntfy     ?? {}) },
				};
				save(next);
				return next;
			});
		},

		importJson(json: string) {
			const parsed = JSON.parse(json) as Partial<NexusSettings>;
			const merged: NexusSettings = {
				...DEFAULT_NEXUS,
				...parsed,
				location: { ...DEFAULT_NEXUS.location, ...(parsed.location ?? {}) },
				ai:       { ...DEFAULT_NEXUS.ai,        ...(parsed.ai       ?? {}) },
				ntfy:     { ...DEFAULT_NEXUS.ntfy,      ...(parsed.ntfy     ?? {}) },
			};
			_set(merged);
			save(merged);
		},

		reset() {
			const fresh: NexusSettings = {
				...DEFAULT_NEXUS,
				ai:   { ...DEFAULT_NEXUS.ai },
				ntfy: { ...DEFAULT_NEXUS.ntfy },
			};
			_set(fresh);
			save(fresh);
		},
	};
}

export const nexusSettings = createNexusSettingsStore();

// ── Pending AI context (set by resources page, consumed by ai page) ───────────

export interface PendingAiContext {
	filename: string;
	subject: string;
	text: string;
}

export const pendingAiContext = writable<PendingAiContext | null>(null);

// ── Other stores ──────────────────────────────────────────────────────────────

/** Currently selected Ollama model — initialized from nexus_settings on load */
export const selectedModel = writable<string>(_nexusInitial.ai.defaultModel);

/** Controls the Ctrl+Space AI overlay */
export const overlayOpen = writable<boolean>(false);

/** Pre-fills the overlay input (set by quick-bar before opening overlay) */
export const overlayPrefill = writable<string>('');

/** When true the overlay auto-submits its prefill on open (set by quick-bar Enter/Ask) */
export const overlayAutoSend = writable<boolean>(false);
