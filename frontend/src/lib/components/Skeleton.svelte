<script lang="ts">
	export let width: string = '100%';
	export let height: string = '10px';
	export let rounded: boolean = false;
</script>

<span
	class="sk"
	class:rounded
	style="width:{width};height:{height}"
	aria-hidden="true"
></span>

<style>
	.sk {
		display: block;
		background: linear-gradient(90deg, #21262d 25%, #2c3440 50%, #21262d 75%);
		background-size: 500px 100%;
		animation: shimmer 1.4s infinite;
		border-radius: 3px;
		flex-shrink: 0;
	}
	.sk.rounded { border-radius: 50%; }
</style>
