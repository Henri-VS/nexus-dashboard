<script lang="ts">
	import { goto } from '$app/navigation';
	import { BASE } from '$lib/api';

	let apiKey = $state('');
	let error = $state('');
	let loading = $state(false);

	async function connect() {
		if (!apiKey.trim()) {
			error = 'API key is required';
			return;
		}
		loading = true;
		error = '';
		try {
			const res = await fetch(`${BASE}/api/auth/verify`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				credentials: 'include',
				body: JSON.stringify({ key: apiKey.trim() }),
			});
			if (!res.ok) {
				error = 'Invalid API key';
				return;
			}
			// Remove old localStorage key — session is now managed by HttpOnly cookie
			localStorage.removeItem('nexus_api_key');
			goto('/');
		} catch {
			error = 'Could not reach the API. Check that Nexus is running.';
		} finally {
			loading = false;
		}
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') connect();
	}
</script>

<svelte:head><title>Nexus — Setup</title></svelte:head>

<div class="overlay">
	<div class="card">
		<div class="logo">NEXUS</div>
		<h1>Setup</h1>
		<p class="subtitle">Enter the API key configured in your <code>NEXUS_SECRET_KEY</code> env var.</p>

		<div class="field">
			<label for="api-key">API Key</label>
			<input
				id="api-key"
				type="password"
				bind:value={apiKey}
				placeholder="your-secret-key"
				onkeydown={handleKeydown}
				autofocus
			/>
		</div>

		{#if error}
			<p class="error">{error}</p>
		{/if}

		<button onclick={connect} disabled={loading}>{loading ? 'Connecting…' : 'Connect'}</button>
	</div>
</div>

<style>
	.overlay {
		position: fixed;
		inset: 0;
		z-index: 9999;
		background: var(--bg0);
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.card {
		background: var(--bg1);
		border: 1px solid var(--border);
		border-radius: 8px;
		padding: 2rem;
		width: 100%;
		max-width: 400px;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}

	.logo {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.7rem;
		font-weight: 700;
		letter-spacing: 0.25em;
		color: var(--accent);
		margin-bottom: -0.25rem;
	}

	h1 {
		font-family: 'JetBrains Mono', monospace;
		font-size: 1.5rem;
		color: var(--text0);
		margin: 0;
	}

	.subtitle {
		color: var(--text1);
		font-size: 0.85rem;
		margin: 0;
		line-height: 1.5;
	}

	code {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.8rem;
		color: var(--accent);
		background: var(--bg2);
		padding: 0.1em 0.3em;
		border-radius: 3px;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 0.375rem;
	}

	label {
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.08em;
		color: var(--text1);
	}

	input {
		background: var(--bg2);
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 0.5rem 0.75rem;
		color: var(--text0);
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.875rem;
		width: 100%;
		box-sizing: border-box;
		transition: border-color 0.15s;
	}

	input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.error {
		color: var(--red);
		font-size: 0.8rem;
		font-family: 'JetBrains Mono', monospace;
		margin: 0;
	}

	button {
		background: var(--accent);
		color: var(--bg0);
		border: none;
		border-radius: 4px;
		padding: 0.625rem 1rem;
		font-family: 'JetBrains Mono', monospace;
		font-size: 0.875rem;
		font-weight: 700;
		cursor: pointer;
		width: 100%;
		letter-spacing: 0.03em;
		transition: opacity 0.15s;
	}

	button:hover {
		opacity: 0.85;
	}
</style>
