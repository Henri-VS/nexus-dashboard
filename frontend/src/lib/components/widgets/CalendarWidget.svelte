<script lang="ts">
	import { onMount } from 'svelte';
	import Card from '$lib/components/Card.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	const LS_KEY = 'dashboard_calendar_events';

	interface CalEvent {
		id: number;
		title: string;
		date: string;
		time: string;
		color: string;
		repeat: string;
		description: string;
		notify: boolean;
	}

	// Fixed to the current month — widget always shows "now"
	const TODAY     = new Date();
	const YEAR      = TODAY.getFullYear();
	const MONTH     = TODAY.getMonth();
	const TODAY_STR = localDate(TODAY);

	let events: CalEvent[] = [];
	let loading = true;

	function localDate(d: Date): string {
		const y   = d.getFullYear();
		const m   = String(d.getMonth() + 1).padStart(2, '0');
		const day = String(d.getDate()).padStart(2, '0');
		return `${y}-${m}-${day}`;
	}

	function isOnDate(ev: CalEvent, ds: string): boolean {
		if (ev.date === ds) return true;
		if (ev.repeat === 'none') return false;
		const base  = new Date(ev.date + 'T00:00:00');
		const check = new Date(ds + 'T00:00:00');
		if (check <= base) return false;
		if (ev.repeat === 'daily')   return true;
		if (ev.repeat === 'weekly') {
			const diff = Math.round((check.getTime() - base.getTime()) / 86_400_000);
			return diff % 7 === 0;
		}
		if (ev.repeat === 'monthly') return base.getDate() === check.getDate();
		return false;
	}

	function eventsOn(ds: string): CalEvent[] {
		return events.filter((ev) => isOnDate(ev, ds));
	}

	// Build the month grid once (widget always shows current month)
	function buildGrid(): (Date | null)[] {
		const firstDow   = new Date(YEAR, MONTH, 1).getDay();
		const startShift = (firstDow + 6) % 7; // Mon = 0
		const daysIn     = new Date(YEAR, MONTH + 1, 0).getDate();
		const cells: (Date | null)[] = [];
		for (let i = 0; i < startShift; i++) cells.push(null);
		for (let d = 1; d <= daysIn; d++) cells.push(new Date(YEAR, MONTH, d));
		while (cells.length % 7 !== 0) cells.push(null);
		return cells;
	}

	const grid = buildGrid();

	// Upcoming events: from today onward, sorted, capped at 3
	$: upcoming = [...events]
		.filter((ev) => ev.date >= TODAY_STR)
		.sort((a, b) => {
			const da = a.date + (a.time || '00:00');
			const db = b.date + (b.time || '00:00');
			return da < db ? -1 : da > db ? 1 : 0;
		})
		.slice(0, 3);

	function fmtDate(ev: CalEvent): string {
		const d = new Date(ev.date + 'T00:00:00');
		const label = d.toLocaleDateString('en', { month: 'short', day: 'numeric' });
		return ev.time ? `${label} · ${ev.time}` : label;
	}

	const MONTH_LABEL = TODAY.toLocaleDateString('en', { month: 'long', year: 'numeric' });

	onMount(() => {
		try {
			events = JSON.parse(localStorage.getItem(LS_KEY) || '[]');
		} catch { /* ignore corrupt storage */ }
		loading = false;
	});
</script>

<Card label="calendar" accentColor="var(--accent)" {loading}>
	<a href="/calendar" class="cal-link" aria-label="Open calendar">

		<div class="month-lbl">{MONTH_LABEL}</div>

		<!-- Mini calendar grid -->
		<div class="mini-grid">
			{#each ['M','T','W','T','F','S','S'] as d}
				<div class="mini-dow">{d}</div>
			{/each}

			{#each grid as cell}
				{@const ds    = cell ? localDate(cell) : ''}
				{@const dayEvs = cell ? eventsOn(ds) : []}
				<div
					class="mini-cell"
					class:is-today={ds === TODAY_STR}
					class:is-empty={!cell}
				>
					{#if cell}
						<span class="mini-num">{cell.getDate()}</span>
						{#if dayEvs.length > 0}
							<div class="mini-dots">
								{#each dayEvs.slice(0, 2) as ev}
									<span
										class="mini-dot"
										style="background:{ev.color}"
									></span>
								{/each}
								{#if dayEvs.length > 2}
									<span class="mini-dot extra"></span>
								{/if}
							</div>
						{/if}
					{/if}
				</div>
			{/each}
		</div>

		<div class="divider"></div>

		<!-- Upcoming list -->
		{#if upcoming.length > 0}
			<ul class="upcoming">
				{#each upcoming as ev}
					<li class="up-row">
						<span class="up-dot" style="background:{ev.color}"></span>
						<span class="up-title">{ev.title}</span>
						<span class="up-when">{fmtDate(ev)}</span>
					</li>
				{/each}
			</ul>
		{:else}
			<EmptyState
				variant="not-configured"
				size="compact"
				title="No events"
				body="No upcoming events."
			/>
		{/if}

	</a>
</Card>

<style>
	.cal-link {
		display: block;
		text-decoration: none;
		color: inherit;
	}

	.cal-link:hover .month-lbl {
		color: var(--accent);
	}

	/* ── Month label ─────────────────────────────────────── */
	.month-lbl {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.07em;
		color: var(--text1);
		margin-bottom: 0.55rem;
		transition: color 0.12s;
	}

	/* ── Mini grid ───────────────────────────────────────── */
	.mini-grid {
		display: grid;
		grid-template-columns: repeat(7, 1fr);
		gap: 1px 0;
	}

	.mini-dow {
		font-family: var(--font-mono);
		font-size: 0.52rem;
		text-transform: uppercase;
		color: var(--text2);
		text-align: center;
		padding-bottom: 0.2rem;
	}

	.mini-cell {
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 1px 0;
		border-radius: 3px;
		min-height: 1.65rem;
	}

	.mini-cell.is-empty { pointer-events: none; }

	.mini-cell.is-today {
		background: var(--accent);
		border-radius: 4px;
	}

	.mini-cell.is-today .mini-num {
		color: var(--bg-base);
		font-weight: 700;
	}

	.mini-num {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		color: var(--text2);
		line-height: 1.3;
	}

	/* ── Event dots ──────────────────────────────────────── */
	.mini-dots {
		display: flex;
		gap: 2px;
		justify-content: center;
		margin-top: 1px;
	}

	.mini-dot {
		width: 3px;
		height: 3px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.mini-dot.extra { background: var(--text2); }

	/* ── Divider ─────────────────────────────────────────── */
	.divider {
		height: 1px;
		background: var(--border);
		margin: 0.6rem 0 0.5rem;
	}

	/* ── Upcoming list ───────────────────────────────────── */
	.upcoming {
		list-style: none;
		display: flex;
		flex-direction: column;
		gap: 0.3rem;
	}

	.up-row {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.up-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.up-title {
		font-family: var(--font-mono);
		font-size: 0.75rem;
		color: var(--text0);
		flex: 1;
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
	}

	.up-when {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text2);
		white-space: nowrap;
		flex-shrink: 0;
	}

	/* .empty removed — empty state handled by <EmptyState> component */
</style>
