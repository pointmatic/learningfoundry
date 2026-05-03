<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import Lock from 'lucide-svelte/icons/lock';

	interface Props {
		moduleTitle: string;
		lessonTitle: string;
		blockedBy: string | null;
	}
	let { moduleTitle, lessonTitle, blockedBy }: Props = $props();
</script>

<section
	class="mx-auto flex max-w-xl flex-col items-center gap-4 px-6 py-16 text-center"
>
	<div class="rounded-full bg-gray-100 p-4 text-gray-500">
		<Lock size={32} aria-hidden="true" />
	</div>
	<h1 class="text-xl font-semibold text-gray-800">Lesson is locked</h1>
	<p class="text-sm leading-relaxed text-gray-600">
		<span class="font-medium">{moduleTitle}</span> &mdash;
		<span>{lessonTitle}</span>
	</p>
	{#if blockedBy}
		<p class="text-sm text-gray-600">
			Complete <span class="font-medium">{blockedBy}</span> to unlock this lesson.
		</p>
	{:else}
		<p class="text-sm text-gray-600">
			This lesson is gated by the curriculum's locking rules.
		</p>
	{/if}
	<a
		href="/"
		class="mt-2 inline-flex items-center rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
	>
		Return to dashboard
	</a>
</section>
