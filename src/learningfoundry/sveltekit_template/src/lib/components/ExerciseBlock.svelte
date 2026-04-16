<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import type { ExerciseContent } from '$lib/types/index.js';
	import PlaceholderBlock from './PlaceholderBlock.svelte';

	interface Props {
		content: ExerciseContent;
	}
	let { content }: Props = $props();

	const isStub = $derived(content.status === 'stub');
</script>

{#if isStub}
	<PlaceholderBlock
		label="Exercise: {content.title}"
		message="nbfoundry integration pending."
	/>
{:else}
	<div class="rounded-lg border border-blue-200 bg-blue-50 p-6">
		<h3 class="text-base font-semibold text-blue-900">{content.title}</h3>
		<!-- eslint-disable-next-line svelte/no-at-html-tags -->
		<div class="prose mt-2 text-sm text-blue-800">{@html content.instructions}</div>
		{#if content.hints.length > 0}
			<details class="mt-4">
				<summary class="cursor-pointer text-xs text-blue-600">Hints</summary>
				<ul class="mt-2 list-disc pl-4 text-xs text-blue-700">
					{#each content.hints as hint}
						<li>{hint}</li>
					{/each}
				</ul>
			</details>
		{/if}
	</div>
{/if}
