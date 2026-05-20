<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<!--
  Adapter between the vendor `<QuizBlock>` from `@pointmatic/quizazz` and
  learningfoundry's score-persistence + pass-threshold event protocol.
  Renders the vendor component, translates its `complete` event payload to a
  `QuizScore`, persists via `progressRepo.saveQuizScore`, and fires the
  consumer-facing `oncomplete` / `onquizcomplete` callbacks.
-->
<script lang="ts">
	import { QuizBlock as VendorQuizBlock } from '@pointmatic/quizazz';
	import { progressRepo } from '$lib/db/index.js';
	import type { AssessmentManifest, QuizScore } from '$lib/types/index.js';

	interface QuizCompleteDetail {
		quizRef: string;
		score: number;
		maxScore: number;
		questionCount: number;
	}

	interface Props {
		manifest: AssessmentManifest;
		quizRef: string;
		passThreshold?: number;
		oncomplete?: (score: QuizScore) => void;
		onquizcomplete?: () => void;
	}
	let { manifest, quizRef, passThreshold = 0.0, oncomplete, onquizcomplete }: Props = $props();

	async function handleComplete(detail: QuizCompleteDetail) {
		const score: QuizScore = {
			quizRef: detail.quizRef,
			score: detail.score,
			maxScore: detail.maxScore,
			questionCount: detail.questionCount,
			completedAt: new Date().toISOString()
		};
		await progressRepo.saveQuizScore(score);
		oncomplete?.(score);
		if (detail.maxScore > 0 && detail.score / detail.maxScore >= passThreshold) {
			onquizcomplete?.();
		} else if (detail.maxScore === 0) {
			onquizcomplete?.();
		}
	}
</script>

<!--
  The vendor `<QuizBlock>` types `manifest` against its internal `QuizManifest`
  (narrow: NavNode[]/Question[]). Our local `AssessmentManifest` uses opaque
  `unknown[]` plus an index signature because we pass-through Python-emitted
  JSON without re-asserting the vendor's schema. The runtime shapes match
  (both describe the same `compile_assessment` output, with `quizName`
  relabeled to `assessmentName` by `QuizazzProvider`); the cast bridges the
  TS declarations.
-->
<VendorQuizBlock manifest={manifest as never} {quizRef} oncomplete={(detail) => handleComplete(detail)} />
