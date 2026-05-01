<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { currentPosition } from '$lib/stores/curriculum.js';
	import type { Curriculum, Module, ModuleProgress } from '$lib/types/index.js';
	import { getOptionalLessons, lockedLessonIds } from '$lib/utils/locking.js';
	import { computeAutoExpand, resolveModuleHeaderClick } from './module-list.helpers.js';
	import LessonList from './LessonList.svelte';
	import ProgressBar from './ProgressBar.svelte';
	import Lock from 'lucide-svelte/icons/lock';

	interface Props {
		modules: Module[];
		progress?: Record<string, ModuleProgress>;
		curriculum?: Curriculum | null;
		lockedModules?: Set<string>;
	}
	let {
		modules,
		progress = {},
		curriculum = null,
		lockedModules = new Set()
	}: Props = $props();

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
		const action = resolveModuleHeaderClick(id, expandedModuleId, lockedModules);
		if (action.kind === 'noop') return;
		expandedModuleId = action.kind === 'collapse' ? null : action.id;
	}

	// Auto-expand the module containing the current lesson.
	// Only fire when `currentPosition.moduleId` changes to a *new* value;
	// `lastAutoExpandedModuleId` breaks the self-dependency that previously
	// caused manual toggles to revert immediately. When the position is
	// cleared (Finish on the last lesson, FR-P14), collapse the previously
	// expanded module so the dashboard sidebar starts from a clean slate.
	$effect(() => {
		const pos = $currentPosition;
		const next = computeAutoExpand(pos?.moduleId ?? null, lastAutoExpandedModuleId);
		if (next) {
			expandedModuleId = next.expandedModuleId;
			lastAutoExpandedModuleId = next.lastAutoExpandedModuleId;
		}
	});
</script>

<nav aria-label="Modules">
	<ul class="space-y-2">
		{#each modules as mod (mod.id)}
			{@const pct = modulePercent(mod)}
			{@const locked = lockedModules.has(mod.id)}
			{@const isExpanded = !locked && expandedModuleId === mod.id}
			{@const optional = curriculum ? getOptionalLessons(mod.id, curriculum, progress) : new Set<string>()}
			{@const lockedLessons = curriculum ? lockedLessonIds(mod.id, curriculum, progress) : new Set<string>()}
			<li
				class="rounded-lg border border-gray-200 bg-white
					{!locked && mod.id === $currentPosition?.moduleId
					? 'border-l-2 border-l-blue-500 bg-blue-50'
					: ''}"
			>
				<button
					onclick={() => toggleModule(mod.id)}
					class="flex w-full items-center justify-between px-4 py-3 text-left
						{locked ? 'cursor-not-allowed text-gray-400' : ''}"
					aria-expanded={isExpanded}
					aria-disabled={locked}
				>
					<span class="flex items-center gap-2 text-sm font-medium {locked ? 'text-gray-400' : 'text-gray-800'}">
						{#if locked}
							<Lock size={14} aria-hidden="true" />
						{/if}
						{mod.title}
					</span>
					<span class="text-xs text-gray-400">{pct}%</span>
				</button>
				{#if !locked}
					<div class="px-4 pb-2">
						<ProgressBar percent={pct} />
					</div>
				{/if}
				{#if isExpanded}
					<div class="border-t border-gray-100 px-2 pb-2 pt-1">
						<LessonList
							moduleId={mod.id}
							lessons={mod.lessons}
							progress={progress[mod.id]?.lessons}
							optionalLessons={optional}
							lockedLessons={lockedLessons}
						/>
					</div>
				{/if}
			</li>
		{/each}
	</ul>
</nav>
