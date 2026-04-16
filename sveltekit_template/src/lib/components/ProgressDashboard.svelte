<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { navigateTo } from '$lib/stores/curriculum.js';
	import type { Module, ModuleProgress, QuizScore } from '$lib/types/index.js';
	import ProgressBar from './ProgressBar.svelte';

	interface Props {
		modules: Module[];
		progress: Record<string, ModuleProgress>;
		quizScores?: Record<string, QuizScore>;
	}
	let { modules, progress, quizScores = {} }: Props = $props();

	function moduleStats(mod: Module) {
		const mp = progress[mod.id];
		const total = mod.lessons.length;
		if (!mp || total === 0) return { done: 0, total, pct: 0, status: 'not_started' };
		const done = Object.values(mp.lessons).filter((l) => l.status === 'complete').length;
		return { done, total, pct: Math.round((done / total) * 100), status: mp.status };
	}

	function resumeFirst(mod: Module) {
		const mp = progress[mod.id];
		const firstIncomplete = mod.lessons.find(
			(l) => mp?.lessons[l.id]?.status !== 'complete'
		);
		const target = firstIncomplete ?? mod.lessons[0];
		if (target) navigateTo(mod.id, target.id);
	}

	const overallPct = $derived(() => {
		let done = 0;
		let total = 0;
		for (const mod of modules) {
			const s = moduleStats(mod);
			done += s.done;
			total += s.total;
		}
		return total === 0 ? 0 : Math.round((done / total) * 100);
	});
</script>

<div class="space-y-6">
	<div>
		<h2 class="mb-2 text-lg font-semibold text-gray-900">Overall Progress</h2>
		<ProgressBar percent={overallPct()} label="All lessons" />
	</div>

	<div class="space-y-4">
		{#each modules as mod (mod.id)}
			{@const stats = moduleStats(mod)}
			<div class="rounded-lg border border-gray-200 bg-white p-4">
				<div class="mb-2 flex items-center justify-between">
					<h3 class="text-sm font-medium text-gray-800">{mod.title}</h3>
					<span class="text-xs text-gray-500">{stats.done}/{stats.total} lessons</span>
				</div>
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
