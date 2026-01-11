<script lang="ts">
	import { onMount } from 'svelte';
	import type { Talk } from '$lib/api/types';
	import { talksApi } from '$lib/api/talks';

	let talks = $state<Talk[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			talks = await talksApi.getAll();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load talks';
		} finally {
			loading = false;
		}
	});
</script>

<svelte:head>
	<title>Gospel Language Study</title>
</svelte:head>

<div class="home">
	<h1>Gospel Language Study</h1>
	<p class="intro">
		Learn languages through General Conference talks. Listen in one language while reading in
		another.
	</p>

	<section class="talks-section">
		<h2>Available Talks</h2>

		{#if loading}
			<p class="text-secondary">Loading talks...</p>
		{:else if error}
			<p class="error">{error}</p>
		{:else if talks.length === 0}
			<p class="text-secondary">No talks available yet. Add talks to the data/talks directory.</p>
		{:else}
			<ul class="talks-list">
				{#each talks as talk (talk.id)}
					<li class="talk-card">
						<a href="/talks/{talk.id}">
							<h3>{talk.title}</h3>
							<p class="talk-meta">
								{talk.speaker} &bull; {talk.conference}
							</p>
							<div class="talk-languages">
								{#each talk.available_languages as lang (lang)}
									<span class="language-tag">{lang}</span>
								{/each}
							</div>
						</a>
					</li>
				{/each}
			</ul>
		{/if}
	</section>
</div>

<style>
	.home {
		max-width: 800px;
		margin: 0 auto;
	}

	.intro {
		font-size: 1.125rem;
		color: var(--color-text-secondary);
		margin-bottom: var(--spacing-xl);
	}

	.talks-section {
		margin-top: var(--spacing-xl);
	}

	.talks-list {
		list-style: none;
		padding: 0;
		display: grid;
		gap: var(--spacing-md);
	}

	.talk-card {
		background: var(--color-bg-secondary);
		border-radius: var(--radius-md);
		transition: box-shadow 0.2s;
	}

	.talk-card:hover {
		box-shadow: var(--shadow-md);
	}

	.talk-card a {
		display: block;
		padding: var(--spacing-lg);
		color: inherit;
		text-decoration: none;
	}

	.talk-card h3 {
		margin: 0 0 var(--spacing-sm);
		color: var(--color-text);
	}

	.talk-meta {
		margin: 0 0 var(--spacing-sm);
		color: var(--color-text-secondary);
		font-size: 0.875rem;
	}

	.talk-languages {
		display: flex;
		gap: var(--spacing-xs);
		flex-wrap: wrap;
	}

	.language-tag {
		background: var(--color-primary);
		color: white;
		padding: 2px 8px;
		border-radius: var(--radius-sm);
		font-size: 0.75rem;
		text-transform: uppercase;
	}

	.error {
		color: #dc2626;
	}
</style>
