<script lang="ts">
	import { onMount } from 'svelte';
	
	let projects = $state<any[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	
	onMount(async () => {
		try {
			// For now, we'll use static data
			// In the future, this will fetch from the backend API
			projects = [
				{ name: 'Spring Boot', hasApi: true, hasReference: true },
				{ name: 'Spring Framework', hasApi: true, hasReference: true },
				{ name: 'Spring Security', hasApi: false, hasReference: true },
				{ name: 'Spring Cloud', hasApi: false, hasReference: true }
			];
			loading = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load projects';
			loading = false;
		}
	});
</script>

<div class="container">
	<header>
		<h1>🌱 Spring Documentation Browser</h1>
		<p class="subtitle">Browse local copies of Spring project documentation</p>
	</header>
	
	{#if loading}
		<div class="loading">Loading projects...</div>
	{:else if error}
		<div class="error">Error: {error}</div>
	{:else}
		<div class="projects-grid">
			{#each projects as project}
				<div class="project-card">
					<h2 class="project-name">{project.name}</h2>
					<div class="doc-links">
						{#if project.hasApi}
							<a href="/docs/{project.name.toLowerCase().replace(' ', '-')}/current/api/index.html" class="doc-link">API Docs</a>
						{/if}
						{#if project.hasReference}
							<a href="/docs/{project.name.toLowerCase().replace(' ', '-')}/current/reference/index.html" class="doc-link">Reference</a>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<style>
	.container {
		max-width: 1200px;
		margin: 0 auto;
		padding: 2rem;
	}
	
	header {
		text-align: center;
		margin-bottom: 3rem;
	}
	
	h1 {
		color: #6db33f;
		font-size: 2.5rem;
		margin-bottom: 0.5rem;
	}
	
	.subtitle {
		color: #666;
		font-size: 1.2rem;
	}
	
	.loading, .error {
		text-align: center;
		padding: 2rem;
		font-size: 1.2rem;
	}
	
	.error {
		color: #d32f2f;
	}
	
	.projects-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
		gap: 1.5rem;
	}
	
	.project-card {
		background: white;
		border: 1px solid #e0e0e0;
		border-radius: 8px;
		padding: 1.5rem;
		transition: transform 0.2s, box-shadow 0.2s;
	}
	
	.project-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 12px rgba(0,0,0,0.1);
	}
	
	.project-name {
		font-size: 1.3rem;
		margin-bottom: 1rem;
		color: #333;
	}
	
	.doc-links {
		display: flex;
		gap: 1rem;
	}
	
	.doc-link {
		text-decoration: none;
		color: #6db33f;
		padding: 0.5rem 1rem;
		border: 1px solid #6db33f;
		border-radius: 4px;
		font-weight: 500;
		transition: background-color 0.2s, color 0.2s;
	}
	
	.doc-link:hover {
		background-color: #6db33f;
		color: white;
	}
	
	:global(body) {
		margin: 0;
		background-color: #f5f5f5;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
	}
</style>