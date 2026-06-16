<script lang="ts">
	import { onMount } from 'svelte';
	import { services as servicesApi, type Service } from '$lib/api';
	import Card from '$lib/components/Card.svelte';
	import WidgetSkeleton from '$lib/components/WidgetSkeleton.svelte';
	import EmptyState from '$lib/components/EmptyState.svelte';
	import {
		Globe, Play, Box, Shield, Database, Lock, Cpu, Terminal,
		Wifi, Server, Home, Zap, BookOpen, Music, Camera, Monitor,
		Activity, Code, Layers,
	} from '@lucide/svelte';

	type LucideIcon = typeof Globe;

	const ICON_MAP: Record<string, LucideIcon> = {
		globe: Globe, play: Play, box: Box, shield: Shield,
		database: Database, lock: Lock, cpu: Cpu, terminal: Terminal,
		wifi: Wifi, server: Server, home: Home, zap: Zap,
		book: BookOpen, music: Music, camera: Camera, monitor: Monitor,
		activity: Activity, code: Code, layers: Layers,
	};

	function getIcon(name: string): LucideIcon {
		return ICON_MAP[name.toLowerCase()] ?? Globe;
	}

	// ── State ─────────────────────────────────────────────────────
	let allServices: Service[] = [];
	let statuses: Record<string, { online: boolean | null; ms: number | null }> = {};
	let loading = true;
	let skeletonMinShown = false;

	$: displayed = allServices.filter((s) => s.enabled).slice(0, 6);
	$: extraCount = Math.max(0, allServices.filter((s) => s.enabled).length - 6);

	async function load() {
		const res = await servicesApi.list();
		allServices = res?.services ?? [];
		loading = false;
		for (const s of allServices.filter((s) => s.enabled)) {
			statuses[s.id] = { online: null, ms: null };
			servicesApi
				.ping(s.url)
				.then((r) => {
					statuses[s.id] = r ? { online: r.online, ms: r.latency_ms } : { online: false, ms: null };
					statuses = { ...statuses };
				})
				.catch(() => {
					statuses[s.id] = { online: false, ms: null };
					statuses = { ...statuses };
				});
		}
	}

	onMount(() => {
		setTimeout(() => { skeletonMinShown = true; }, 400);
		load();
	});
</script>

<Card label="services" accentColor="var(--accent2)" {loading} mocked={false}>
	{#if !skeletonMinShown || loading}
		<WidgetSkeleton variant="list" />
	{:else if displayed.length === 0}
		<EmptyState
			variant="not-configured"
			title="No services"
			body="Add services on the Services page."
			primaryAction="Go to Services"
			primaryHref="/home"
			size="compact"
		/>
	{:else}
		<ul class="svc-list">
			{#each displayed as svc (svc.id)}
				{@const st = statuses[svc.id]}
				<li class="svc-row">
					<a href={svc.url} target="_blank" rel="noopener noreferrer" class="svc-link">
						<span class="svc-icon-wrap">
							<svelte:component this={getIcon(svc.icon)} size={12} strokeWidth={1.6} />
						</span>
						<span class="svc-name">{svc.name}</span>
					</a>
					<span
						class="svc-dot"
						class:dot-checking={st === undefined || st.online === null}
						class:dot-online={st?.online === true}
						class:dot-offline={st?.online === false}
						title={st?.online === true
							? (st.ms !== null ? `${st.ms}ms` : 'Online')
							: st?.online === false ? 'Offline' : 'Checking…'}
					></span>
				</li>
			{/each}
		</ul>
		<div class="footer-link">
			<a href="/home">
				{extraCount > 0 ? `+${extraCount} more →` : 'View all →'}
			</a>
		</div>
	{/if}
</Card>

<style>
	.svc-list {
		list-style: none;
		padding: 0;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
	}

	.svc-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 0.3rem 0.25rem;
		border-radius: 4px;
		transition: background 0.1s;
	}
	.svc-row:hover { background: var(--bg2); }

	.svc-link {
		flex: 1;
		display: flex;
		align-items: center;
		gap: 0.45rem;
		text-decoration: none;
		min-width: 0;
	}

	.svc-icon-wrap {
		flex-shrink: 0;
		color: var(--accent2);
		display: flex;
		align-items: center;
	}

	.svc-name {
		font-family: var(--font-ui);
		font-size: 0.8rem;
		color: var(--text0);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.svc-dot {
		width: 6px;
		height: 6px;
		border-radius: 50%;
		flex-shrink: 0;
	}
	.dot-checking { background: var(--text2); }
	.dot-online   { background: var(--green); }
	.dot-offline  { background: var(--red); }

	.footer-link {
		margin-top: 0.5rem;
		padding-top: 0.5rem;
		border-top: 1px solid var(--border);
	}

	.footer-link a {
		font-family: var(--font-mono);
		font-size: 0.7rem;
		color: var(--text2);
		text-decoration: none;
		transition: color 0.1s;
	}
	.footer-link a:hover { color: var(--accent2); }
</style>
