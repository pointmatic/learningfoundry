<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<!--
  Story J.s — module-level assessment route. Mirrors the structure of
  `[module]/[lesson]/+page.svelte`: derives params, looks up the
  matching `AssessmentDefinition` in the curriculum store, and mounts
  `<AssessmentBlock>`. The completion callback is a no-op stub here;
  Story J.u replaces it with `progressRepo.markAssessmentComplete(...)`
  once that method lands. Locking is not enforced at this route until
  Story J.v.
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { curriculum, setAssessmentPosition } from '$lib/stores/curriculum.js';
	import type {
		AssessmentDefinition,
		AssessmentManifest,
		AssessmentScore,
		Module
	} from '$lib/types/index.js';
	import { capitalizeRole } from '$lib/components/module-list.helpers.js';
	import AssessmentBlock from '$lib/components/AssessmentBlock.svelte';

	const moduleId = $derived(page.params.module);
	const assessmentId = $derived(page.params.id);

	const currentModule = $derived<Module | null>(
		$curriculum?.modules.find((m) => m.id === moduleId) ?? null
	);
	const currentAssessment = $derived<AssessmentDefinition | null>(
		currentModule?.assessments.find((a) => a.id === assessmentId) ?? null
	);

	// Sync URL → store so the sidebar's assessment-row active state
	// (Story J.t) lights up. Mirrors the lesson route's pattern; locking
	// integration arrives in Story J.v.
	onMount(() => {
		if (moduleId && assessmentId && currentAssessment) {
			setAssessmentPosition(moduleId, assessmentId);
		}
	});

	$effect(() => {
		if (moduleId && assessmentId && currentAssessment) {
			setAssessmentPosition(moduleId, assessmentId);
		}
	});

	// Story J.u will replace this with a real persistence call:
	//   progressRepo.markAssessmentComplete(moduleId, assessmentId, score)
	// AssessmentBlock already calls `progressRepo.saveAssessmentScore`
	// internally — this stub is the higher-level "module-assessment
	// completed" hook that J.u wires to the new write path.
	async function handleComplete(_score: AssessmentScore): Promise<void> {
		/* J.u wires the per-module-assessment persistence */
	}
</script>

<svelte:head>
	<title
		>{currentAssessment ? `${capitalizeRole(currentAssessment.role)} Assessment` : 'Assessment'} —
		{$curriculum?.title ?? 'LearningFoundry'}</title
	>
</svelte:head>

{#if currentAssessment && currentModule}
	<article class="mx-auto max-w-4xl p-6">
		<header class="mb-6">
			<h1 class="text-2xl font-semibold">
				{capitalizeRole(currentAssessment.role)} Assessment
			</h1>
		</header>
		{#key `${currentModule.id}/${currentAssessment.id}`}
			<AssessmentBlock
				manifest={currentAssessment.content as AssessmentManifest}
				assessmentRef={currentAssessment.ref}
				passThreshold={currentAssessment.pass_threshold ?? 0.0}
				oncomplete={handleComplete}
			/>
		{/key}
	</article>
{:else if $curriculum}
	<div class="flex h-full items-center justify-center">
		<p class="text-gray-400">Assessment not found.</p>
	</div>
{:else}
	<div class="flex h-full items-center justify-center">
		<p class="text-gray-400">Loading…</p>
	</div>
{/if}
