import type {
	WeatherData,
	SystemData,
	SecurityAlert,
	NoteFile,
	ContainerStatus,
	LearningData,
	HomeEntity,
} from '$lib/types';

export const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8088';

export const EXCALIDRAW_URL = import.meta.env.PUBLIC_EXCALIDRAW_URL ?? 'http://localhost:3002';

// Returns null on any failure — widgets handle the fallback to mock data.
async function get<T>(path: string): Promise<T | null> {
	try {
		const res = await fetch(`${BASE}${path}`, { credentials: 'include' });
		if (!res.ok) return null;
		return res.json() as Promise<T>;
	} catch {
		return null;
	}
}

async function post<T>(path: string, body: unknown): Promise<T | null> {
	try {
		const res = await fetch(`${BASE}${path}`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			credentials: 'include',
			body: JSON.stringify(body),
		});
		if (!res.ok) return null;
		return res.json() as Promise<T>;
	} catch {
		return null;
	}
}

async function put<T>(path: string, body: unknown): Promise<T | null> {
	try {
		const res = await fetch(`${BASE}${path}`, {
			method: 'PUT',
			headers: { 'Content-Type': 'application/json' },
			credentials: 'include',
			body: JSON.stringify(body),
		});
		if (!res.ok) return null;
		return res.json() as Promise<T>;
	} catch {
		return null;
	}
}

async function del<T>(path: string): Promise<T | null> {
	try {
		const res = await fetch(`${BASE}${path}`, {
			method: 'DELETE',
			credentials: 'include',
		});
		if (!res.ok) return null;
		return res.json() as Promise<T>;
	} catch {
		return null;
	}
}

async function patch<T>(path: string): Promise<T | null> {
	try {
		const res = await fetch(`${BASE}${path}`, {
			method: 'PATCH',
			credentials: 'include',
		});
		if (!res.ok) return null;
		return res.json() as Promise<T>;
	} catch {
		return null;
	}
}

// ── Auth ──────────────────────────────────────────────────────
export const auth = {
	verify: (key: string) =>
		fetch(`${BASE}/api/auth/verify`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			credentials: 'include',
			body: JSON.stringify({ key }),
		}),
	logout: async () => {
		await fetch(`${BASE}/api/auth/logout`, {
			method: 'POST',
			credentials: 'include',
		});
	},
};

// ── Heartbeat ─────────────────────────────────────────────────
export interface HBHost {
	id?:   string;
	name:  string;
	url:   string;
	auto:  boolean;
}

export const heartbeat = {
	status:     () => get<{ services: Record<string, unknown>; last_summary: string; fetched_at: string }>('/api/heartbeat/status'),
	hosts:      () => get<{ hosts: HBHost[] }>('/api/heartbeat/hosts'),
	addHost:    (name: string, url: string) => post<{ ok: boolean; id: string }>('/api/heartbeat/hosts', { name, url }),
	removeHost: (id: string)               => del<{ ok: boolean }>(`/api/heartbeat/hosts/${id}`),
};

// ── Service catalog ──────────────────────────────────────────
export interface Service {
	id: string;
	name: string;
	url: string;
	category: string;
	icon: string;
	description: string;
	enabled: boolean;
}

export const services = {
	list:    ()                                     => get<{ services: Service[] }>('/api/services'),
	create:  (s: Omit<Service, 'id'>)              => post<Service>('/api/services', s),
	update:  (id: string, s: Omit<Service, 'id'>)  => put<Service>(`/api/services/${id}`, s),
	delete:  (id: string)                           => del<{ ok: boolean }>(`/api/services/${id}`),
	reorder: (ids: string[])                        => post<{ ok: boolean }>('/api/services/reorder', { ids }),
	ping:    (url: string)                          => get<{ online: boolean; latency_ms: number | null }>(`/api/services/ping?url=${encodeURIComponent(url)}`),
};

// ── Weather ───────────────────────────────────────────────────
export const weather = {
	current: () => get<WeatherData>('/api/weather/current'),
};

// ── System ────────────────────────────────────────────────────
export const system = {
	stats: () => get<SystemData>('/api/system/stats'),
};

// ── Security ──────────────────────────────────────────────────
export const security = {
	alerts: () => get<{ live: boolean; alerts: SecurityAlert[] }>('/api/security/alerts'),
};

// ── Docker ────────────────────────────────────────────────────
export const docker = {
	containers: () => get<{ docker_unavailable: boolean; containers: ContainerStatus[] }>('/api/docker/containers'),
};

// ── Notes ─────────────────────────────────────────────────────
export const notes = {
	recent:  ()           => get<NoteFile[]>('/api/notes/recent'),
	file:    (path: string) => get<NoteFile>(`/api/notes/file?path=${encodeURIComponent(path)}`),
};

// ── Home Assistant ────────────────────────────────────────────
export const homeAssistant = {
	entities:    ()                                                => get<HomeEntity[]>('/api/home/entities'),
	callService: (domain: string, service: string, data: unknown) =>
		post('/api/home/service', { domain, service, data }),
};

// ── Learning ──────────────────────────────────────────────────
export const learn = {
	progress: () => get<LearningData>('/api/learn/progress'),
};

// ── Resources ─────────────────────────────────────────────────
export const resources = {
	process: (data: {
		filename: string;
		content: string;
		file_type: string;
		subject?: string;
		semester?: string;
	}) =>
		post<{ status: string; chunks: number; filename: string; text: string }>(
			'/api/resources/process',
			data,
		),
	search: (q: string, subject?: string, n = 5) =>
		get<{
			query: string;
			chunks: Array<{ content: string; metadata: Record<string, string>; score: number }>;
		}>(
			`/api/resources/search?q=${encodeURIComponent(q)}${subject ? `&subject=${encodeURIComponent(subject)}` : ''}&n=${n}`,
		),
};

// ── News feeds ───────────────────────────────────────────────
export interface Feed {
	url: string;
	source: string;
	category: string;
	enabled: boolean;
}

export const newsFeeds = {
	list:   ()                                          => get<{ feeds: Feed[] }>('/api/news/feeds'),
	add:    (f: Omit<Feed, 'enabled'>)                 => post<{ ok: boolean; feeds: Feed[] }>('/api/news/feeds', f),
	remove: (url: string)                               => del<{ ok: boolean }>(`/api/news/feeds?url=${encodeURIComponent(url)}`),
	toggle: (url: string, enabled: boolean)             => patch<{ ok: boolean }>(`/api/news/feeds?url=${encodeURIComponent(url)}&enabled=${enabled}`),
	reset:  ()                                          => post<{ ok: boolean; feeds: Feed[] }>('/api/news/feeds/reset', {}),
};

// ── News ──────────────────────────────────────────────────────
export interface NewsArticle {
	title:     string;
	link:      string;
	summary:   string;
	source:    string;
	published: string;
	category:  'cybersecurity' | 'tech' | 'ai' | 'robotics';
}

// ── Quick Links ───────────────────────────────────────────────
export const quicklinks = {
	ping: (url: string) =>
		fetch(`${BASE}/api/quicklinks/ping?url=${encodeURIComponent(url)}`, {
			credentials: 'include',
		})
			.then((r) => r.ok ? r.json() as Promise<{ online: boolean; latency_ms: number | null }> : null)
			.catch(() => null),
};

export const news = {
	feed: (refresh = false) =>
		get<{ articles: NewsArticle[]; fetched_at: string; count: number; failed_feeds: number }>(
			`/api/news${refresh ? '?refresh=true' : ''}`,
		),
};

// ── RAG ───────────────────────────────────────────────────────
export const rag = {
	status: () =>
		get<{ available: boolean; indexed_chunks: number; collection: string }>('/api/rag/status'),
	ingest: () => post('/api/rag/ingest', {}),
};

// ── AI ────────────────────────────────────────────────────────
export const ai = {
	health:  () => get<{ status: string; model: string }>('/api/ai/health'),
	models:  () => get<{ models: { name: string }[] }>('/api/ai/models'),
	history: (conversationId: string) => get(`/api/ai/history/${conversationId}`),
	// Streaming — returns raw Response so the caller reads the SSE stream
	chat: (body: { model: string; message: string; conversation_id?: string }) =>
		fetch(`${BASE}/api/ai/chat`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			credentials: 'include',
			body: JSON.stringify(body),
		}),
};
