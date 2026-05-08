// Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0
/**
 * Module list helpers.
 *
 * Extracted from `ModuleList.svelte` so the auto-expand and active-highlight
 * logic can be unit-tested without mounting the full component (which depends
 * on Svelte stores and the DOM).
 */

/**
 * Determine how the sidebar should react to a change in the current
 * navigation position.
 *
 * Returns:
 * - `null` — no change required (position is null and nothing was
 *   previously auto-expanded; or the current module already matches
 *   the last auto-expanded module).
 * - `{ expandedModuleId: null, lastAutoExpandedModuleId: null }` — the
 *   position was just cleared (FR-P14: Finish on the last lesson);
 *   collapse the previously expanded module and forget the auto-expand
 *   anchor so the next manual toggle starts from a clean slate.
 * - `{ expandedModuleId, lastAutoExpandedModuleId }` — auto-expand the
 *   new module (and remember it as the auto-expand anchor so manual
 *   toggles aren't reverted; see Story I.f).
 */
export function computeAutoExpand(
	currentModuleId: string | null | undefined,
	lastAutoExpandedModuleId: string | null
): { expandedModuleId: string | null; lastAutoExpandedModuleId: string | null } | null {
	if (!currentModuleId) {
		// Position cleared. Only emit a reset if we previously auto-expanded
		// — otherwise we'd loop forever rewriting the same null values.
		if (lastAutoExpandedModuleId !== null) {
			return { expandedModuleId: null, lastAutoExpandedModuleId: null };
		}
		return null;
	}
	if (currentModuleId === lastAutoExpandedModuleId) return null;
	return {
		expandedModuleId: currentModuleId,
		lastAutoExpandedModuleId: currentModuleId,
	};
}

/**
 * Return the CSS class string for the active module highlight.
 * An active module (the one containing the current lesson) receives a
 * left-border accent and a light background tint.
 */
export function activeModuleClass(
	moduleId: string,
	currentModuleId: string | undefined
): string {
	return moduleId === currentModuleId
		? 'border-l-2 border-l-blue-500 bg-blue-50'
		: '';
}

/**
 * Decide how a click on a module header should be handled.
 *
 * - `'noop'` — module is locked; click is suppressed.
 * - `'collapse'` — clicking the currently-expanded module collapses it.
 * - module id — expand the clicked module.
 */
export function resolveModuleHeaderClick(
	clickedId: string,
	expandedModuleId: string | null,
	lockedModules: Set<string>
): { kind: 'noop' } | { kind: 'collapse' } | { kind: 'expand'; id: string } {
	if (lockedModules.has(clickedId)) return { kind: 'noop' };
	if (expandedModuleId === clickedId) return { kind: 'collapse' };
	return { kind: 'expand', id: clickedId };
}

/**
 * Decide how a click on a lesson row should be handled.
 *
 * - `'noop'` — lesson is locked; click is suppressed.
 * - `'navigate'` — proceed to navigate to the lesson.
 */
export function resolveLessonClick(
	lessonId: string,
	lockedLessons: Set<string>
): 'noop' | 'navigate' {
	return lockedLessons.has(lessonId) ? 'noop' : 'navigate';
}

/**
 * Sidebar lesson status icon — accounts for `optional` rendering.
 *
 * `opened` (Story I.p / FR-P15) deliberately shares the `…` icon with
 * `in_progress` so the learner sees a single "started" symbol; the
 * underlying data distinction exists for analytics / future hooks only.
 */
export function lessonStatusIcon(
	lessonId: string,
	status: 'complete' | 'in_progress' | 'opened' | 'not_started' | undefined,
	optionalLessons: Set<string>
): string {
	if (status === 'complete') return '✓';
	if (status === 'in_progress' || status === 'opened') return '…';
	if (optionalLessons.has(lessonId)) return '◇';
	return '○';
}

/**
 * Determine what action the Next/Finish button should perform.
 *
 * - `'navigate'` — there is a next lesson; `navigateTo(next)`.
 * - `'complete'` — no next lesson and an `onComplete` callback exists;
 *   call it (which navigates to the dashboard).
 * - `'noop'` — no next lesson and no callback; button press is a no-op.
 */
export type NextAction = 'navigate' | 'complete' | 'noop';

export function resolveNextAction(
	hasNext: boolean,
	hasOnComplete: boolean
): NextAction {
	if (hasNext) return 'navigate';
	if (hasOnComplete) return 'complete';
	return 'noop';
}

// ---------------------------------------------------------------------------
// Story J.f — module flow interleave. The resolver emits assessments in
// canonical placement order with a `position` field still attached; this
// helper walks lessons + assessments and returns a single mixed list the
// component can iterate without re-resolving placement.
// ---------------------------------------------------------------------------

import type { AssessmentDefinition, Lesson } from '$lib/types/index.js';

export type ModuleFlowItem =
	| { kind: 'lesson'; lesson: Lesson }
	| { kind: 'assessment'; assessment: AssessmentDefinition };

/**
 * Build the rendered module-flow sequence: lessons interleaved with
 * assessments at each one's resolved `position` (Story J.f).
 *
 * Placement rules — match the resolver's canonical order so the array
 * the resolver emitted reads back identically here:
 *
 *   1. `position === 'before_lessons'` → at the start of the flow.
 *   2. For each lesson:
 *      a. `{ before_lesson: <id> }` matches → render before the lesson.
 *      b. The lesson row.
 *      c. `{ after_lesson: <id> }` matches → render after the lesson.
 *   3. `position === 'after_lessons'` → at the end of the flow.
 *
 * Author order is preserved within each placement bucket. Lesson-anchored
 * assessments whose target lesson does not exist in `lessons` are silently
 * dropped — the parser already rejects unknown refs at build time
 * (`Module.validate_assessment_lesson_refs`), so this is a defensive belt.
 */
export function interleaveModuleFlow(
	lessons: Lesson[],
	assessments: AssessmentDefinition[]
): ModuleFlowItem[] {
	const beforeAll: AssessmentDefinition[] = [];
	const afterAll: AssessmentDefinition[] = [];
	const byBeforeId = new Map<string, AssessmentDefinition[]>();
	const byAfterId = new Map<string, AssessmentDefinition[]>();

	for (const a of assessments) {
		const pos = a.position;
		if (pos === 'before_lessons') {
			beforeAll.push(a);
		} else if (pos === 'after_lessons') {
			afterAll.push(a);
		} else if (typeof pos === 'object' && pos !== null && 'before_lesson' in pos) {
			const bucket = byBeforeId.get(pos.before_lesson) ?? [];
			bucket.push(a);
			byBeforeId.set(pos.before_lesson, bucket);
		} else if (typeof pos === 'object' && pos !== null && 'after_lesson' in pos) {
			const bucket = byAfterId.get(pos.after_lesson) ?? [];
			bucket.push(a);
			byAfterId.set(pos.after_lesson, bucket);
		}
	}

	const out: ModuleFlowItem[] = [];
	for (const a of beforeAll) out.push({ kind: 'assessment', assessment: a });
	for (const lesson of lessons) {
		for (const a of byBeforeId.get(lesson.id) ?? []) {
			out.push({ kind: 'assessment', assessment: a });
		}
		out.push({ kind: 'lesson', lesson });
		for (const a of byAfterId.get(lesson.id) ?? []) {
			out.push({ kind: 'assessment', assessment: a });
		}
	}
	for (const a of afterAll) out.push({ kind: 'assessment', assessment: a });
	return out;
}

/**
 * Capitalize the first letter of an open-string assessment role
 * (Story J.f). Trailing characters preserved verbatim so e.g. `pre` →
 * `Pre`, `practice` → `Practice`, `checkpoint-1` → `Checkpoint-1`.
 */
export function capitalizeRole(role: string): string {
	if (role.length === 0) return role;
	return role[0].toUpperCase() + role.slice(1);
}

/**
 * Format a `pass_threshold` (0.0–1.0) as a "70% to pass" annotation
 * (Story J.f). Returns `null` when the threshold is unset or out of
 * range so the caller can branch on a single value.
 */
export function formatPassThreshold(threshold: number | null | undefined): string | null {
	if (threshold == null || threshold <= 0 || threshold > 1) return null;
	return `${Math.round(threshold * 100)}% to pass`;
}
