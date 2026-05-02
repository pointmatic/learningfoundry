<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import '../app.css';
	import { afterNavigate } from '$app/navigation';
	import { curriculum, modules } from '$lib/stores/curriculum.js';
	import { progressStore, invalidateProgress } from '$lib/stores/progress.js';
	import ModuleList from '$lib/components/ModuleList.svelte';
	import ResetCourseButton from '$lib/components/ResetCourseButton.svelte';
	import { clearActivePosition } from './layout.helpers.js';
	import { resetMainScrollOnForwardNav } from './layout.scroll.js';
	import { lockedModuleIds } from '$lib/utils/locking.js';
	import { hasAnyProgress } from '$lib/utils/progress.js';

	interface Props {
		children: import('svelte').Snippet;
	}
	let { children }: Props = $props();

	let mainEl: HTMLElement | undefined = $state();

	// SvelteKit's built-in scroll restoration only manages `window.scrollY`,
	// but our shell pins the viewport (`h-screen overflow-hidden`) and
	// scrolls inside `<main>`. Without this hook, navigating from the bottom
	// of one lesson (where the Next button lives) to the next lesson leaves
	// `<main>.scrollTop` at the previous bottom. We reset it on every
	// forward navigation; `popstate` (back/forward) is left alone so the
	// browser's natural restoration still works for the back button.
	afterNavigate((nav) => resetMainScrollOnForwardNav(nav, mainEl));

	$effect(() => {
		const cur = $curriculum;
		if (cur) {
			void invalidateProgress(cur);
		}
	});
</script>

<div class="flex h-screen overflow-hidden bg-gray-50">
	<!-- Sidebar -->
	<aside class="flex w-72 shrink-0 flex-col overflow-y-auto border-r border-gray-200 bg-white p-4">
		<a
			href="/"
			class="mb-6 text-lg font-bold text-blue-600"
			onclick={clearActivePosition}
		>
			{$curriculum?.title ?? 'LearningFoundry'}
		</a>
		{#if $modules.length && $curriculum}
			<ModuleList
				modules={$modules}
				progress={$progressStore}
				curriculum={$curriculum}
				lockedModules={lockedModuleIds($curriculum, $progressStore)}
			/>
		{:else}
			<p class="text-sm text-gray-400">Loading…</p>
		{/if}

		<div class="mt-auto pt-4">
			<ResetCourseButton disabled={!hasAnyProgress($progressStore)} />
		</div>
	</aside>

	<!-- Main content -->
	<main bind:this={mainEl} class="flex-1 overflow-y-auto px-6 py-4">
		{@render children()}
	</main>
</div>
