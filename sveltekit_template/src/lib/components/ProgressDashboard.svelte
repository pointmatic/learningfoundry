<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { navigateTo } from '$lib/stores/curriculum.js';
	import type { Curriculum, Module, ModuleProgress, QuizScore } from '$lib/types/index.js';
	import { getOptionalLessons, isModuleComplete } from '$lib/utils/locking.js';
	import ProgressBar from './ProgressBar.svelte';

	interface Props {
		modules: Module[];
		progress: Record<string, ModuleProgress>;
		quizScores?: Record<string, QuizScore>;
		curriculum?: Curriculum | null;
	}
	let { modules, progress, quizScores = {}, curriculum = null }: Props = $props();

	type ModuleStatus = 'not_started' | 'in_progress' | 'complete';

	function moduleStats(mod: Module): {
		done: number;
		total: number;
		pct: number;
		status: ModuleStatus;
	} {
		const mp = progress[mod.id];
		const total = mod.lessons.length;
		if (!mp || total === 0) {
			return { done: 0, total, pct: 0, status: 'not_started' };
		}
		const done = Object.values(mp.lessons).filter((l) => l.status === 'complete').length;
		const complete = curriculum
			? isModuleComplete(mod.id, curriculum, progress)
			: mp.status === 'complete';
		const status: ModuleStatus = complete
			? 'complete'
			: done > 0
				? 'in_progress'
				: 'not_started';
		return { done, total, pct: Math.round((done / total) * 100), status };
	}

	function resumeFirst(mod: Module) {
		const mp = progress[mod.id];
		const optional = curriculum ? getOptionalLessons(mod.id, curriculum, progress) : new Set<string>();
		const firstIncomplete = mod.lessons.find(
			(l) => !optional.has(l.id) && mp?.lessons[l.id]?.status !== 'complete'
		);
		const target = firstIncomplete ?? mod.lessons[0];
		if (target) navigateTo(mod.id, target.id);
	}

	const totalLessons = $derived(modules.reduce((n, m) => n + m.lessons.length, 0));

	const totalComplete = $derived(
		modules.reduce((n, m) => {
			const mp = progress[m.id];
			if (!mp) return n;
			return n + Object.values(mp.lessons).filter((l) => l.status === 'complete').length;
		}, 0)
	);

	const overallPct = $derived(
		totalLessons === 0 ? 0 : Math.round((totalComplete / totalLessons) * 100)
	);
</script>

<div class="space-y-6">
	{#if totalLessons > 0}
		<div>
			<p class="mb-1 text-sm text-gray-600">{totalComplete} of {totalLessons} lessons completed</p>
			<ProgressBar percent={overallPct} />
		</div>
	{/if}

	<div class="space-y-4">
		{#each modules as mod (mod.id)}
			{@const stats = moduleStats(mod)}
			<div class="rounded-lg border border-gray-200 bg-white p-4">
				<div class="mb-2 flex items-center justify-between">
					<h3 class="text-sm font-medium text-gray-800">{mod.title}</h3>
					<span class="text-xs text-gray-500">{stats.done}/{stats.total} lessons</span>
				</div>
				{#if mod.description}
					<p class="mb-2 text-xs leading-relaxed text-gray-500">{mod.description}</p>
				{/if}
				<ProgressBar percent={stats.pct} />

				{#if mod.pre_assessment && quizScores[`pre:${mod.id}`]}
					{@const qs = quizScores[`pre:${mod.id}`]}
					<p class="mt-2 text-xs text-gray-500">
						Pre-assessment: {qs.score}/{qs.maxScore}
					</p>
				{/if}
				{#if mod.post_assessment && quizScores[`post:${mod.id}`]}
					{@const qs = quizScores[`post:${mod.id}`]}
					<p class="mt-1 text-xs text-gray-500">
						Post-assessment: {qs.score}/{qs.maxScore}
					</p>
				{/if}

				{#if stats.status !== 'complete'}
					<button
						onclick={() => resumeFirst(mod)}
						class="mt-3 text-xs font-medium text-blue-600 hover:underline"
					>
						{stats.status === 'not_started' ? 'Start module →' : 'Continue →'}
					</button>
				{:else}
					<p class="mt-3 text-xs font-medium text-green-600">✓ Complete</p>
				{/if}
			</div>
		{/each}
	</div>
</div>
