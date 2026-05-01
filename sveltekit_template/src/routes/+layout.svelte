<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import '../app.css';
	import { curriculum, modules } from '$lib/stores/curriculum.js';
	import { progressStore, invalidateProgress } from '$lib/stores/progress.js';
	import ModuleList from '$lib/components/ModuleList.svelte';

	interface Props {
		children: import('svelte').Snippet;
	}
	let { children }: Props = $props();

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
		<a href="/" class="mb-6 text-lg font-bold text-blue-600">
			{$curriculum?.title ?? 'LearningFoundry'}
		</a>
		{#if $modules.length}
			<ModuleList modules={$modules} progress={$progressStore} />
		{:else}
			<p class="text-sm text-gray-400">Loading…</p>
		{/if}
	</aside>

	<!-- Main content -->
	<main class="flex-1 overflow-y-auto px-6 py-4">
		{@render children()}
	</main>
</div>
