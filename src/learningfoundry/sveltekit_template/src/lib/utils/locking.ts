// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * Pure functions for deriving locked / optional / module-complete state
 * from the curriculum config and the reactive progress store.
 *
 * The curriculum-level `locking` block on `curriculum.json` is the effective
 * config produced by the Python resolver — global-config merging happens
 * upstream, so the frontend has nothing else to consult.
 */
import type {
	Curriculum,
	LockingConfig,
	Module,
	ModuleProgress
} from '$lib/types/index.js';
import { interleaveModuleFlow } from '$lib/components/module-list.helpers.js';
import { computeAssessmentPassed } from './assessment-passed.js';

const DEFAULT_LOCKING: LockingConfig = { sequential: false, lesson_sequential: false };

/** Effective locking config for a curriculum. */
export function effectiveLocking(curriculum: Curriculum | null | undefined): LockingConfig {
	return curriculum?.locking ?? DEFAULT_LOCKING;
}

function isLessonComplete(
	progress: Record<string, ModuleProgress>,
	moduleId: string,
	lessonId: string
): boolean {
	// Strict equality with `'complete'` — `'opened'` and `'in_progress'`
	// (Story I.p / FR-P15) deliberately do NOT trigger the
	// `unlock_module_on_complete` cascade, do not contribute to module
	// completeness, and do not unlock the next sequential module.
	return progress[moduleId]?.lessons[lessonId]?.status === 'complete';
}

/**
 * A module is locked when:
 *   1. `module.locked === true` (explicit override), OR
 *   2. `locking.sequential` is on AND the previous module is not complete.
 * The first module is never locked by the sequential rule alone.
 * `module.locked === false` overrides the sequential rule.
 */
export function isModuleLocked(
	moduleIndex: number,
	curriculum: Curriculum,
	progress: Record<string, ModuleProgress>
): boolean {
	const mod = curriculum.modules[moduleIndex];
	if (!mod) return false;
	if (mod.locked === true) return true;
	if (mod.locked === false) return false;
	const locking = effectiveLocking(curriculum);
	if (!locking.sequential) return false;
	if (moduleIndex === 0) return false;
	const prev = curriculum.modules[moduleIndex - 1];
	return !isModuleComplete(prev.id, curriculum, progress);
}

/**
 * A lesson is locked only when `locking.lesson_sequential` is on
 * and the previous lesson within the same module is not complete.
 */
export function isLessonLocked(
	moduleId: string,
	lessonIndex: number,
	curriculum: Curriculum,
	progress: Record<string, ModuleProgress>
): boolean {
	const locking = effectiveLocking(curriculum);
	if (!locking.lesson_sequential) return false;
	if (lessonIndex === 0) return false;
	const mod = curriculum.modules.find((m) => m.id === moduleId);
	if (!mod) return false;
	const prev = mod.lessons[lessonIndex - 1];
	if (!prev) return false;
	return !isLessonComplete(progress, moduleId, prev.id);
}

/**
 * Return the IDs of sibling lessons that are optional within a module.
 *
 * If the module contains a key lesson with `unlock_module_on_complete: true`
 * and that key lesson is `complete` in the progress store, every other
 * lesson in the module is optional. Otherwise, the set is empty.
 */
export function getOptionalLessons(
	moduleId: string,
	curriculum: Curriculum,
	progress: Record<string, ModuleProgress>
): Set<string> {
	const result = new Set<string>();
	const mod = curriculum.modules.find((m) => m.id === moduleId);
	if (!mod) return result;
	const keyLesson = mod.lessons.find((l) => l.unlock_module_on_complete);
	if (!keyLesson) return result;
	if (!isLessonComplete(progress, moduleId, keyLesson.id)) return result;
	for (const l of mod.lessons) {
		if (l.id !== keyLesson.id) result.add(l.id);
	}
	return result;
}

/**
 * A module is complete when every non-optional lesson is `complete` AND
 * every threshold-bearing non-pre assessment has a passed score
 * (Story J.v). Optional lessons that happen to be complete still count
 * toward the curriculum-level totals, but they do not block module
 * completion.
 *
 * Why assessments gate completion: the sequential-module rule
 * (`locking.sequential`) consults `isModuleComplete(prev)` to decide
 * whether the next module is unlocked. Threshold-bearing assessments
 * are *gates*; their pass state must propagate to the cross-module rule
 * for "next module locked until post-assessment passed" to actually
 * work (the J.v acceptance criteria).
 *
 * `role: pre` is exempt — the J.v sharp-edge resolution: pre-assessments
 * with thresholds are diagnostic, not gates. Authors who want hard
 * pre-gating use `role: practice` with `position: { before_lesson: ... }`.
 */
export function isModuleComplete(
	moduleId: string,
	curriculum: Curriculum,
	progress: Record<string, ModuleProgress>
): boolean {
	const mod = curriculum.modules.find((m) => m.id === moduleId);
	if (!mod || mod.lessons.length === 0) return false;
	const optional = getOptionalLessons(moduleId, curriculum, progress);
	const required = mod.lessons.filter((l) => !optional.has(l.id));
	if (required.length === 0) {
		// All siblings were marked optional by an unlock_module_on_complete lesson;
		// the key lesson itself is required (it is not in `optional`).
		return false;
	}
	if (!required.every((l) => isLessonComplete(progress, moduleId, l.id))) {
		return false;
	}
	// Assessment gates (Story J.v).
	const scores = progress[moduleId]?.assessmentScores ?? {};
	for (const a of mod.assessments) {
		if (a.pass_threshold == null) continue; // informational, doesn't gate
		if (a.role === 'pre') continue; // soft-gate exception
		const score = scores[a.id];
		if (!score) return false;
		if (!computeAssessmentPassed(score, a.pass_threshold)) return false;
	}
	return true;
}

/** Convenience: build a `Set<moduleId>` of locked modules across the curriculum. */
export function lockedModuleIds(
	curriculum: Curriculum,
	progress: Record<string, ModuleProgress>
): Set<string> {
	const result = new Set<string>();
	curriculum.modules.forEach((m: Module, i: number) => {
		if (isModuleLocked(i, curriculum, progress)) result.add(m.id);
	});
	return result;
}

/**
 * Combined lock-state for everything inside one module's flow (Story J.v).
 *
 * Walks `interleaveModuleFlow(lessons, assessments)` in canonical order
 * and applies two rules:
 *
 *   1. **lesson_sequential** — each lesson whose prior sibling is not
 *      complete is locked (same rule the original `isLessonLocked` /
 *      `lockedLessonIds` already enforced).
 *   2. **Assessment threshold gate** — when an assessment carries a
 *      `pass_threshold` (and is not `role: pre` per the soft-gate
 *      convention), any item that appears *after* it in the flow is
 *      locked until that assessment has a recorded passed score.
 *      "Passed" is read-time via `computeAssessmentPassed` so a
 *      mid-curriculum threshold tweak re-evaluates against the active
 *      rule rather than freezing to the value at completion.
 *
 * Once the gate trips, both subsequent lessons and subsequent assessments
 * lock — a later post-assessment behind an unpassed earlier gate renders
 * locked too (test case 5 in the J.v spec).
 *
 * The thin per-purpose wrappers `lockedLessonIds` and
 * `lockedAssessmentIds` project this output into the consumer-facing
 * Sets `<LessonList>` already takes via props.
 */
export function lockedItemsInModule(
	moduleId: string,
	curriculum: Curriculum,
	progress: Record<string, ModuleProgress>
): { lockedLessons: Set<string>; lockedAssessments: Set<string> } {
	const lockedLessons = new Set<string>();
	const lockedAssessments = new Set<string>();
	const mod = curriculum.modules.find((m) => m.id === moduleId);
	if (!mod) return { lockedLessons, lockedAssessments };

	// Fold in `lesson_sequential` lessons first — that rule is orthogonal
	// to the assessment-gate rule below, and `interleaveModuleFlow` is
	// oblivious to it.
	mod.lessons.forEach((l, i) => {
		if (isLessonLocked(moduleId, i, curriculum, progress)) {
			lockedLessons.add(l.id);
		}
	});

	const scores = progress[moduleId]?.assessmentScores ?? {};
	const flow = interleaveModuleFlow(mod.lessons, mod.assessments);
	let gateBlocked = false;

	for (const item of flow) {
		if (item.kind === 'lesson') {
			if (gateBlocked) lockedLessons.add(item.lesson.id);
		} else {
			const a = item.assessment;
			if (gateBlocked) lockedAssessments.add(a.id);
			// After visiting this assessment, check whether it raises the
			// gate for items appearing *after* it.
			const thresholded = a.pass_threshold != null;
			const isPre = a.role === 'pre';
			if (thresholded && !isPre) {
				const score = scores[a.id];
				const passed = score
					? computeAssessmentPassed(score, a.pass_threshold)
					: false;
				if (!passed) gateBlocked = true;
			}
		}
	}

	return { lockedLessons, lockedAssessments };
}

/** Convenience: build a `Set<lessonId>` of locked lessons within a module. */
export function lockedLessonIds(
	moduleId: string,
	curriculum: Curriculum,
	progress: Record<string, ModuleProgress>
): Set<string> {
	return lockedItemsInModule(moduleId, curriculum, progress).lockedLessons;
}

/** Convenience: build a `Set<assessmentId>` of locked assessments within a module (Story J.v). */
export function lockedAssessmentIds(
	moduleId: string,
	curriculum: Curriculum,
	progress: Record<string, ModuleProgress>
): Set<string> {
	return lockedItemsInModule(moduleId, curriculum, progress).lockedAssessments;
}
