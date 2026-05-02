<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<script lang="ts">
	import { progressRepo } from '$lib/db/index.js';
	import { curriculum } from '$lib/stores/curriculum.js';
	import { invalidateProgress } from '$lib/stores/progress.js';
	import type { Lesson, QuizScore } from '$lib/types/index.js';
	import ContentBlock from './ContentBlock.svelte';
	import Navigation from './Navigation.svelte';
	import { contentBlockKey } from './lesson-view.helpers.js';
	import { onMount } from 'svelte';

	/**
	 * Lifecycle event payload (Story I.p / FR-P15). Each callback fires
	 * at most once per mount session and only when a meaningful state
	 * transition occurred:
	 *   - `onlessonopen` — every mount.
	 *   - `onlessonengage` — first block-completion event of the mount
	 *     (suppressed on revisits to a `complete` lesson).
	 *   - `onlessoncomplete` — when every content block has fired
	 *     completion (suppressed on revisits to a `complete` lesson; for
	 *     zero-block lessons fires immediately after `onlessonopen`).
	 * No internal subscribers exist today — these are forward-compatible
	 * hooks for future analytics / telemetry adapters.
	 */
	export interface LessonLifecycleDetail {
		moduleId: string;
		lessonId: string;
	}

	interface Props {
		lesson: Lesson;
		moduleId: string;
		onlessonopen?: (detail: LessonLifecycleDetail) => void;
		onlessonengage?: (detail: LessonLifecycleDetail) => void;
		onlessoncomplete?: (detail: LessonLifecycleDetail) => void;
	}
	let {
		lesson,
		moduleId,
		onlessonopen,
		onlessonengage,
		onlessoncomplete
	}: Props = $props();

	let allBlocksComplete = $state(false);
	let completedBlocks = $state(new Set<number>());
	// Tracks whether we have already promoted this mount session to
	// `in_progress` — first block-completion flips it; subsequent block
	// completions re-use the existing row without reissuing the SQL.
	let engaged = $state(false);

	const lessonComplete = $derived(
		allBlocksComplete || completedBlocks.size === lesson.content_blocks.length
	);

	function fireOpen() {
		onlessonopen?.({ moduleId, lessonId: lesson.id });
	}
	function fireComplete() {
		onlessoncomplete?.({ moduleId, lessonId: lesson.id });
	}

	onMount(async () => {
		// Every mount records an open before any other state transition.
		await progressRepo.markLessonOpened(moduleId, lesson.id);
		fireOpen();

		// Zero-block edge case — instant complete after open.
		if (lesson.content_blocks.length === 0) {
			allBlocksComplete = true;
			await progressRepo.markLessonComplete(moduleId, lesson.id);
			await invalidateProgress($curriculum);
			fireComplete();
			return;
		}

		// Revisit: pre-fill nav so Next/Finish is enabled immediately. No
		// engage / complete events fire on revisit — no transition occurs.
		const existing = await progressRepo.getLessonProgress(moduleId, lesson.id);
		if (existing?.status === 'complete') {
			allBlocksComplete = true;
			engaged = true; // suppress redundant `markLessonInProgress` if a block fires
		}
		// First-engage promotion is now deferred to `handleBlockComplete`
		// so a learner who opens a lesson but engages with no content is
		// distinguishable from one genuinely partway through.
		await invalidateProgress($curriculum);
	});

	async function handleBlockComplete(blockIndex: number) {
		if (allBlocksComplete) return;
		completedBlocks.add(blockIndex);
		completedBlocks = new Set(completedBlocks);

		// First engagement of the mount session: promote to in_progress
		// and emit `lessonengage`.
		if (!engaged) {
			engaged = true;
			await progressRepo.markLessonInProgress(moduleId, lesson.id);
			onlessonengage?.({ moduleId, lessonId: lesson.id });
			await invalidateProgress($curriculum);
		}

		if (completedBlocks.size === lesson.content_blocks.length) {
			await progressRepo.markLessonComplete(moduleId, lesson.id);
			// Refreshing the progress store is enough to drive the
			// `unlock_module_on_complete` cascade: locking utilities in
			// `$lib/utils/locking.ts` re-derive sibling-optional and
			// next-module-unlocked state from the new `complete` status —
			// no additional DB write or extra invalidation is required.
			await invalidateProgress($curriculum);
			fireComplete();
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
		{#each lesson.content_blocks as block, i (contentBlockKey(block, i))}
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
