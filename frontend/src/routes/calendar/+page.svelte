<script lang="ts">
	import { onMount } from 'svelte';
	import { ChevronLeft, ChevronRight, Plus, X, Trash2, Edit2 } from '@lucide/svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';

	const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8088';

	type ViewMode = 'month' | 'week' | 'day';
	type Repeat   = 'none' | 'daily' | 'weekly' | 'monthly';

	interface CalEvent {
		id: number;
		title: string;
		date: string;
		time: string;
		description: string;
		repeat: Repeat;
		notify: boolean;
		color: string;
	}

	const COLORS   = ['#7c8cf8', '#f87171', '#34d399', '#fbbf24', '#a78bfa', '#38bdf8'];
	const MONTHS   = ['January','February','March','April','May','June',
	                  'July','August','September','October','November','December'];
	const DAY_ABBR = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'];
	const HOURS    = Array.from({ length: 16 }, (_, i) => i + 7); // 7–22
	const VIEWS: ViewMode[] = ['month', 'week', 'day'];
	const LS_KEY   = 'dashboard_calendar_events';

	let viewMode: ViewMode = 'month';
	let cursor   = new Date();
	let events: CalEvent[] = [];
	let showModal  = false;
	let selectedEv: CalEvent | null = null;
	let isEditing  = false;

	function defaultForm() {
		return {
			title:       '',
			date:        localDate(new Date()),
			time:        '',
			description: '',
			repeat:      'none' as Repeat,
			notify:      false,
			color:       COLORS[0],
		};
	}

	let form = defaultForm();

	// ── Date helpers ─────────────────────────────────────────────
	function localDate(d: Date): string {
		const y   = d.getFullYear();
		const m   = String(d.getMonth() + 1).padStart(2, '0');
		const day = String(d.getDate()).padStart(2, '0');
		return `${y}-${m}-${day}`;
	}

	function fmtHour(h: number): string {
		if (h === 0)  return '12am';
		if (h < 12)   return `${h}am`;
		if (h === 12) return '12pm';
		return `${h - 12}pm`;
	}

	// ── Calendar math ────────────────────────────────────────────
	function monthGrid(year: number, month: number): (Date | null)[] {
		const firstDow   = new Date(year, month, 1).getDay();
		const startShift = (firstDow + 6) % 7; // Mon = 0
		const daysIn     = new Date(year, month + 1, 0).getDate();
		const cells: (Date | null)[] = [];
		for (let i = 0; i < startShift; i++) cells.push(null);
		for (let d = 1; d <= daysIn; d++) cells.push(new Date(year, month, d));
		while (cells.length % 7 !== 0) cells.push(null);
		return cells;
	}

	function getWeekDays(d: Date): Date[] {
		const dow   = d.getDay();
		const shift = (dow + 6) % 7;
		const start = new Date(d);
		start.setDate(d.getDate() - shift);
		return Array.from({ length: 7 }, (_, i) => {
			const day = new Date(start);
			day.setDate(start.getDate() + i);
			return day;
		});
	}

	// ── Event matching with repeat support ───────────────────────
	function isOnDate(ev: CalEvent, ds: string): boolean {
		if (ev.date === ds) return true;
		if (ev.repeat === 'none') return false;
		const base  = new Date(ev.date + 'T00:00:00');
		const check = new Date(ds + 'T00:00:00');
		if (check <= base) return false;
		if (ev.repeat === 'daily') return true;
		if (ev.repeat === 'weekly') {
			const diff = Math.round((check.getTime() - base.getTime()) / 86_400_000);
			return diff % 7 === 0;
		}
		if (ev.repeat === 'monthly') return base.getDate() === check.getDate();
		return false;
	}

	function eventsOn(ds: string): CalEvent[] {
		return events.filter(ev => isOnDate(ev, ds));
	}

	function eventsForHour(ds: string, h: number): CalEvent[] {
		return eventsOn(ds).filter(ev => ev.time && parseInt(ev.time.split(':')[0]) === h);
	}

	// ── Navigation ───────────────────────────────────────────────
	function nav(dir: -1 | 1) {
		const d = new Date(cursor);
		if (viewMode === 'month')      d.setMonth(d.getMonth() + dir);
		else if (viewMode === 'week')  d.setDate(d.getDate() + dir * 7);
		else                           d.setDate(d.getDate() + dir);
		cursor = d;
	}

	// ── Persistence ──────────────────────────────────────────────
	async function loadEvents() {
		const local: CalEvent[] = JSON.parse(localStorage.getItem(LS_KEY) || '[]');
		events = local;
		try {
			const r = await fetch(`${BASE}/api/calendar/events`);
			if (r.ok) {
				events = await r.json();
				localStorage.setItem(LS_KEY, JSON.stringify(events));
			}
		} catch { /* offline – use local cache */ }
	}

	// ── CRUD ─────────────────────────────────────────────────────
	async function submitForm() {
		if (!form.title.trim()) return;

		if (isEditing && selectedEv) {
			try {
				await fetch(`${BASE}/api/calendar/events/${selectedEv.id}`, { method: 'DELETE' });
			} catch {}
			events = events.filter(e => e.id !== selectedEv!.id);
		}

		let created: CalEvent;
		try {
			const r = await fetch(`${BASE}/api/calendar/events`, {
				method:  'POST',
				headers: { 'Content-Type': 'application/json' },
				body:    JSON.stringify(form),
			});
			created = r.ok ? await r.json() : { id: Date.now(), ...form };
		} catch {
			created = { id: Date.now(), ...form };
		}

		events = [...events, created];
		localStorage.setItem(LS_KEY, JSON.stringify(events));
		closeModal();
	}

	async function removeEvent(ev: CalEvent) {
		try {
			await fetch(`${BASE}/api/calendar/events/${ev.id}`, { method: 'DELETE' });
		} catch {}
		events    = events.filter(e => e.id !== ev.id);
		localStorage.setItem(LS_KEY, JSON.stringify(events));
		selectedEv = null;
	}

	// ── Modal helpers ────────────────────────────────────────────
	function openAdd(date?: Date) {
		isEditing  = false;
		selectedEv = null;
		form       = { ...defaultForm(), date: date ? localDate(date) : localDate(new Date()) };
		showModal  = true;
	}

	function openAddAt(date: Date, hour: number) {
		openAdd(date);
		form.time = `${String(hour).padStart(2, '0')}:00`;
	}

	function openEdit(ev: CalEvent) {
		isEditing  = true;
		selectedEv = ev;
		form       = { title: ev.title, date: ev.date, time: ev.time,
		               description: ev.description, repeat: ev.repeat,
		               notify: ev.notify, color: ev.color };
		showModal  = true;
	}

	function closeModal() {
		showModal  = false;
		isEditing  = false;
		selectedEv = null;
		form       = defaultForm();
	}

	onMount(loadEvents);

	// ── Reactive ─────────────────────────────────────────────────
	$: cursorYear  = cursor.getFullYear();
	$: cursorMonth = cursor.getMonth();
	$: grid        = monthGrid(cursorYear, cursorMonth);
	$: weekDayList = getWeekDays(cursor);
	$: todayStr    = localDate(new Date());
	$: cursorStr   = localDate(cursor);

	$: headerLabel =
		viewMode === 'month' ? `${MONTHS[cursorMonth]} ${cursorYear}` :
		viewMode === 'week'  ? (() => {
			const wk = getWeekDays(cursor);
			return `${wk[0].toLocaleDateString('en', { month: 'short', day: 'numeric' })} – ${wk[6].toLocaleDateString('en', { month: 'short', day: 'numeric', year: 'numeric' })}`;
		})() :
		cursor.toLocaleDateString('en', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });
</script>

<svelte:head><title>Nexus — Calendar</title></svelte:head>

<div class="cal-page">

	<!-- ── Toolbar ─────────────────────────────────────────── -->
	<div class="toolbar">
		<div class="toolbar-left">
			<button class="nav-btn" on:click={() => nav(-1)} aria-label="Previous">
				<ChevronLeft size={15} strokeWidth={2} />
			</button>
			<button class="nav-btn" on:click={() => nav(1)} aria-label="Next">
				<ChevronRight size={15} strokeWidth={2} />
			</button>
			<button class="today-btn" on:click={() => (cursor = new Date())}>today</button>
			<span class="period-label">{headerLabel}</span>
		</div>
		<div class="toolbar-right">
			<div class="view-tabs" role="group" aria-label="Calendar view">
				{#each VIEWS as v}
					<button
						class="view-tab"
						class:active={viewMode === v}
						on:click={() => (viewMode = v)}
					>{v}</button>
				{/each}
			</div>
			<button class="add-btn" on:click={() => openAdd()}>
				<Plus size={13} strokeWidth={2.5} /> new event
			</button>
		</div>
	</div>

	<!-- ── Month view ──────────────────────────────────────── -->
	{#if viewMode === 'month'}
		<div class="month-wrap">
			<div class="dow-row">
				{#each DAY_ABBR as d}<div class="dow-hdr">{d}</div>{/each}
			</div>
			<div class="month-grid">
				{#each grid as cell}
					{@const ds    = cell ? localDate(cell) : ''}
					{@const dayEvs = cell ? eventsOn(ds) : []}
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<div
						class="m-cell"
						class:today={ds === todayStr}
						class:muted={!cell}
						on:click={() => cell && openAdd(cell)}
						on:keydown={(e) => e.key === 'Enter' && cell && openAdd(cell)}
						role={cell ? 'button' : 'presentation'}
						tabindex={cell ? 0 : -1}
						aria-label={cell ? `${ds}, ${dayEvs.length} event${dayEvs.length !== 1 ? 's' : ''}` : undefined}
					>
						{#if cell}
							<span class="cell-num" class:today-num={ds === todayStr}>{cell.getDate()}</span>
							<div class="dots-row">
								{#each dayEvs.slice(0, 4) as ev}
									<button
										class="ev-dot"
										style="background:{ev.color}"
										title={ev.title}
										on:click|stopPropagation={() => (selectedEv = ev)}
										aria-label={ev.title}
									></button>
								{/each}
								{#if dayEvs.length > 4}
									<span class="more-pill">+{dayEvs.length - 4}</span>
								{/if}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		</div>

	<!-- ── Week view ───────────────────────────────────────── -->
	{:else if viewMode === 'week'}
		<div class="week-wrap">
			<div class="time-grid">
				<div class="grid-corner"></div>
				{#each weekDayList as d}
					{@const ds = localDate(d)}
					<div class="col-hdr" class:today-col={ds === todayStr}>
						<span class="col-dow">{DAY_ABBR[(d.getDay() + 6) % 7]}</span>
						<span class="col-date" class:today-num={ds === todayStr}>{d.getDate()}</span>
					</div>
				{/each}
				{#each HOURS as h}
					<div class="hour-lbl">{fmtHour(h)}</div>
					{#each weekDayList as d}
						{@const ds   = localDate(d)}
						{@const hEvs = eventsForHour(ds, h)}
						<!-- svelte-ignore a11y-no-static-element-interactions -->
						<div
							class="hour-cell"
							class:today-col={ds === todayStr}
							on:click={() => openAddAt(d, h)}
							on:keydown={(e) => e.key === 'Enter' && openAddAt(d, h)}
							role="button"
							tabindex="0"
							aria-label={`${fmtHour(h)} ${ds}`}
						>
							{#each hEvs as ev}
								<button
									class="week-ev"
									style="border-left-color:{ev.color};background:color-mix(in srgb,{ev.color} 12%,var(--bg2))"
									on:click|stopPropagation={() => (selectedEv = ev)}
									title={ev.title}
								>{ev.title}</button>
							{/each}
						</div>
					{/each}
				{/each}
			</div>
		</div>

	<!-- ── Day view ────────────────────────────────────────── -->
	{:else}
		<div class="day-wrap">
			{#each HOURS as h}
				{@const hEvs = eventsForHour(cursorStr, h)}
				<div class="day-row">
					<div class="day-hour-lbl">{fmtHour(h)}</div>
					<!-- svelte-ignore a11y-no-static-element-interactions -->
					<div
						class="day-hour-slot"
						on:click={() => openAddAt(cursor, h)}
						on:keydown={(e) => e.key === 'Enter' && openAddAt(cursor, h)}
						role="button"
						tabindex="0"
						aria-label={fmtHour(h)}
					>
						{#each hEvs as ev}
							<button
								class="day-ev"
								style="border-left-color:{ev.color};background:color-mix(in srgb,{ev.color} 10%,var(--bg1))"
								on:click|stopPropagation={() => (selectedEv = ev)}
							>
								<span class="day-ev-time">{ev.time}</span>
								<span class="day-ev-title">{ev.title}</span>
								{#if ev.description}<span class="day-ev-desc">{ev.description}</span>{/if}
							</button>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	{/if}

	{#if events.length === 0}
		<EmptyState
			variant="not-configured"
			size="compact"
			title="No events this month"
			body="Connect a calendar integration in Settings to sync Google Calendar, CalDAV, or iCal feeds."
			primaryAction="Configure Calendar →"
			primaryHref="/settings"
		/>
	{/if}

</div>

<!-- ── Event detail popup ──────────────────────────────────── -->
{#if selectedEv && !showModal}
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="overlay-backdrop"
		on:click={() => (selectedEv = null)}
		on:keydown={(e) => e.key === 'Escape' && (selectedEv = null)}
	>
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div class="detail-card" on:click|stopPropagation on:keydown|stopPropagation>
			<div class="detail-top" style="border-left-color:{selectedEv.color}">
				<div class="detail-info">
					<div class="detail-title">{selectedEv.title}</div>
					<div class="detail-meta">
						{selectedEv.date}{selectedEv.time ? ` · ${selectedEv.time}` : ''}
					</div>
				</div>
				<div class="detail-btns">
					<button
						class="icon-btn"
						on:click={() => { openEdit(selectedEv!); }}
						title="Edit"
						aria-label="Edit event"
					><Edit2 size={13} /></button>
					<button
						class="icon-btn danger"
						on:click={() => removeEvent(selectedEv!)}
						title="Delete"
						aria-label="Delete event"
					><Trash2 size={13} /></button>
					<button
						class="icon-btn"
						on:click={() => (selectedEv = null)}
						title="Close"
						aria-label="Close"
					><X size={13} /></button>
				</div>
			</div>
			{#if selectedEv.description}
				<div class="detail-desc">{selectedEv.description}</div>
			{/if}
			{#if selectedEv.repeat !== 'none' || selectedEv.notify}
				<div class="detail-chips">
					{#if selectedEv.repeat !== 'none'}
						<span class="chip">repeats {selectedEv.repeat}</span>
					{/if}
					{#if selectedEv.notify}
						<span class="chip accent">push on</span>
					{/if}
				</div>
			{/if}
		</div>
	</div>
{/if}

<!-- ── Add / Edit modal ─────────────────────────────────────── -->
{#if showModal}
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		class="overlay-backdrop"
		on:click={closeModal}
		on:keydown={(e) => e.key === 'Escape' && closeModal()}
	>
		<!-- svelte-ignore a11y-no-static-element-interactions -->
		<div class="modal" on:click|stopPropagation on:keydown|stopPropagation>
			<div class="modal-hdr">
				<span class="modal-title">{isEditing ? 'edit event' : 'new event'}</span>
				<button class="icon-btn" on:click={closeModal} aria-label="Close"><X size={14} /></button>
			</div>

			<div class="modal-body">
				<label class="field">
					<span class="flbl">title</span>
					<input class="finput" type="text" bind:value={form.title} placeholder="Event title" />
				</label>

				<div class="field-row">
					<label class="field">
						<span class="flbl">date</span>
						<input class="finput" type="date" bind:value={form.date} />
					</label>
					<label class="field">
						<span class="flbl">time</span>
						<input class="finput" type="time" bind:value={form.time} />
					</label>
				</div>

				<label class="field">
					<span class="flbl">description</span>
					<textarea class="finput ftextarea" bind:value={form.description} rows="2" placeholder="Optional"></textarea>
				</label>

				<div class="field-row">
					<label class="field">
						<span class="flbl">repeat</span>
						<select class="finput" bind:value={form.repeat}>
							<option value="none">none</option>
							<option value="daily">daily</option>
							<option value="weekly">weekly</option>
							<option value="monthly">monthly</option>
						</select>
					</label>
					<div class="field">
						<span class="flbl">color</span>
						<div class="color-row">
							{#each COLORS as c}
								<button
									class="color-sw"
									class:active={form.color === c}
									style="background:{c}"
									on:click={() => (form.color = c)}
									aria-label={c}
								></button>
							{/each}
						</div>
					</div>
				</div>

				<label class="field check-field">
					<input type="checkbox" bind:checked={form.notify} />
					<span class="flbl">send push notification (ntfy)</span>
				</label>
			</div>

			<div class="modal-ftr">
				<button class="cancel-btn" on:click={closeModal}>cancel</button>
				<button
					class="submit-btn"
					on:click={submitForm}
					disabled={!form.title.trim()}
				>{isEditing ? 'save changes' : 'add event'}</button>
			</div>
		</div>
	</div>
{/if}

<style>
	/* ── Page shell ─────────────────────────────────────────── */
	.cal-page {
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
		height: 100%;
	}

	/* ── Toolbar ────────────────────────────────────────────── */
	.toolbar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		flex-wrap: wrap;
		gap: 0.5rem;
		padding: 0.55rem 0.85rem;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		flex-shrink: 0;
	}

	.toolbar-left, .toolbar-right {
		display: flex;
		align-items: center;
		gap: 0.4rem;
	}

	.nav-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		background: none;
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text2);
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}

	.nav-btn:hover { color: var(--text0); border-color: var(--text1); }

	.today-btn {
		font-family: var(--font-mono);
		font-size: 0.68rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		padding: 0.25rem 0.6rem;
		background: none;
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text2);
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}

	.today-btn:hover { color: var(--text0); border-color: var(--text1); }

	.period-label {
		font-family: var(--font-mono);
		font-size: 0.88rem;
		font-weight: 700;
		color: var(--text0);
		letter-spacing: 0.02em;
	}

	.view-tabs {
		display: flex;
		border: 1px solid var(--border);
		border-radius: 4px;
		overflow: hidden;
	}

	.view-tab {
		font-family: var(--font-mono);
		font-size: 0.65rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		padding: 0.25rem 0.6rem;
		background: none;
		border: none;
		color: var(--text2);
		cursor: pointer;
		border-right: 1px solid var(--border);
		transition: background 0.1s, color 0.1s;
	}

	.view-tab:last-child { border-right: none; }
	.view-tab:hover      { background: var(--bg2); color: var(--text0); }

	.view-tab.active {
		background: var(--accent);
		color: var(--bg-base);
	}

	.add-btn {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		font-family: var(--font-mono);
		font-size: 0.68rem;
		font-weight: 700;
		padding: 0.3rem 0.7rem;
		background: var(--accent);
		color: var(--bg-base);
		border: none;
		border-radius: 4px;
		cursor: pointer;
		transition: opacity 0.1s;
	}

	.add-btn:hover { opacity: 0.85; }

	/* ── Month view ─────────────────────────────────────────── */
	.month-wrap {
		flex: 1;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		min-height: 0;
	}

	.dow-row {
		display: grid;
		grid-template-columns: repeat(7, 1fr);
		border-bottom: 1px solid var(--border);
		flex-shrink: 0;
	}

	.dow-hdr {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text2);
		padding: 0.4rem;
		text-align: center;
	}

	.month-grid {
		display: grid;
		grid-template-columns: repeat(7, 1fr);
		flex: 1;
		overflow-y: auto;
	}

	.m-cell {
		border-right: 1px solid var(--border);
		border-bottom: 1px solid var(--border);
		padding: 0.4rem 0.45rem;
		min-height: 5.5rem;
		cursor: pointer;
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		transition: background 0.1s;
	}

	.m-cell:nth-child(7n) { border-right: none; }
	.m-cell:hover         { background: var(--bg2); }
	.m-cell.muted         { cursor: default; background: none; }
	.m-cell.today         { background: color-mix(in srgb, var(--accent) 6%, transparent); }

	.cell-num {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		color: var(--text2);
		width: 1.5em;
		height: 1.5em;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 50%;
	}

	.cell-num.today-num {
		background: var(--accent);
		color: var(--bg-base);
		font-weight: 700;
	}

	.dots-row {
		display: flex;
		flex-wrap: wrap;
		gap: 3px;
		align-items: center;
	}

	.ev-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		border: none;
		cursor: pointer;
		padding: 0;
		flex-shrink: 0;
		transition: transform 0.1s;
	}

	.ev-dot:hover { transform: scale(1.5); }

	.more-pill {
		font-family: var(--font-mono);
		font-size: 0.55rem;
		color: var(--text2);
		line-height: 1;
	}

	/* ── Week view ──────────────────────────────────────────── */
	.week-wrap {
		flex: 1;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow: auto;
		min-height: 0;
	}

	.time-grid {
		display: grid;
		grid-template-columns: 3.5rem repeat(7, 1fr);
		min-width: 520px;
	}

	.grid-corner {
		position: sticky;
		top: 0;
		left: 0;
		background: var(--bg1);
		border-right: 1px solid var(--border);
		border-bottom: 1px solid var(--border);
		z-index: 3;
	}

	.col-hdr {
		position: sticky;
		top: 0;
		background: var(--bg1);
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 0.45rem 0.25rem;
		border-right: 1px solid var(--border);
		border-bottom: 1px solid var(--border);
		z-index: 2;
	}

	.col-hdr.today-col { background: color-mix(in srgb, var(--accent) 6%, var(--bg1)); }

	.col-dow {
		font-family: var(--font-mono);
		font-size: 0.58rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text2);
	}

	.col-date {
		font-family: var(--font-mono);
		font-size: 0.88rem;
		font-weight: 700;
		color: var(--text1);
	}

	.col-date.today-num {
		background: var(--accent);
		color: var(--bg-base);
		border-radius: 50%;
		width: 1.6em;
		height: 1.6em;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.hour-lbl {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text2);
		text-align: right;
		padding: 0.3rem 0.4rem 0 0;
		border-right: 1px solid var(--border);
		border-bottom: 1px solid color-mix(in srgb, var(--border) 40%, transparent);
		height: 3rem;
		box-sizing: border-box;
	}

	.hour-cell {
		border-right: 1px solid color-mix(in srgb, var(--border) 40%, transparent);
		border-bottom: 1px solid color-mix(in srgb, var(--border) 40%, transparent);
		padding: 2px 3px;
		min-height: 3rem;
		cursor: pointer;
		transition: background 0.1s;
	}

	.hour-cell:hover         { background: color-mix(in srgb, var(--accent) 4%, transparent); }
	.hour-cell.today-col     { background: color-mix(in srgb, var(--accent) 4%, transparent); }

	.week-ev {
		display: block;
		width: 100%;
		text-align: left;
		font-family: var(--font-mono);
		font-size: 0.62rem;
		padding: 0.12rem 0.3rem;
		border-left: 2px solid;
		border-top: none;
		border-right: none;
		border-bottom: none;
		border-radius: 0 2px 2px 0;
		cursor: pointer;
		color: var(--text0);
		overflow: hidden;
		white-space: nowrap;
		text-overflow: ellipsis;
		margin-bottom: 1px;
		transition: opacity 0.1s;
	}

	.week-ev:hover { opacity: 0.75; }

	/* ── Day view ───────────────────────────────────────────── */
	.day-wrap {
		flex: 1;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		overflow-y: auto;
		min-height: 0;
	}

	.day-row {
		display: grid;
		grid-template-columns: 3.5rem 1fr;
		border-bottom: 1px solid color-mix(in srgb, var(--border) 50%, transparent);
		min-height: 4rem;
	}

	.day-hour-lbl {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		color: var(--text2);
		text-align: right;
		padding: 0.4rem 0.5rem 0 0;
		border-right: 1px solid var(--border);
		box-sizing: border-box;
	}

	.day-hour-slot {
		padding: 0.25rem 0.6rem;
		cursor: pointer;
		transition: background 0.1s;
	}

	.day-hour-slot:hover { background: color-mix(in srgb, var(--accent) 4%, transparent); }

	.day-ev {
		display: flex;
		flex-direction: column;
		gap: 2px;
		width: 100%;
		text-align: left;
		padding: 0.35rem 0.6rem;
		border-left: 3px solid;
		border-top: none;
		border-right: none;
		border-bottom: none;
		border-radius: 0 5px 5px 0;
		cursor: pointer;
		margin-bottom: 4px;
		transition: opacity 0.1s;
	}

	.day-ev:hover       { opacity: 0.8; }
	.day-ev-time        { font-family: var(--font-mono); font-size: 0.6rem; color: var(--text2); }
	.day-ev-title       { font-family: var(--font-mono); font-size: 0.82rem; font-weight: 700; color: var(--text0); }
	.day-ev-desc        { font-family: var(--font-mono); font-size: 0.7rem; color: var(--text1); }

	/* ── Overlays (shared) ──────────────────────────────────── */
	.overlay-backdrop {
		position: fixed;
		inset: 0;
		z-index: 200;
		background: rgba(0, 0, 0, 0.45);
		display: flex;
		align-items: center;
		justify-content: center;
		cursor: pointer;
	}

	/* ── Detail card ────────────────────────────────────────── */
	.detail-card {
		cursor: default;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		width: min(320px, 90vw);
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
		overflow: hidden;
	}

	.detail-top {
		display: flex;
		align-items: flex-start;
		justify-content: space-between;
		gap: 0.75rem;
		padding: 0.85rem 1rem;
		border-left: 3px solid;
		border-bottom: 1px solid var(--border);
	}

	.detail-info      { flex: 1; min-width: 0; }
	.detail-title     { font-family: var(--font-mono); font-size: 0.88rem; font-weight: 700; color: var(--text0); margin-bottom: 0.15rem; }
	.detail-meta      { font-family: var(--font-mono); font-size: 0.68rem; color: var(--text2); }
	.detail-btns      { display: flex; gap: 0.25rem; flex-shrink: 0; }
	.detail-desc      { font-family: var(--font-mono); font-size: 0.75rem; color: var(--text1); padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); }

	.detail-chips {
		display: flex;
		gap: 0.35rem;
		padding: 0.6rem 1rem;
	}

	.chip {
		font-family: var(--font-mono);
		font-size: 0.6rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.06em;
		padding: 0.1rem 0.4rem;
		border: 1px solid var(--border);
		border-radius: 3px;
		color: var(--text2);
	}

	.chip.accent {
		border-color: color-mix(in srgb, var(--accent) 40%, var(--border));
		color: var(--accent);
	}

	/* ── Modal ──────────────────────────────────────────────── */
	.modal {
		cursor: default;
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: var(--radius);
		width: min(480px, 94vw);
		box-shadow: 0 12px 48px rgba(0, 0, 0, 0.6);
	}

	.modal-hdr {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.75rem 1rem;
		border-bottom: 1px solid var(--border);
	}

	.modal-title {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text1);
	}

	.modal-body {
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 0.75rem;
	}

	.modal-ftr {
		display: flex;
		align-items: center;
		justify-content: flex-end;
		gap: 0.5rem;
		padding: 0.75rem 1rem;
		border-top: 1px solid var(--border);
	}

	/* ── Form elements ──────────────────────────────────────── */
	.field {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		flex: 1;
		min-width: 0;
	}

	.field-row {
		display: flex;
		gap: 0.75rem;
	}

	.check-field {
		flex-direction: row;
		align-items: center;
		gap: 0.5rem;
	}

	.flbl {
		font-family: var(--font-mono);
		font-size: 0.62rem;
		font-weight: 700;
		text-transform: uppercase;
		letter-spacing: 0.07em;
		color: var(--text2);
	}

	.finput {
		font-family: var(--font-mono);
		font-size: 0.78rem;
		color: var(--text0);
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 0.4rem 0.6rem;
		width: 100%;
		box-sizing: border-box;
		outline: none;
		transition: border-color 0.1s;
	}

	.finput:focus { border-color: var(--accent); }

	.ftextarea {
		resize: vertical;
		min-height: 60px;
	}

	.color-row {
		display: flex;
		gap: 0.4rem;
		padding: 0.3rem 0;
	}

	.color-sw {
		width: 22px;
		height: 22px;
		border-radius: 50%;
		border: 2px solid transparent;
		cursor: pointer;
		padding: 0;
		transition: transform 0.1s, border-color 0.1s;
	}

	.color-sw:hover  { transform: scale(1.15); }
	.color-sw.active { border-color: var(--text0); }

	/* ── Action buttons ─────────────────────────────────────── */
	.icon-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 28px;
		height: 28px;
		background: none;
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text2);
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}

	.icon-btn:hover         { color: var(--text0); border-color: var(--text1); }
	.icon-btn.danger:hover  { color: var(--red); border-color: var(--red); }

	.cancel-btn {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		padding: 0.35rem 0.85rem;
		background: none;
		border: 1px solid var(--border);
		border-radius: 4px;
		color: var(--text2);
		cursor: pointer;
		transition: color 0.1s, border-color 0.1s;
	}

	.cancel-btn:hover { color: var(--text0); border-color: var(--text1); }

	.submit-btn {
		font-family: var(--font-mono);
		font-size: 0.72rem;
		font-weight: 700;
		padding: 0.35rem 0.9rem;
		background: var(--accent);
		color: var(--bg-base);
		border: none;
		border-radius: 4px;
		cursor: pointer;
		transition: opacity 0.1s;
	}

	.submit-btn:hover    { opacity: 0.85; }
	.submit-btn:disabled { opacity: 0.4; cursor: not-allowed; }

	@media (max-width: 768px) {
		/* Hide week/day view tabs — month is the only usable view on small screens */
		.view-tabs { display: none; }
	}
</style>
