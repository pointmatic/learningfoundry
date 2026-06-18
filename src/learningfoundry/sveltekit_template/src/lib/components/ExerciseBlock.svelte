<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<!--
  nbfoundry exercise renderer (Story K.f). `status: stub` draws the
  placeholder card; `status: ready` renders the manual-completion view —
  code-scaffold sections (read-only in v1), expected outputs (image URLs
  composed at runtime from `content.id`, plus inline text/table), hints, and
  local-run setup instructions, with a "Mark as Complete" control that
  persists `exercise_status` via progressRepo and fires the upward callbacks.
  Graded `submission` is deferred to a future story.
-->
<script lang="ts">
	import type { ExerciseContent } from '$lib/types/index.js';
	import { progressRepo } from '$lib/db/index.js';
	import PlaceholderBlock from './PlaceholderBlock.svelte';

	interface Props {
		content: ExerciseContent;
		// Typed consumer event mirroring the nbfoundry contract's
		// `ExerciseCompleteEvent` (manual-completion subset).
		oncomplete?: (detail: { exerciseRef: string; status: 'completed' }) => void;
		// No-arg block-completion callback (mirrors `onassessmentcomplete`);
		// the dispatcher wires it to lesson-level block progress.
		onexercisecomplete?: () => void;
	}
	let { content, oncomplete, onexercisecomplete }: Props = $props();

	const isStub = $derived(content.status === 'stub');
	let completed = $state(false);

	async function handleComplete() {
		await progressRepo.updateExerciseStatus(content.id, 'complete');
		completed = true;
		oncomplete?.({ exerciseRef: content.id, status: 'completed' });
		onexercisecomplete?.();
	}
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

		{#if content.sections.length > 0}
			<div class="mt-4 space-y-4">
				{#each content.sections as section}
					<section class="rounded border border-blue-100 bg-white p-3">
						<div class="flex items-center justify-between">
							<h4 class="text-sm font-semibold text-blue-900">{section.title}</h4>
							{#if section.editable}
								<span class="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-800">
									Your code here
								</span>
							{/if}
						</div>
						{#if section.description}
							<!-- eslint-disable-next-line svelte/no-at-html-tags -->
							<div class="prose mt-1 text-xs text-blue-700">{@html section.description}</div>
						{/if}
						<pre class="mt-2 overflow-x-auto rounded bg-slate-900 p-3 text-xs text-slate-100"><code>{section.code}</code></pre>
					</section>
				{/each}
			</div>
		{/if}

		{#if content.expected_outputs.length > 0}
			<div class="mt-4">
				<h4 class="text-sm font-semibold text-blue-900">Expected outputs</h4>
				<div class="mt-2 space-y-3">
					{#each content.expected_outputs as output}
						<div class="text-xs text-blue-800">
							<p class="font-medium">{output.description}</p>
							{#if output.type === 'image'}
								<img
									class="mt-1 max-w-full rounded border border-blue-100"
									src="/exercises/{content.id}/{output.path}"
									alt={output.alt}
									loading="lazy"
								/>
							{:else if output.type === 'text'}
								<p class="mt-1 text-blue-700">{output.content}</p>
							{:else if output.type === 'table'}
								<pre class="mt-1 overflow-x-auto rounded bg-white p-2 text-blue-700">{output.content}</pre>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		{/if}

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

		{#if content.environment}
			<div class="mt-4 rounded border border-blue-100 bg-white p-3 text-xs text-blue-800">
				<h4 class="font-semibold text-blue-900">Run this exercise locally</h4>
				<p class="mt-1">{content.environment.setup_instructions}</p>
				{#if content.environment.dependencies.length > 0}
					<p class="mt-1 text-blue-700">
						Dependencies: {content.environment.dependencies.join(', ')}
					</p>
				{/if}
			</div>
		{/if}

		<button
			type="button"
			class="mt-4 rounded bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 disabled:bg-green-600"
			disabled={completed}
			onclick={handleComplete}
		>
			{completed ? 'Completed' : 'Mark as Complete'}
		</button>
	</div>
{/if}
