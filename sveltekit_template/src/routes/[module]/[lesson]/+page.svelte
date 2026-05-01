<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { curriculum, navigateTo } from '$lib/stores/curriculum.js';
	import type { Lesson, Module } from '$lib/types/index.js';
	import LessonView from '$lib/components/LessonView.svelte';
	import { onMount } from 'svelte';

	const moduleId = $derived($page.params.module);
	const lessonId = $derived($page.params.lesson);

	const currentModule = $derived<Module | null>(
		$curriculum?.modules.find((m) => m.id === moduleId) ?? null
	);
	const currentLesson = $derived<Lesson | null>(
		currentModule?.lessons.find((l) => l.id === lessonId) ?? null
	);

	// Sync URL params into the curriculum store position
	onMount(() => {
		if (moduleId && lessonId) navigateTo(moduleId, lessonId);
	});

	$effect(() => {
		if (moduleId && lessonId) navigateTo(moduleId, lessonId);
	});

	function handleLessonComplete() {
		void goto('/');
	}
</script>

<svelte:head>
	<title>{currentLesson?.title ?? 'Lesson'} — {$curriculum?.title ?? 'LearningFoundry'}</title>
</svelte:head>

{#if currentLesson && currentModule}
	<LessonView
		lesson={currentLesson}
		moduleId={currentModule.id}
		oncomplete={handleLessonComplete}
	/>
{:else if $curriculum}
	<div class="flex h-full items-center justify-center">
		<p class="text-gray-400">Lesson not found.</p>
	</div>
{:else}
	<div class="flex h-full items-center justify-center">
		<p class="text-gray-400">Loading…</p>
	</div>
{/if}
