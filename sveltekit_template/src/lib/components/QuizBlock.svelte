<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<!--
  QuizBlock renders a quizazz quiz manifest.
  When the quiz completes, it writes the score to SQLite and dispatches
  a 'complete' event with QuizScore data.
  The quizazz SvelteKit component is imported dynamically so it remains
  optional until the quizazz npm package is published.
-->
<script lang="ts">
	import { saveQuizScore } from '$lib/db/index.js';
	import type { QuizManifest, QuizScore } from '$lib/types/index.js';
	import PlaceholderBlock from './PlaceholderBlock.svelte';

	interface QuizCompleteDetail {
		quizRef: string;
		score: number;
		maxScore: number;
		questionCount: number;
	}

	interface Props {
		manifest: QuizManifest;
		quizRef: string;
		oncomplete?: (score: QuizScore) => void;
	}
	let { manifest, quizRef, oncomplete }: Props = $props();

	async function handleComplete(detail: QuizCompleteDetail) {
		const score: QuizScore = {
			quizRef: detail.quizRef,
			score: detail.score,
			maxScore: detail.maxScore,
			questionCount: detail.questionCount,
			completedAt: new Date().toISOString()
		};
		await saveQuizScore(score);
		oncomplete?.(score);
	}
</script>

<!--
  Replace this placeholder once @pointmatic/quizazz is published:

  <QuizazzComponent
    {manifest}
    {quizRef}
    on:complete={(e) => handleComplete(e.detail)}
  />
-->
<PlaceholderBlock
	label="Quiz: {manifest.quizName ?? quizRef}"
	message="quizazz component pending (@pointmatic/quizazz)."
/>
