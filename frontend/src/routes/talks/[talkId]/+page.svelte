<script lang="ts">
	/**
	 * Study View - Main page for studying a talk with synced audio and text.
	 *
	 * Allows selecting audio and text languages independently.
	 * Shows AudioPlayer and SyncedText components with highlighting.
	 */

	import { page } from '$app/stores';
	import { onMount, onDestroy } from 'svelte';
	import type { Talk, Alignment } from '$lib/api/types';
	import { talksApi, type TextContent } from '$lib/api/talks';
	import { playbackStore } from '$lib/stores/playback.svelte';
	import AudioPlayer from '$lib/components/audio/AudioPlayer.svelte';
	import SyncedText from '$lib/components/text/SyncedText.svelte';

	// Route parameter
	let talkId = $derived($page.params.talkId ?? '');

	// Page state
	let talk = $state<Talk | null>(null);
	let textContent = $state<TextContent | null>(null);
	let alignment = $state<Alignment | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Language selection (default to first available)
	let audioLanguage = $state<string>('');
	let textLanguage = $state<string>('');

	// Derived
	let audioUrl = $derived(
		talk && audioLanguage && talkId ? talksApi.getAudioUrl(talkId, audioLanguage) : ''
	);

	onMount(async () => {
		await loadTalk();
	});

	onDestroy(() => {
		playbackStore.reset();
	});

	async function loadTalk() {
		loading = true;
		error = null;

		try {
			talk = await talksApi.getById(talkId);

			if (talk.available_languages.length === 0) {
				error = 'This talk has no available languages.';
				return;
			}

			// Default to first language for both
			audioLanguage = talk.available_languages[0];
			textLanguage = talk.available_languages[0];

			// Load text content and alignment
			await loadTextContent();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load talk';
		} finally {
			loading = false;
		}
	}

	async function loadTextContent() {
		if (!textLanguage) return;

		try {
			textContent = await talksApi.getText(talkId, textLanguage);

			// Load alignment if available for audio language (for synced playback)
			if (audioLanguage) {
				alignment = await talksApi.getAlignment(talkId, audioLanguage);
				playbackStore.setAlignment(alignment);
			}
		} catch {
			textContent = null;
			alignment = null;
			playbackStore.setAlignment(null);
		}
	}

	async function handleAudioLanguageChange(event: Event) {
		const select = event.target as HTMLSelectElement;
		audioLanguage = select.value;
		playbackStore.reset();

		// Reload alignment for new audio language
		alignment = await talksApi.getAlignment(talkId, audioLanguage);
		playbackStore.setAlignment(alignment);
	}

	async function handleTextLanguageChange(event: Event) {
		const select = event.target as HTMLSelectElement;
		textLanguage = select.value;
		await loadTextContent();
	}

	function handleAudioLoad() {
		// Audio metadata loaded successfully
	}

	// Language names for display
	const languageNames: Record<string, string> = {
		eng: 'English',
		zhs: 'Chinese (Simplified)',
		zht: 'Chinese (Traditional)',
		spa: 'Spanish',
		por: 'Portuguese',
		fra: 'French',
		deu: 'German',
		ita: 'Italian',
		jpn: 'Japanese',
		kor: 'Korean',
		rus: 'Russian',
		ces: 'Czech'
	};

	function getLanguageName(code: string): string {
		return languageNames[code] || code.toUpperCase();
	}
</script>

<svelte:head>
	<title>{talk?.title || 'Loading...'} - Gospel Language Study</title>
</svelte:head>

<div class="study-view">
	{#if loading}
		<div class="loading">
			<p>Loading talk...</p>
		</div>
	{:else if error}
		<div class="error-container">
			<p class="error">{error}</p>
			<a href="/" class="back-link">Back to talks</a>
		</div>
	{:else if talk}
		<header class="talk-header">
			<a href="/" class="back-link">Back to talks</a>
			<h1>{talk.title}</h1>
			<p class="talk-meta">{talk.speaker} - {talk.conference}</p>
		</header>

		<div class="language-controls">
			<div class="language-select">
				<label for="audio-language">Listen in:</label>
				<select id="audio-language" value={audioLanguage} onchange={handleAudioLanguageChange}>
					{#each talk.available_languages as lang (lang)}
						<option value={lang}>{getLanguageName(lang)}</option>
					{/each}
				</select>
			</div>

			<div class="language-select">
				<label for="text-language">Read in:</label>
				<select id="text-language" value={textLanguage} onchange={handleTextLanguageChange}>
					{#each talk.available_languages as lang (lang)}
						<option value={lang}>{getLanguageName(lang)}</option>
					{/each}
				</select>
			</div>
		</div>

		{#if audioUrl}
			<div class="player-container">
				<AudioPlayer src={audioUrl} onload={handleAudioLoad} />
			</div>
		{/if}

		<div class="text-container">
			{#if audioLanguage === textLanguage && alignment}
				<SyncedText {alignment} />
			{:else}
				<SyncedText alignment={null} plainText={textContent?.text_content || ''} />
			{/if}
		</div>
	{/if}
</div>

<style>
	.study-view {
		max-width: 900px;
		margin: 0 auto;
	}

	.loading,
	.error-container {
		padding: var(--spacing-xl);
		text-align: center;
	}

	.error {
		color: #dc2626;
		margin-bottom: var(--spacing-md);
	}

	.back-link {
		display: inline-block;
		color: var(--color-primary);
		text-decoration: none;
		margin-bottom: var(--spacing-md);
	}

	.back-link:hover {
		text-decoration: underline;
	}

	.talk-header {
		margin-bottom: var(--spacing-lg);
	}

	.talk-header h1 {
		margin: 0 0 var(--spacing-xs);
		font-size: 1.75rem;
	}

	.talk-meta {
		color: var(--color-text-secondary);
		margin: 0;
	}

	.language-controls {
		display: flex;
		gap: var(--spacing-lg);
		flex-wrap: wrap;
		margin-bottom: var(--spacing-lg);
		padding: var(--spacing-md);
		background: var(--color-bg-secondary);
		border-radius: var(--radius-md);
	}

	.language-select {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
	}

	.language-select label {
		font-weight: 500;
		color: var(--color-text-secondary);
	}

	.language-select select {
		padding: var(--spacing-xs) var(--spacing-sm);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-sm);
		background: white;
		font-size: 1rem;
		cursor: pointer;
	}

	.language-select select:focus {
		outline: 2px solid var(--color-primary);
		outline-offset: 2px;
	}

	.player-container {
		position: sticky;
		top: 0;
		z-index: 10;
		background: white;
		margin-bottom: var(--spacing-lg);
		box-shadow: var(--shadow-sm);
		border-radius: var(--radius-md);
	}

	.text-container {
		padding-bottom: var(--spacing-xl);
	}
</style>
