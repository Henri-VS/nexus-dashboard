<script lang="ts">
	import { onMount } from 'svelte';
	import { learn as learnApi } from '$lib/api';
	import { editMode } from '$lib/stores/dashConfig';
	import { GripVertical, Eye, EyeOff } from '@lucide/svelte';

	interface Room {
		name: string;
		pct: number;
		status: 'complete' | 'in-progress' | 'not-started';
	}

	interface Cert {
		name: string;
		shortName: string;
		targetDate: string;
		pct: number;
		status: 'studying' | 'upcoming' | 'not-started';
		accentVar: string;
	}

	// THM live data — replaced on mount
	let thmPoints  = 0;
	let thmRank    = '—';
	let thmStreak  = 0;
	let thmRooms   = 0;
	let thmOffline = true;

	const _THM_MOCK = { points: 12_450, rank: 'Hacker', streak: 0, rooms: 44 };

	const ROOMS: Room[] = [
		{ name: 'Linux Fundamentals 1',     pct: 100, status: 'complete'    },
		{ name: 'Linux Fundamentals 2',     pct: 100, status: 'complete'    },
		{ name: 'Linux Fundamentals 3',     pct: 100, status: 'complete'    },
		{ name: 'Nmap',                      pct: 80,  status: 'in-progress' },
		{ name: 'Metasploit: Introduction', pct: 0,   status: 'not-started' },
		{ name: 'Burp Suite Basics',        pct: 0,   status: 'not-started' },
		{ name: 'OWASP Top 10',            pct: 0,   status: 'not-started' },
	];

	const CERTS: Cert[] = [
		{
			name:       'CompTIA Security+',
			shortName:  'Sec+',
			targetDate: '2026-10-15',
			pct:        35,
			status:     'studying',
			accentVar:  'var(--accent)',
		},
		{
			name:       'Cisco CCNA',
			shortName:  'CCNA',
			targetDate: '2027-07-10',
			pct:        5,
			status:     'upcoming',
			accentVar:  'var(--accent2)',
		},
		{
			name:       'CompTIA CySA+',
			shortName:  'CySA+',
			targetDate: '2027-11-20',
			pct:        0,
			status:     'not-started',
			accentVar:  'var(--accent3)',
		},
		{
			name:       'OSCP',
			shortName:  'OSCP',
			targetDate: '2028-05-01',
			pct:        0,
			status:     'not-started',
			accentVar:  'var(--red)',
		},
	];

	onMount(async () => {
		const res = await learnApi.progress();
		if (res) {
			thmPoints  = res.thm_points;
			thmRank    = res.thm_rank;
			thmStreak  = res.streak ?? 0;
			thmRooms   = res.thm_completed_rooms;
			thmOffline = false;
		}
		// else: keep thmOffline = true and show mock defaults
	});

	const TODAY = new Date();

	function daysUntil(dateStr: string): number {
		return Math.ceil((new Date(dateStr).getTime() - TODAY.getTime()) / 86_400_000);
	}

	function roomBarColor(pct: number, status: string): string {
		if (status === 'complete') return 'var(--green)';
		if (pct > 0)               return 'var(--yellow)';
		return 'var(--text2)';
	}

	function certStatusColor(s: string): string {
		if (s === 'studying') return 'var(--accent)';
		if (s === 'upcoming') return 'var(--accent2)';
		return 'var(--text2)';
	}

	function certStatusLabel(s: string): string {
		if (s === 'studying') return 'studying';
		if (s === 'upcoming') return 'upcoming';
		return 'not started';
	}

	function daysColor(days: number): string {
		if (days < 90)  return 'var(--red)';
		if (days < 270) return 'var(--yellow)';
		return 'var(--accent2)';
	}

	$: completeRooms = ROOMS.filter((r) => r.status === 'complete').length;

	// ── Edit mode layout ──────────────────────────────────────────
	const PAGE_KEY = 'dashboard_config.learn';
	const DEFAULT_ORDER = ['thm', 'certs'] as const;
	const COL_LABELS: Record<string, string> = { thm: 'tryhackme', certs: 'cert roadmap' };

	let colOrder: string[]      = [...DEFAULT_ORDER];
	let disabledSet = new Set<string>();
	let draggedId:    string | null = null;
	let dropTargetId: string | null = null;
	let cfgMounted = false;

	// ── Section collapse ──────────────────────────────────────────
	let thmStatsOpen = true;
	let roomsOpen    = true;
	let certsOpen    = true;

	onMount(() => {
		const raw = localStorage.getItem(PAGE_KEY);
		if (raw) {
			try {
				const cfg = JSON.parse(raw);
				if (Array.isArray(cfg.order))    colOrder    = cfg.order;
				if (Array.isArray(cfg.disabled)) disabledSet = new Set(cfg.disabled);
				if (cfg.collapsed) {
					if ('thmStats' in cfg.collapsed) thmStatsOpen = !cfg.collapsed.thmStats;
					if ('rooms'    in cfg.collapsed) roomsOpen    = !cfg.collapsed.rooms;
					if ('certs'    in cfg.collapsed) certsOpen    = !cfg.collapsed.certs;
				}
			} catch { /* ignore */ }
		}
		cfgMounted = true;
	});

	$: if (cfgMounted) {
		try {
			localStorage.setItem(PAGE_KEY, JSON.stringify({
				order:    colOrder,
				disabled: [...disabledSet],
				collapsed: {
					thmStats: !thmStatsOpen,
					rooms:    !roomsOpen,
					certs:    !certsOpen,
				},
			}));
		} catch { /* ignore */ }
	}

	function startDrag(id: string) { draggedId = id; }
	function onDragOver(id: string) { if (id !== draggedId) dropTargetId = id; }
	function onDrop(id: string) {
		if (!draggedId || draggedId === id) return;
		const from = colOrder.indexOf(draggedId);
		const to   = colOrder.indexOf(id);
		if (from < 0 || to < 0) return;
		const arr = [...colOrder]; arr.splice(from, 1); arr.splice(to, 0, draggedId);
		colOrder = arr;
	}
	function onDragEnd() { draggedId = null; dropTargetId = null; }
	function toggleCol(id: string) {
		const s = new Set(disabledSet);
		if (s.has(id)) s.delete(id); else s.add(id);
		disabledSet = s;
	}

	// ── Study stats ───────────────────────────────────────────────
	interface StudyStat { subject: string; minutes: number; }

	let studyStats: StudyStat[] = [];

	$: maxMins = studyStats.reduce((m, s) => Math.max(m, s.minutes), 0);

	function loadStudyStats() {
		try {
			const raw = localStorage.getItem('nexus_study_sessions');
			if (!raw) { studyStats = []; return; }
			const sessions = JSON.parse(raw) as Array<{ subject: string; minutes: number; date: number }>;
			const cutoff   = Date.now() - 7 * 24 * 60 * 60 * 1000;
			const recent   = sessions.filter((s) => s.date >= cutoff);
			const map = new Map<string, number>();
			for (const s of recent) map.set(s.subject, (map.get(s.subject) ?? 0) + s.minutes);
			studyStats = [...map.entries()].map(([subject, minutes]) => ({ subject, minutes }))
				.sort((a, b) => b.minutes - a.minutes);
		} catch { studyStats = []; }
	}

	onMount(() => { loadStudyStats(); });
</script>

<svelte:head>
	<title>Nexus — Learn</title>
</svelte:head>

<div class="learn-outer">

{#if studyStats.length > 0}
<div class="study-stats-section">
	<div class="section">
		<div class="section-header">
			<div class="section-title">
				<span class="accent-bar" style="background: var(--accent3)"></span>
				<h2>study activity · last 7 days</h2>
			</div>
			<span class="offline-badge">{studyStats.reduce((s, r) => s + r.minutes, 0)} min total</span>
		</div>
		<div class="stats-bars">
			{#each studyStats as stat}
				<div class="stat-row">
					<span class="stat-subject">{stat.subject}</span>
					<div class="stat-track">
						<div
							class="stat-fill"
							style="width:{maxMins > 0 ? Math.round((stat.minutes / maxMins) * 100) : 0}%"
						></div>
					</div>
					<span class="stat-mins">{stat.minutes}m</span>
				</div>
			{/each}
		</div>
	</div>
</div>
{/if}

<div class="learn-page">

	{#each colOrder as id (id)}
		{#if !disabledSet.has(id) || $editMode}
			<div
				class="col-wrap"
				role="region"
				aria-label={COL_LABELS[id]}
				class:is-dragging={draggedId === id}
				class:is-target={dropTargetId === id}
				class:is-hidden={disabledSet.has(id)}
				draggable={$editMode ? 'true' : 'false'}
				on:dragstart={() => startDrag(id)}
				on:dragover|preventDefault={() => onDragOver(id)}
				on:drop|preventDefault={() => onDrop(id)}
				on:dragend={onDragEnd}
			>
				{#if $editMode}
					<div class="edit-bar">
						<GripVertical size={13} strokeWidth={1.5} />
						<span class="edit-label">{COL_LABELS[id]}</span>
						<button
							class="vis-btn"
							on:click={() => toggleCol(id)}
							title={disabledSet.has(id) ? 'Show column' : 'Hide column'}
							aria-label={disabledSet.has(id) ? 'Show column' : 'Hide column'}
						>
							{#if disabledSet.has(id)}<EyeOff size={13} strokeWidth={1.5} />{:else}<Eye size={13} strokeWidth={1.5} />{/if}
						</button>
					</div>
				{/if}

				{#if id === 'thm'}
					<!-- ── TryHackMe column ────────────────── -->
					<div class="col">
						<div class="section">
							<div class="section-header">
								<div class="section-title">
									<span class="accent-bar" style="background: var(--red)"></span>
									<h2>tryhackme</h2>
								</div>
								<div class="header-right">
									{#if thmOffline}<span class="offline-badge">— offline —</span>{/if}
									<button class="collapse-btn" on:click={() => (thmStatsOpen = !thmStatsOpen)} aria-label={thmStatsOpen ? 'Collapse' : 'Expand'}>{thmStatsOpen ? '▲' : '▼'}</button>
								</div>
							</div>
							{#if thmStatsOpen}
							<div class="thm-stats">
								<div class="thm-stat">
									<span class="thm-val" style="color: var(--red)">{thmPoints.toLocaleString()}</span>
									<span class="thm-lbl">points</span>
								</div>
								<div class="thm-divider"></div>
								<div class="thm-stat">
									<span class="thm-val" style="color: var(--yellow)">{thmRank}</span>
									<span class="thm-lbl">rank</span>
								</div>
								<div class="thm-divider"></div>
								<div class="thm-stat">
									<span class="thm-val" style="color: var(--accent2)">{thmRooms}</span>
									<span class="thm-lbl">rooms</span>
								</div>
								<div class="thm-divider"></div>
								<div class="thm-stat">
									<span class="thm-val" style="color: var(--accent4)">{thmStreak}</span>
									<span class="thm-lbl">day streak</span>
								</div>
							</div>
							{/if}
						</div>

						<div class="section">
							<div class="section-header">
								<div class="section-title">
									<span class="accent-bar" style="background: var(--yellow)"></span>
									<h2>rooms</h2>
									<span class="count-pill" style="color: var(--green); border-color: color-mix(in srgb, var(--green) 30%, var(--border))">
										{completeRooms}/{ROOMS.length} complete
									</span>
								</div>
								<button class="collapse-btn" on:click={() => (roomsOpen = !roomsOpen)} aria-label={roomsOpen ? 'Collapse' : 'Expand'}>{roomsOpen ? '▲' : '▼'}</button>
							</div>
							{#if roomsOpen}
							<div class="room-list">
								{#each ROOMS as room}
									<div class="room-row">
										<div class="room-top">
											<span class="room-name">{room.name}</span>
											<span class="room-badge" style="color:{roomBarColor(room.pct,room.status)};border-color:color-mix(in srgb,{roomBarColor(room.pct,room.status)} 30%,var(--border))">
												{#if room.status === 'complete'}complete{:else if room.status === 'in-progress'}{room.pct}%{:else}not started{/if}
											</span>
										</div>
										<div class="progress-track">
											<div class="progress-fill" style="width:{room.pct}%;background:{roomBarColor(room.pct,room.status)}"></div>
										</div>
									</div>
								{/each}
							</div>
							{/if}
						</div>
					</div>

				{:else if id === 'certs'}
					<!-- ── Cert roadmap column ─────────────── -->
					<div class="col">
						<div class="section">
							<div class="section-header">
								<div class="section-title">
									<span class="accent-bar" style="background: var(--accent3)"></span>
									<h2>certification roadmap</h2>
								</div>
								<button class="collapse-btn" on:click={() => (certsOpen = !certsOpen)} aria-label={certsOpen ? 'Collapse' : 'Expand'}>{certsOpen ? '▲' : '▼'}</button>
							</div>
							{#if certsOpen}
							<div class="cert-list">
								{#each CERTS as cert}
									{@const days = daysUntil(cert.targetDate)}
									<div class="cert-card" style="border-left-color:{cert.accentVar}">
										<div class="cert-top">
											<div class="cert-names">
												<span class="cert-short" style="color:{cert.accentVar}">{cert.shortName}</span>
												<span class="cert-full">{cert.name}</span>
											</div>
											<span class="cert-status" style="color:{certStatusColor(cert.status)};border-color:color-mix(in srgb,{certStatusColor(cert.status)} 30%,var(--border))">{certStatusLabel(cert.status)}</span>
										</div>
										<div class="cert-meta">
											<span class="cert-target">target: <code>{cert.targetDate}</code></span>
											<span class="cert-days" style="color:{daysColor(days)}">{days}d</span>
										</div>
										<div class="cert-bar-row">
											<div class="progress-track">
												<div class="progress-fill" style="width:{cert.pct}%;background:{cert.accentVar}"></div>
											</div>
											<span class="cert-pct">{cert.pct}%</span>
										</div>
									</div>
								{/each}
							</div>
							{/if}
						</div>
					</div>
				{/if}

			</div>
		{/if}
	{/each}

</div>
</div>

<style>
	.learn-outer {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	.study-stats-section { width: 100%; }

	.stats-bars {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
	}

	.stat-row {
		display: flex;
		align-items: center;
		gap: 0.65rem;
	}

	.stat-subject {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text0);
		width: 80px;
		flex-shrink: 0;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.stat-track {
		flex: 1;
		height: 6px;
		background: var(--bg2);
		border-radius: 3px;
		overflow: hidden;
	}

	.stat-fill {
		height: 100%;
		background: var(--accent3);
		border-radius: 3px;
		transition: width 0.4s ease;
	}

	.stat-mins {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--accent3);
		width: 38px;
		text-align: right;
		flex-shrink: 0;
	}

	.learn-page {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 1.25rem;
		align-items: start;
	}

	/* ── Edit mode ──────────────────────────────────────────── */
	.col-wrap {
		display: flex;
		flex-direction: column;
		min-width: 0;
	}

	.col-wrap.is-dragging {
		opacity: 0.45;
		outline: 2px dashed var(--accent);
		outline-offset: 2px;
		border-radius: var(--radius);
	}

	.col-wrap.is-target {
		outline: 2px dashed var(--accent3);
		outline-offset: 2px;
		border-radius: var(--radius);
	}

	.col-wrap.is-hidden { opacity: 0.35; }

	.edit-bar {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.3rem 0.75rem;
		background: color-mix(in srgb, var(--accent) 8%, var(--bg2));
		border: 1px dashed color-mix(in srgb, var(--accent) 35%, var(--border));
		border-bottom: none;
		border-radius: var(--radius) var(--radius) 0 0;
		cursor: grab;
		user-select: none;
		margin-bottom: 0;
	}

	.edit-label {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text2);
		flex: 1;
	}

	.vis-btn {
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		padding: 0.15rem;
		border-radius: 3px;
		display: flex;
		align-items: center;
		transition: color 0.1s;
	}

	.vis-btn:hover { color: var(--text0); }

	.col {
		display: flex;
		flex-direction: column;
		gap: 1.25rem;
	}

	/* ── Section shell ──────────────────────────────────────── */
	.section {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
	}

	.section-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.65rem 1rem;
		border-bottom: 1px solid var(--border);
	}

	.section-title {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.accent-bar {
		width: 3px;
		height: 1rem;
		border-radius: 2px;
		flex-shrink: 0;
	}

	h2 {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text1);
		margin: 0;
	}

	.offline-badge {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		letter-spacing: 0.04em;
	}

	.count-pill {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		border: 1px solid;
		border-radius: 20px;
		padding: 0.1rem 0.5rem;
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.collapse-btn {
		background: none;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		color: var(--text2);
		font-family: var(--font-mono);
		font-size: 0.6rem;
		padding: 0.1rem 0.45rem;
		cursor: pointer;
		flex-shrink: 0;
		min-height: unset;
		transition: color 0.1s, border-color 0.1s;
	}
	.collapse-btn:hover { color: var(--accent2); border-color: var(--accent2); }

	/* ── THM stats ──────────────────────────────────────────── */
	.thm-stats {
		display: flex;
		align-items: stretch;
	}

	.thm-stat {
		flex: 1;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 0.2rem;
		padding: 1.1rem 0.5rem;
	}

	.thm-val {
		font-family: var(--font-mono);
		font-size: 1.5rem;
		font-weight: 700;
		line-height: 1;
	}

	.thm-lbl {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text2);
	}

	.thm-divider {
		width: 1px;
		background: var(--border);
		align-self: stretch;
		margin: 0.75rem 0;
	}

	/* ── Room list ──────────────────────────────────────────── */
	.room-list {
		display: flex;
		flex-direction: column;
	}

	.room-row {
		padding: 0.6rem 1rem;
		border-bottom: 1px solid color-mix(in srgb, var(--border) 50%, transparent);
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		transition: background 0.1s;
	}

	.room-row:last-child { border-bottom: none; }
	.room-row:hover      { background: var(--bg2); }

	.room-top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.room-name {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text0);
	}

	.room-badge {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		border: 1px solid;
		border-radius: 3px;
		padding: 0.05rem 0.35rem;
		white-space: nowrap;
		flex-shrink: 0;
	}

	/* ── Shared progress bar ────────────────────────────────── */
	.progress-track {
		height: 3px;
		background: var(--bg2);
		border-radius: 2px;
		overflow: hidden;
		flex: 1;
	}

	.progress-fill {
		height: 100%;
		border-radius: 2px;
		transition: width 0.4s ease;
	}

	/* ── Cert cards ─────────────────────────────────────────── */
	.cert-list {
		display: flex;
		flex-direction: column;
	}

	.cert-card {
		padding: 0.85rem 1rem 0.85rem 0.85rem;
		border-left: 3px solid;
		border-bottom: 1px solid color-mix(in srgb, var(--border) 50%, transparent);
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		transition: background 0.1s;
	}

	.cert-card:last-child { border-bottom: none; }
	.cert-card:hover      { background: var(--bg2); }

	.cert-top {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.cert-names {
		display: flex;
		flex-direction: column;
		gap: 0.05rem;
	}

	.cert-short {
		font-family: var(--font-mono);
		font-size: 0.9rem;
		font-weight: 700;
		line-height: 1;
	}

	.cert-full {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text1);
	}

	.cert-status {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		border: 1px solid;
		border-radius: 3px;
		padding: 0.1rem 0.4rem;
		white-space: nowrap;
		flex-shrink: 0;
	}

	.cert-meta {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 0.5rem;
	}

	.cert-target {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		color: var(--text2);
	}

	.cert-target code {
		color: var(--text1);
		background: none;
		border: none;
		padding: 0;
		font-size: inherit;
	}

	.cert-days {
		font-family: var(--font-mono);
		font-size: 0.82rem;
		font-weight: 700;
		flex-shrink: 0;
	}

	.cert-bar-row {
		display: flex;
		align-items: center;
		gap: 0.5rem;
	}

	.cert-pct {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		flex-shrink: 0;
		min-width: 2.5ch;
		text-align: right;
	}

	/* ── Responsive ─────────────────────────────────────────── */
	@media (max-width: 900px) {
		.learn-page { grid-template-columns: 1fr; }
		.col-wrap.is-dragging, .col-wrap.is-target { outline-offset: 0; }
	}
</style>
