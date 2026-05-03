<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { page } from '$app/state';
	import { curriculum, navigateTo } from '$lib/stores/curriculum.js';
	import { progressStore } from '$lib/stores/progress.js';
	import type { Lesson, Module } from '$lib/types/index.js';
	import { isLessonLocked, isModuleLocked } from '$lib/utils/locking.js';
	import LessonView from '$lib/components/LessonView.svelte';
	import LockedLessonPlaceholder from '$lib/components/LockedLessonPlaceholder.svelte';
	import { onMount } from 'svelte';

	const moduleId = $derived(page.params.module);
	const lessonId = $derived(page.params.lesson);

	const currentModule = $derived<Module | null>(
		$curriculum?.modules.find((m) => m.id === moduleId) ?? null
	);
	const currentLesson = $derived<Lesson | null>(
		currentModule?.lessons.find((l) => l.id === lessonId) ?? null
	);

	// Story I.aa.2 — locking failsafe. The sidebar already filters
	// locked-module clicks (Story I.i / I.j), but a learner who types or
	// bookmarks a locked-lesson URL would otherwise bypass the model
	// entirely. Compute lock state here from the same helpers the
	// sidebar uses, render a placeholder if locked, and skip the
	// `navigateTo` side-effect so the sidebar doesn't highlight a module
	// the learner can't actually access.
	const moduleIndex = $derived<number>(
		$curriculum?.modules.findIndex((m) => m.id === moduleId) ?? -1
	);
	const lessonIndex = $derived<number>(
		currentModule?.lessons.findIndex((l) => l.id === lessonId) ?? -1
	);
	const isLocked = $derived<boolean>(
		!!$curriculum &&
			!!currentModule &&
			!!currentLesson &&
			(isModuleLocked(moduleIndex, $curriculum, $progressStore) ||
				isLessonLocked(currentModule.id, lessonIndex, $curriculum, $progressStore))
	);
	const blockedByTitle = $derived<string | null>(
		(() => {
			if (!isLocked || !$curriculum || !currentModule) return null;
			// `lesson_sequential` blocks on the previous lesson within the same module.
			if (lessonIndex > 0 && $curriculum.locking?.lesson_sequential) {
				return currentModule.lessons[lessonIndex - 1]?.title ?? null;
			}
			// Otherwise the block is module-level: name the previous module.
			if (moduleIndex > 0) return $curriculum.modules[moduleIndex - 1]?.title ?? null;
			return null;
		})()
	);

	// Sync URL params into the curriculum store position — but only when
	// the lesson is *accessible*. Navigating to a locked URL must not
	// highlight the locked module in the sidebar; that would be visually
	// inconsistent with "you can't go here."
	onMount(() => {
		if (moduleId && lessonId && !isLocked) navigateTo(moduleId, lessonId);
	});

	$effect(() => {
		if (moduleId && lessonId && !isLocked) navigateTo(moduleId, lessonId);
	});
</script>

<svelte:head>
	<title>{currentLesson?.title ?? 'Lesson'} — {$curriculum?.title ?? 'LearningFoundry'}</title>
</svelte:head>

{#if currentLesson && currentModule && isLocked}
	<LockedLessonPlaceholder
		moduleTitle={currentModule.title}
		lessonTitle={currentLesson.title}
		blockedBy={blockedByTitle}
	/>
{:else if currentLesson && currentModule}
	{#key `${currentModule.id}/${currentLesson.id}`}
		<LessonView lesson={currentLesson} moduleId={currentModule.id} />
	{/key}
{:else if $curriculum}
	<div class="flex h-full items-center justify-center">
		<p class="text-gray-400">Lesson not found.</p>
	</div>
{:else}
	<div class="flex h-full items-center justify-center">
		<p class="text-gray-400">Loading…</p>
	</div>
{/if}
