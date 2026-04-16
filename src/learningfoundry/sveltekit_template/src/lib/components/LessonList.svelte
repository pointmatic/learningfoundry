<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { currentPosition, navigateTo } from '$lib/stores/curriculum.js';
	import type { Lesson, LessonProgress } from '$lib/types/index.js';

	interface Props {
		moduleId: string;
		lessons: Lesson[];
		progress?: Record<string, LessonProgress>;
	}
	let { moduleId, lessons, progress = {} }: Props = $props();

	function statusIcon(lessonId: string): string {
		const s = progress[lessonId]?.status;
		if (s === 'complete') return '✓';
		if (s === 'in_progress') return '…';
		return '○';
	}

	function statusClass(lessonId: string): string {
		const s = progress[lessonId]?.status;
		if (s === 'complete') return 'text-green-600';
		if (s === 'in_progress') return 'text-blue-500';
		return 'text-gray-400';
	}
</script>

<ul class="space-y-1">
	{#each lessons as lesson (lesson.id)}
		{@const isActive =
			$currentPosition?.moduleId === moduleId && $currentPosition?.lessonId === lesson.id}
		<li>
			<button
				onclick={() => navigateTo(moduleId, lesson.id)}
				class="flex w-full items-center gap-2 rounded px-3 py-1.5 text-left text-sm transition-colors
					{isActive
					? 'bg-blue-100 font-medium text-blue-700'
					: 'text-gray-700 hover:bg-gray-100'}"
			>
				<span class="shrink-0 text-xs {statusClass(lesson.id)}">{statusIcon(lesson.id)}</span>
				<span class="truncate">{lesson.title}</span>
			</button>
		</li>
	{/each}
</ul>
