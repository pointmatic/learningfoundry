<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { getLessonProgress, markLessonComplete, markLessonInProgress } from '$lib/db/index.js';
	import { curriculum } from '$lib/stores/curriculum.js';
	import { invalidateProgress } from '$lib/stores/progress.js';
	import type { Lesson, QuizScore } from '$lib/types/index.js';
	import ContentBlock from './ContentBlock.svelte';
	import Navigation from './Navigation.svelte';
	import { onMount } from 'svelte';

	interface Props {
		lesson: Lesson;
		moduleId: string;
	}
	let { lesson, moduleId }: Props = $props();

	let allBlocksComplete = $state(false);
	let completedBlocks = $state(new Set<number>());

	const lessonComplete = $derived(
		allBlocksComplete || completedBlocks.size === lesson.content_blocks.length
	);

	onMount(async () => {
		// Zero-block edge case
		if (lesson.content_blocks.length === 0) {
			allBlocksComplete = true;
			await markLessonComplete(moduleId, lesson.id);
			await invalidateProgress($curriculum);
			return;
		}

		// Revisit: if lesson is already complete, pre-fill so nav is active
		const existing = await getLessonProgress(moduleId, lesson.id);
		if (existing?.status === 'complete') {
			allBlocksComplete = true;
		} else {
			await markLessonInProgress(moduleId, lesson.id);
		}
	});

	async function handleBlockComplete(blockIndex: number) {
		if (allBlocksComplete) return;
		completedBlocks.add(blockIndex);
		completedBlocks = new Set(completedBlocks);
		if (completedBlocks.size === lesson.content_blocks.length) {
			await markLessonComplete(moduleId, lesson.id);
			// Refreshing the progress store is enough to drive the
			// `unlock_module_on_complete` cascade: locking utilities in
			// `$lib/utils/locking.ts` re-derive sibling-optional and
			// next-module-unlocked state from the new `complete` status —
			// no additional DB write or extra invalidation is required.
			await invalidateProgress($curriculum);
		}
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
				<ContentBlock
					{block}
					blockIndex={i}
					onblockcomplete={handleBlockComplete}
					onquizcomplete={handleQuizComplete}
				/>
			</section>
		{/each}
	</div>

	<Navigation disabled={!lessonComplete} />
</article>
