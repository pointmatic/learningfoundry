<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { curriculum, modules } from '$lib/stores/curriculum.js';
	import { progressStore } from '$lib/stores/progress.js';
	import ProgressDashboard from '$lib/components/ProgressDashboard.svelte';
</script>

<svelte:head>
	<title>{$curriculum?.title ?? 'LearningFoundry'}</title>
</svelte:head>

{#if $curriculum}
	<div class="mx-auto max-w-3xl py-8">
		<h1 class="mb-2 text-3xl font-bold text-gray-900">{$curriculum.title}</h1>
		{#if $curriculum.description}
			<p class="mb-8 text-gray-500">{$curriculum.description}</p>
		{/if}
		<ProgressDashboard modules={$modules} progress={$progressStore} />
	</div>
{:else}
	<div class="flex h-full items-center justify-center">
		<p class="text-gray-400">Loading curriculum…</p>
	</div>
{/if}
