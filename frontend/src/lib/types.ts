// ── Weather ───────────────────────────────────────────────────

export interface WeatherForecastDay {
	day: string;    // 'Mon', 'Tue', etc.
	code: number;   // WMO weather code
	high: number;
	low: number;
}

export interface WeatherData {
	temperature: number;
	apparent_temperature: number;
	weathercode: number;
	windspeed: number;
	humidity: number;
	location: string;
	forecast?: WeatherForecastDay[];
}

// ── System ────────────────────────────────────────────────────

export interface SystemData {
	cpu_percent: number;
	ram_percent: number;
	ram_used_gb: number;
	ram_total_gb: number;
	disk_percent: number;
	disk_used_gb: number;
	disk_total_gb: number;
	temps: Record<string, number>;
	battery_percent: number | null;
}

// ── Security ──────────────────────────────────────────────────

export interface SecurityAlert {
	id: string;
	timestamp: string;
	severity: 'CRIT' | 'HIGH' | 'WARN' | 'INFO';
	rule_id: string;
	rule_description: string;
	rule_level: number;
	agent_name: string;
	src_ip: string;
}

// ── Notes ─────────────────────────────────────────────────────

export interface NoteFile {
	path: string;
	name: string;
	modified: string | number;
	content?: string;
}

// ── Docker ────────────────────────────────────────────────────

export interface ContainerStatus {
	id: string;
	name: string;
	image: string;
	status: 'running' | 'exited' | 'paused' | 'restarting';
	health: 'healthy' | 'unhealthy' | 'starting' | 'none';
	uptime?: string;
	restart_count?: number;
}

// ── Learning ──────────────────────────────────────────────────

export interface CertTracker {
	name: string;
	exam_date: string | null;
	days_remaining: number | null;
	status: 'studying' | 'scheduled' | 'passed';
}

export interface LearningData {
	thm_rank: string;
	thm_points: number;
	thm_completed_rooms: number;
	badge_name?: string;
	streak?: number;
	certs: CertTracker[];
}

// ── Home Assistant ────────────────────────────────────────────

export interface HomeEntity {
	entity_id: string;
	state: string;
	attributes: {
		friendly_name?: string;
		unit_of_measurement?: string;
		device_class?: string;
		icon?: string;
		[key: string]: unknown;
	};
}

// ── AI ────────────────────────────────────────────────────────

export interface AiMessage {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	timestamp: string;
}

export interface AiConversation {
	id: string;
	title: string;
	model: string;
	messages: AiMessage[];
	created_at: string;
}

// ── Backwards-compatible aliases ──────────────────────────────

export type SystemStats    = SystemData;
export type DockerContainer = ContainerStatus;
export type HaEntity       = HomeEntity;
export type LearningProgress = LearningData;
export type WeatherCurrent = WeatherData;
