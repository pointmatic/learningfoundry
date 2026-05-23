// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * Story J.u — pure `passed` computation for module-level assessment
 * scores. Kept as a free function (not a method on `ModuleAssessmentScore`)
 * so it can be re-evaluated against a current YAML `pass_threshold` at
 * read time. Persisting `passed` at write time would freeze it to
 * whatever threshold was set when the learner completed the assessment;
 * a future tweak to the threshold would then desync the stored boolean
 * from the active rule.
 *
 * Semantics — matches the J.u story spec:
 *
 * - `passThreshold` is `null` (or `undefined`): the assessment is
 *   informational and never gates → `passed` is vacuously `true`.
 * - `passThreshold` is set: `passed` iff `score / maxScore >= threshold`.
 * - `maxScore === 0` with a non-null threshold: `passed = false` (no
 *   evidence the learner demonstrated competence; the threshold-author
 *   intended a gate).
 *
 * J.v's locking logic is the primary consumer.
 */
import type { ModuleAssessmentScore } from '$lib/types/index.js';

export function computeAssessmentPassed(
	score: Pick<ModuleAssessmentScore, 'score' | 'maxScore'>,
	passThreshold: number | null | undefined
): boolean {
	if (passThreshold === null || passThreshold === undefined) return true;
	if (score.maxScore === 0) return false;
	return score.score / score.maxScore >= passThreshold;
}
