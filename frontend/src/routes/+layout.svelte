<script lang="ts">
	import '../app.css';

	interface Props {
		children: import('svelte').Snippet;
	}

	let { children }: Props = $props();
</script>

<div class="app">
	<header>
		<nav class="container">
			<a href="/" class="logo">Gospel Language Study</a>
			<ul class="nav-links">
				<li><a href="/talks">Talks</a></li>
				<li><a href="/vocabulary">Vocabulary</a></li>
				<li><a href="/settings">Settings</a></li>
			</ul>
		</nav>
	</header>

	<main class="container">
		{@render children()}
	</main>

	<footer class="container">
		<p class="text-secondary text-center">Personal language study tool</p>
	</footer>
</div>

<style>
	.app {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}

	header {
		border-bottom: 1px solid var(--color-border);
		padding: var(--spacing-md) 0;
	}

	nav {
		display: flex;
		align-items: center;
		justify-content: space-between;
	}

	.logo {
		font-weight: 600;
		font-size: 1.25rem;
		color: var(--color-text);
	}

	.logo:hover {
		text-decoration: none;
		color: var(--color-primary);
	}

	.nav-links {
		display: flex;
		gap: var(--spacing-lg);
		list-style: none;
		margin: 0;
		padding: 0;
	}

	main {
		flex: 1;
		padding: var(--spacing-xl) var(--spacing-md);
	}

	footer {
		padding: var(--spacing-lg) 0;
		border-top: 1px solid var(--color-border);
	}
</style>
