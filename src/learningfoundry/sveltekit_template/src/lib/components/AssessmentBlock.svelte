<!-- Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0 -->
<!--
  learningfoundry's `<AssessmentBlock>` wrapper around the vendor `<QuizBlock>`
  from `@pointmatic/quizazz`. Translates between LF-domain props/events and
  the vendor's surface: accepts `assessmentRef` from callers and forwards it
  to the vendor as `quizRef`; receives the vendor's `complete` event payload
  (whose `quizRef` field mirrors the vendor's identifier name — preserved
  per project-essentials' vendor-boundary rule) and translates `quizRef` →
  `assessmentRef` at the assignment site when building an
  `AssessmentScore`, persists via `progressRepo.saveAssessmentScore`, and
  fires the consumer-facing `oncomplete` / `onassessmentcomplete` callbacks.
-->
<script lang="ts">
	import { QuizBlock as VendorQuizBlock } from '@pointmatic/quizazz';
	import { progressRepo } from '$lib/db/index.js';
	import type { AssessmentManifest, AssessmentScore } from '$lib/types/index.js';

	interface QuizCompleteDetail {
		quizRef: string;
		score: number;
		maxScore: number;
		questionCount: number;
	}

	interface Props {
		manifest: AssessmentManifest;
		assessmentRef: string;
		passThreshold?: number;
		oncomplete?: (score: AssessmentScore) => void;
		onassessmentcomplete?: () => void;
	}
	let {
		manifest,
		assessmentRef,
		passThreshold = 0.0,
		oncomplete,
		onassessmentcomplete
	}: Props = $props();

	async function handleComplete(detail: QuizCompleteDetail) {
		const score: AssessmentScore = {
			assessmentRef: detail.quizRef,
			score: detail.score,
			maxScore: detail.maxScore,
			questionCount: detail.questionCount,
			completedAt: new Date().toISOString()
		};
		await progressRepo.saveAssessmentScore(score);
		oncomplete?.(score);
		if (detail.maxScore > 0 && detail.score / detail.maxScore >= passThreshold) {
			onassessmentcomplete?.();
		} else if (detail.maxScore === 0) {
			onassessmentcomplete?.();
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
<VendorQuizBlock manifest={manifest as never} quizRef={assessmentRef} oncomplete={(detail) => handleComplete(detail)} />
