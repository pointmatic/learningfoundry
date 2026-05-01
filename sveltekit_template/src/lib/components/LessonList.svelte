<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { currentPosition } from '$lib/stores/curriculum.js';
	import type { Lesson, LessonProgress } from '$lib/types/index.js';
	import { lessonStatusIcon, resolveLessonClick } from './module-list.helpers.js';
	import { lessonHref } from './navigation.helpers.js';

	interface Props {
		moduleId: string;
		lessons: Lesson[];
		progress?: Record<string, LessonProgress>;
		optionalLessons?: Set<string>;
		lockedLessons?: Set<string>;
	}
	let {
		moduleId,
		lessons,
		progress = {},
		optionalLessons = new Set(),
		lockedLessons = new Set()
	}: Props = $props();

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
	{#each lessons as lesson (lesson.id)}
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
			</button>
		</li>
	{/each}
</ul>
