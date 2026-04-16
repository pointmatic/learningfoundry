<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { markLessonComplete, markLessonInProgress } from '$lib/db/index.js';
	import type { Lesson, QuizScore } from '$lib/types/index.js';
	import ContentBlock from './ContentBlock.svelte';
	import Navigation from './Navigation.svelte';
	import { onMount } from 'svelte';

	interface Props {
		lesson: Lesson;
		moduleId: string;
		oncomplete?: () => void;
	}
	let { lesson, moduleId, oncomplete }: Props = $props();

	onMount(async () => {
		await markLessonInProgress(moduleId, lesson.id);
	});

	async function handleNavComplete() {
		await markLessonComplete(moduleId, lesson.id);
		oncomplete?.();
	}

	function handleQuizComplete(_score: QuizScore) {
		// Score already persisted by QuizBlock; could trigger further logic here
	}
</script>

<article class="mx-auto max-w-3xl space-y-8 py-6">
	<header>
		<h1 class="text-2xl font-bold text-gray-900">{lesson.title}</h1>
	</header>

	<div class="space-y-8">
		{#each lesson.content_blocks as block, i (i)}
			<section>
				<ContentBlock {block} onquizcomplete={handleQuizComplete} />
			</section>
		{/each}
	</div>

	<Navigation onComplete={handleNavComplete} />
</article>
