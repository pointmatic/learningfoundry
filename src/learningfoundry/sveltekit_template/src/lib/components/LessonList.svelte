<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { currentPosition } from '$lib/stores/curriculum.js';
	import type { AssessmentDefinition, Lesson, LessonProgress } from '$lib/types/index.js';
	import {
		capitalizeRole,
		formatPassThreshold,
		interleaveModuleFlow,
		lessonStatusIcon,
		resolveLessonClick
	} from './module-list.helpers.js';
	import { lessonHref } from './navigation.helpers.js';

	interface Props {
		moduleId: string;
		lessons: Lesson[];
		/** Story J.f — assessments rendered at their resolved positions
		 * relative to lessons. Order in the array is the canonical iteration
		 * order; each entry's `position` field places it in the flow. */
		assessments?: AssessmentDefinition[];
		progress?: Record<string, LessonProgress>;
		optionalLessons?: Set<string>;
		lockedLessons?: Set<string>;
	}
	let {
		moduleId,
		lessons,
		assessments = [],
		progress = {},
		optionalLessons = new Set(),
		lockedLessons = new Set()
	}: Props = $props();

	const flow = $derived(interleaveModuleFlow(lessons, assessments));

	function statusIcon(lessonId: string): string {
		const s = progress[lessonId]?.status;
		const concrete = s === 'optional' ? undefined : s;
		return lessonStatusIcon(lessonId, concrete, optionalLessons);
	}

	function statusClass(lessonId: string): string {
		const s = progress[lessonId]?.status;
		if (s === 'complete') return 'text-green-600';
		// `opened` (Story I.p) shares the in_progress visual on purpose —
		// learners shouldn't see "I opened it but didn't engage" as a
		// distinct sidebar symbol; the distinction is data-only.
		if (s === 'in_progress' || s === 'opened') return 'text-blue-500';
		return 'text-gray-400';
	}

	function handleClick(lessonId: string) {
		if (resolveLessonClick(lessonId, lockedLessons) === 'noop') return;
		void goto(lessonHref(moduleId, lessonId));
	}
</script>

<ul class="space-y-1">
	{#each flow as item, i (item.kind === 'lesson' ? `lesson:${item.lesson.id}` : `assessment:${i}:${item.assessment.ref}`)}
		{#if item.kind === 'lesson'}
			{@const lesson = item.lesson}
			{@const isActive =
				$currentPosition?.moduleId === moduleId && $currentPosition?.lessonId === lesson.id}
			{@const locked = lockedLessons.has(lesson.id)}
			<li>
				<button
					onclick={() => handleClick(lesson.id)}
					class="flex w-full items-center gap-2 rounded px-3 py-1.5 text-left text-sm transition-colors
						{locked
						? 'cursor-not-allowed text-gray-300'
						: isActive
							? 'bg-blue-100 font-medium text-blue-700'
							: 'text-gray-700 hover:bg-gray-100'}"
					aria-disabled={locked}
				>
					<span class="shrink-0 text-xs {locked ? 'text-gray-300' : statusClass(lesson.id)}"
						>{statusIcon(lesson.id)}</span
					>
					<span class="truncate">{lesson.title}</span>
					{#if lesson.meta?.role}
						<span
							class="ml-auto shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-gray-600"
							data-testid="lesson-role-chip"
						>
							{lesson.meta.role}
						</span>
					{/if}
				</button>
			</li>
		{:else}
			{@const assessment = item.assessment}
			{@const threshold = formatPassThreshold(assessment.pass_threshold)}
			<li
				class="flex items-center gap-2 rounded px-3 py-1.5 text-sm text-gray-600"
				data-testid="assessment-row"
				data-role={assessment.role}
			>
				<span class="shrink-0 text-xs text-amber-600" aria-hidden="true">◆</span>
				<span class="truncate font-medium">{capitalizeRole(assessment.role)} Assessment</span>
				{#if threshold}
					<span
						class="ml-auto shrink-0 text-[11px] text-gray-400"
						data-testid="assessment-threshold"
					>
						{threshold}
					</span>
				{/if}
			</li>
		{/if}
	{/each}
</ul>
