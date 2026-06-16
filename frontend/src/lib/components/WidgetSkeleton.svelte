<script lang="ts">
	import Skeleton from '$lib/components/Skeleton.svelte';
	export let variant: 'bars' | 'list' | 'cards' = 'bars';
</script>

{#if variant === 'bars'}
	<div class="skel-bars">
		{#each Array(3) as _}
			<div class="bar-row">
				<Skeleton width="34px" height="10px" />
				<Skeleton height="3px" />
				<Skeleton width="38px" height="10px" />
			</div>
		{/each}
	</div>

{:else if variant === 'list'}
	<div class="skel-list">
		{#each (['85%', '60%', '75%', '40%'] as const) as w}
			<div class="list-row">
				<Skeleton width={w} height="10px" />
			</div>
		{/each}
	</div>

{:else if variant === 'cards'}
	<div class="skel-cards">
		<!-- Main: icon + temp -->
		<div class="cards-main">
			<Skeleton width="36px" height="36px" />
			<div class="cards-main-text">
				<Skeleton width="90px" height="22px" />
				<Skeleton width="65px" height="9px" />
			</div>
		</div>
		<!-- Stats row -->
		<div class="cards-stats">
			{#each Array(3) as _}
				<div class="stat-sk">
					<Skeleton width="30px" height="8px" />
					<Skeleton width="38px" height="14px" />
				</div>
			{/each}
		</div>
		<!-- Divider -->
		<div class="cards-div"></div>
		<!-- Forecast strip -->
		<div class="cards-forecast">
			{#each Array(4) as _}
				<div class="forecast-sk">
					<Skeleton width="24px" height="8px" />
					<Skeleton width="20px" height="20px" />
					<Skeleton width="24px" height="8px" />
					<Skeleton width="20px" height="8px" />
				</div>
			{/each}
		</div>
	</div>
{/if}

<style>
	/* ── bars ────────────────────────────────────────────────── */
	.skel-bars {
		display: flex;
		flex-direction: column;
		gap: 11px;
	}

	.bar-row {
		display: flex;
		align-items: center;
		gap: 8px;
	}

	/* ── list ────────────────────────────────────────────────── */
	.skel-list {
		display: flex;
		flex-direction: column;
	}

	.list-row {
		padding: 9px 0;
		border-bottom: 1px solid #21262d;
	}

	.list-row:last-child { border-bottom: none; }

	/* ── cards (weather) ─────────────────────────────────────── */
	.skel-cards {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.cards-main {
		display: flex;
		align-items: center;
		gap: 12px;
		margin-bottom: 0.25rem;
	}

	.cards-main-text {
		display: flex;
		flex-direction: column;
		gap: 7px;
	}

	.cards-stats {
		display: flex;
		gap: 20px;
	}

	.stat-sk {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.cards-div {
		height: 1px;
		background: var(--border);
	}

	.cards-forecast {
		display: flex;
		justify-content: space-between;
	}

	.forecast-sk {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 5px;
	}
</style>
