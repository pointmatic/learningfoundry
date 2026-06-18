<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<!--
  nbfoundry exercise renderer (Story K.j.1, Option C). `status: stub` draws the
  placeholder card; `status: ready` renders the launch banner — the exercise
  runs as a live marimo notebook the learner starts with the `learningfoundry
  launch` CLI (a static page can't spawn a process). The banner shows the
  copy-able launch command, an "Open Exercise" link to the local marimo server,
  and a "Mark as Complete" control that persists `exercise_status` via
  progressRepo and fires the upward callbacks. The completed slate is derived on
  load from the persisted status.
-->
<script lang="ts">
	import { onMount } from 'svelte';
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
	const launchCommand = $derived(`learningfoundry launch ${content.id}`);
	const launchUrl = $derived(`http://localhost:${content.port}`);

	let completed = $state(false);
	let copied = $state(false);

	// Derive the completed slate on load from the persisted status.
	onMount(async () => {
		if (isStub) return;
		const status = await progressRepo.getExerciseStatus(content.id);
		if (status === 'complete') completed = true;
	});

	async function copyCommand() {
		await navigator.clipboard.writeText(launchCommand);
		copied = true;
		setTimeout(() => (copied = false), 2000);
	}

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
		<div class="prose mt-2 text-sm text-blue-800">{@html content.description}</div>

		<div class="mt-4 rounded border border-blue-100 bg-white p-3">
			<p class="text-xs font-semibold text-blue-900">Run this exercise locally</p>
			<p class="mt-1 text-xs text-blue-700">
				Start the live notebook, then open it in a new tab:
			</p>
			<div class="mt-2 flex items-center gap-2">
				<code
					class="flex-1 overflow-x-auto rounded bg-slate-900 px-3 py-2 text-xs text-slate-100"
					>{launchCommand}</code
				>
				<button
					type="button"
					class="shrink-0 rounded bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
					onclick={copyCommand}
				>
					{copied ? 'Copied ✓' : 'Copy'}
				</button>
			</div>
			<a
				class="mt-2 inline-block text-xs font-semibold text-blue-700 underline hover:text-blue-900"
				href={launchUrl}
				target="_blank"
				rel="noopener noreferrer"
			>
				Open Exercise ↗
			</a>
			{#if content.environment && content.environment.dependencies.length > 0}
				<p class="mt-2 text-xs text-blue-600">
					Prerequisites: {content.environment.dependencies.join(', ')}
				</p>
			{/if}
		</div>

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

		{#if completed}
			<p class="mt-4 text-xs font-semibold text-green-700">Exercise complete ✓</p>
		{:else}
			<button
				type="button"
				class="mt-4 rounded bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700"
				onclick={handleComplete}
			>
				Mark as Complete
			</button>
		{/if}
	</div>
{/if}
