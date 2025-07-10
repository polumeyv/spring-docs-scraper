<script lang="ts">
	import { onMount } from 'svelte';
	
	interface DocLink {
		title: string;
		url: string;
		type: 'official' | 'tutorial' | 'api' | 'reference' | 'github';
		description?: string;
	}
	
	interface SearchResult {
		framework: string;
		links: DocLink[];
		timestamp: Date;
	}
	
	let searchQuery = $state('');
	let searchResults = $state<SearchResult | null>(null);
	let recentSearches = $state<SearchResult[]>([]);
	let loading = $state(false);
	let error = $state<string | null>(null);
	let selectedFolder = $state<string>('');
	let availableFolders = $state<string[]>([]);
	let showCreateFolder = $state(false);
	let newFolderName = $state('');
	
	onMount(async () => {
		// Load recent searches from localStorage
		const saved = localStorage.getItem('recentSearches');
		if (saved) {
			recentSearches = JSON.parse(saved);
		}
		
		// Load available folders
		loadFolders();
	});
	
	async function searchDocumentation() {
		if (!searchQuery.trim()) return;
		
		loading = true;
		error = null;
		
		try {
			// TODO: Replace with actual API call
			const response = await fetch(`/api/search-docs?q=${encodeURIComponent(searchQuery)}`);
			
			if (!response.ok) {
				throw new Error('Failed to search documentation');
			}
			
			const data = await response.json();
			searchResults = {
				framework: searchQuery,
				links: data.links,
				timestamp: new Date()
			};
			
			// Add to recent searches
			recentSearches = [searchResults, ...recentSearches.filter(s => s.framework !== searchQuery)].slice(0, 5);
			localStorage.setItem('recentSearches', JSON.stringify(recentSearches));
			
		} catch (err) {
			error = 'Failed to search for documentation. Please try again.';
			console.error('Search error:', err);
		} finally {
			loading = false;
		}
	}
	async function loadFolders() {
		try {
			const response = await fetch('/api/folders');
			if (response.ok) {
				const data = await response.json();
				availableFolders = data.folders.map((f: any) => f.name);
			}
		} catch (err) {
			console.error('Failed to load folders:', err);
		}
	}
	
	async function createFolder() {
		if (!newFolderName.trim()) return;
		
		try {
			const response = await fetch('/api/folders', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ name: newFolderName })
			});
			
			if (response.ok) {
				await loadFolders();
				selectedFolder = newFolderName;
				newFolderName = '';
				showCreateFolder = false;
			} else {
				const data = await response.json();
				alert(data.error || 'Failed to create folder');
			}
		} catch (err) {
			alert('Failed to create folder');
		}
	}
	
	async function scrapeDocumentation(link: DocLink) {
		if (!selectedFolder) {
			alert('Please select a folder to save the documentation');
			return;
		}
		
		try {
			const response = await fetch('/api/scrape', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					url: link.url,
					folder: selectedFolder,
					framework: searchResults?.framework || 'unknown'
				})
			});
			
			if (response.ok) {
				const data = await response.json();
				alert(`Started scraping ${link.title}. Check the ${selectedFolder} folder for the downloaded documentation.`);
			} else {
				alert('Failed to start scraping');
			}
		} catch (err) {
			alert('Failed to scrape documentation');
		}
	}
</script>

<div class="container">
	<header>
		<h1>📚 Developer Documentation Scraper</h1>
		<p class="subtitle">Search and download documentation for any framework or tool</p>
	</header>
	
	<div class="search-section">
		<div class="search-container">
			<input 
				type="text" 
				bind:value={searchQuery}
				placeholder="Enter framework or tool name (e.g., React, Django, FastAPI...)"
				class="search-input"
				onkeypress={(e) => e.key === 'Enter' && searchDocumentation()}
			/>
			<button 
				onclick={searchDocumentation} 
				disabled={loading || !searchQuery.trim()}
				class="search-button"
			>
				{loading ? 'Searching...' : 'Search'}
			</button>
		</div>
		
		<div class="folder-section">
			{#if showCreateFolder}
				<div class="create-folder-form">
					<input
						type="text"
						bind:value={newFolderName}
						placeholder="Enter new folder name"
						class="folder-input"
						onkeypress={(e) => e.key === 'Enter' && createFolder()}
					/>
					<button onclick={createFolder} class="create-btn">Create</button>
					<button onclick={() => { showCreateFolder = false; newFolderName = ''; }} class="cancel-btn">Cancel</button>
				</div>
			{:else}
				<div class="folder-selector">
					<select bind:value={selectedFolder} class="folder-select">
						<option value="">Select a folder...</option>
						{#each availableFolders as folder}
							<option value={folder}>{folder}</option>
						{/each}
					</select>
					<button onclick={() => showCreateFolder = true} class="new-folder-btn">
						📁 New Folder
					</button>
				</div>
			{/if}
		</div>
	</div>
	
	{#if error}
		<div class="error">Error: {error}</div>
	{/if}
	
	{#if searchResults}
		<div class="results-section">
			<h2>Documentation for {searchResults.framework}</h2>
			<div class="doc-links-grid">
				{#each searchResults.links as link}
					<div class="doc-card">
						<div class="doc-header">
							<span class="doc-type doc-type-{link.type}">{link.type}</span>
							<h3>{link.title}</h3>
						</div>
						{#if link.description}
							<p class="doc-description">{link.description}</p>
						{/if}
						<div class="doc-actions">
							<a href={link.url} target="_blank" rel="noopener" class="view-link">View Online</a>
							<button onclick={() => scrapeDocumentation(link)} class="scrape-button">
								Download
							</button>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}
	
	{#if recentSearches.length > 0}
		<div class="recent-section">
			<h2>Recent Searches</h2>
			<div class="recent-searches">
				{#each recentSearches as search}
					<button 
						onclick={() => { searchQuery = search.framework; searchDocumentation(); }}
						class="recent-search-btn"
					>
						{search.framework}
					</button>
				{/each}
			</div>
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
		color: #2563eb;
		font-size: 2.5rem;
		margin-bottom: 0.5rem;
	}
	
	.subtitle {
		color: #666;
		font-size: 1.2rem;
	}
	
	.search-section {
		margin-bottom: 2rem;
	}
	
	.search-container {
		display: flex;
		gap: 1rem;
		margin-bottom: 1rem;
	}
	
	.search-input {
		flex: 1;
		padding: 0.75rem 1rem;
		font-size: 1rem;
		border: 2px solid #e5e7eb;
		border-radius: 8px;
		transition: border-color 0.2s;
	}
	
	.search-input:focus {
		outline: none;
		border-color: #2563eb;
	}
	
	.search-button {
		padding: 0.75rem 2rem;
		font-size: 1rem;
		font-weight: 600;
		color: white;
		background-color: #2563eb;
		border: none;
		border-radius: 8px;
		cursor: pointer;
		transition: background-color 0.2s;
	}
	
	.search-button:hover:not(:disabled) {
		background-color: #1d4ed8;
	}
	
	.search-button:disabled {
		background-color: #9ca3af;
		cursor: not-allowed;
	}
	
	.folder-section {
		margin-top: 1rem;
	}
	
	.folder-selector {
		display: flex;
		gap: 1rem;
		align-items: center;
	}
	
	.folder-select {
		flex: 1;
		padding: 0.75rem 1rem;
		font-size: 1rem;
		border: 2px solid #e5e7eb;
		border-radius: 8px;
		background-color: white;
		cursor: pointer;
		transition: border-color 0.2s;
	}
	
	.folder-select:focus {
		outline: none;
		border-color: #2563eb;
	}
	
	.new-folder-btn {
		padding: 0.75rem 1.5rem;
		font-size: 0.9rem;
		color: #2563eb;
		background-color: white;
		border: 1px solid #2563eb;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.2s;
	}
	
	.new-folder-btn:hover {
		background-color: #2563eb;
		color: white;
	}
	
	.create-folder-form {
		display: flex;
		gap: 0.75rem;
		align-items: center;
	}
	
	.folder-input {
		flex: 1;
		padding: 0.75rem 1rem;
		font-size: 1rem;
		border: 2px solid #e5e7eb;
		border-radius: 8px;
		transition: border-color 0.2s;
	}
	
	.folder-input:focus {
		outline: none;
		border-color: #2563eb;
	}
	
	.create-btn, .cancel-btn {
		padding: 0.75rem 1.5rem;
		font-size: 0.9rem;
		border: none;
		border-radius: 8px;
		cursor: pointer;
		transition: all 0.2s;
	}
	
	.create-btn {
		color: white;
		background-color: #10b981;
	}
	
	.create-btn:hover {
		background-color: #059669;
	}
	
	.cancel-btn {
		color: #6b7280;
		background-color: #f3f4f6;
	}
	
	.cancel-btn:hover {
		background-color: #e5e7eb;
	}
	
	.error {
		text-align: center;
		padding: 1rem;
		margin: 1rem 0;
		color: #dc2626;
		background-color: #fee2e2;
		border-radius: 8px;
	}
	
	.results-section {
		margin-top: 3rem;
	}
	
	.results-section h2 {
		color: #1f2937;
		margin-bottom: 1.5rem;
	}
	
	.doc-links-grid {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
		gap: 1.5rem;
	}
	
	.doc-card {
		background: white;
		border: 1px solid #e5e7eb;
		border-radius: 12px;
		padding: 1.5rem;
		transition: transform 0.2s, box-shadow 0.2s;
	}
	
	.doc-card:hover {
		transform: translateY(-2px);
		box-shadow: 0 4px 20px rgba(0,0,0,0.08);
	}
	
	.doc-header {
		margin-bottom: 1rem;
	}
	
	.doc-type {
		display: inline-block;
		padding: 0.25rem 0.75rem;
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
		border-radius: 4px;
		margin-bottom: 0.5rem;
	}
	
	.doc-type-official {
		background-color: #dbeafe;
		color: #1e40af;
	}
	
	.doc-type-api {
		background-color: #fce7f3;
		color: #be185d;
	}
	
	.doc-type-tutorial {
		background-color: #d1fae5;
		color: #065f46;
	}
	
	.doc-type-github {
		background-color: #e5e7eb;
		color: #374151;
	}
	
	.doc-type-reference {
		background-color: #fef3c7;
		color: #92400e;
	}
	
	.doc-header h3 {
		margin: 0;
		color: #1f2937;
		font-size: 1.1rem;
	}
	
	.doc-description {
		color: #6b7280;
		font-size: 0.9rem;
		margin-bottom: 1rem;
		line-height: 1.5;
	}
	
	.doc-actions {
		display: flex;
		gap: 0.75rem;
	}
	
	.view-link, .scrape-button {
		flex: 1;
		padding: 0.5rem 1rem;
		text-align: center;
		font-size: 0.9rem;
		font-weight: 500;
		border-radius: 6px;
		text-decoration: none;
		transition: all 0.2s;
		cursor: pointer;
	}
	
	.view-link {
		color: #2563eb;
		background-color: #eff6ff;
		border: 1px solid #bfdbfe;
	}
	
	.view-link:hover {
		background-color: #dbeafe;
		border-color: #93c5fd;
	}
	
	.scrape-button {
		color: white;
		background-color: #10b981;
		border: none;
	}
	
	.scrape-button:hover {
		background-color: #059669;
	}
	
	.recent-section {
		margin-top: 3rem;
		padding-top: 2rem;
		border-top: 1px solid #e5e7eb;
	}
	
	.recent-section h2 {
		color: #6b7280;
		font-size: 1.2rem;
		margin-bottom: 1rem;
	}
	
	.recent-searches {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
	}
	
	.recent-search-btn {
		padding: 0.5rem 1rem;
		font-size: 0.9rem;
		color: #4b5563;
		background-color: #f3f4f6;
		border: 1px solid #e5e7eb;
		border-radius: 20px;
		cursor: pointer;
		transition: all 0.2s;
	}
	
	.recent-search-btn:hover {
		background-color: #e5e7eb;
		border-color: #d1d5db;
	}
	
	:global(body) {
		margin: 0;
		background-color: #f9fafb;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
	}
</style>