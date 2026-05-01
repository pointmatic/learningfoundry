<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { currentPosition } from '$lib/stores/curriculum.js';
	import type { Module, ModuleProgress } from '$lib/types/index.js';
	import LessonList from './LessonList.svelte';
	import ProgressBar from './ProgressBar.svelte';

	interface Props {
		modules: Module[];
		progress?: Record<string, ModuleProgress>;
	}
	let { modules, progress = {} }: Props = $props();

	let expandedModuleId = $state<string | null>(null);
	let lastAutoExpandedModuleId = $state<string | null>(null);

	function modulePercent(mod: Module): number {
		const mp = progress[mod.id];
		if (!mp) return 0;
		const total = mod.lessons.length;
		if (total === 0) return 0;
		const done = Object.values(mp.lessons).filter((l) => l.status === 'complete').length;
		return Math.round((done / total) * 100);
	}

	function toggleModule(id: string) {
		expandedModuleId = expandedModuleId === id ? null : id;
	}

	// Auto-expand the module containing the current lesson.
	// Only fire when `currentPosition.moduleId` changes to a *new* value;
	// `lastAutoExpandedModuleId` breaks the self-dependency that previously
	// caused manual toggles to revert immediately.
	$effect(() => {
		const pos = $currentPosition;
		if (pos && pos.moduleId !== lastAutoExpandedModuleId) {
			expandedModuleId = pos.moduleId;
			lastAutoExpandedModuleId = pos.moduleId;
		}
	});
</script>

<nav aria-label="Modules">
	<ul class="space-y-2">
		{#each modules as mod (mod.id)}
			{@const pct = modulePercent(mod)}
			{@const isExpanded = expandedModuleId === mod.id}
			<li
				class="rounded-lg border border-gray-200 bg-white
					{mod.id === $currentPosition?.moduleId
					? 'border-l-2 border-l-blue-500 bg-blue-50'
					: ''}"
			>
				<button
					onclick={() => toggleModule(mod.id)}
					class="flex w-full items-center justify-between px-4 py-3 text-left"
					aria-expanded={isExpanded}
				>
					<span class="text-sm font-medium text-gray-800">{mod.title}</span>
					<span class="text-xs text-gray-400">{pct}%</span>
				</button>
				<div class="px-4 pb-2">
					<ProgressBar percent={pct} />
				</div>
				{#if isExpanded}
					<div class="border-t border-gray-100 px-2 pb-2 pt-1">
						<LessonList
							moduleId={mod.id}
							lessons={mod.lessons}
							progress={progress[mod.id]?.lessons}
						/>
					</div>
				{/if}
			</li>
		{/each}
	</ul>
</nav>
