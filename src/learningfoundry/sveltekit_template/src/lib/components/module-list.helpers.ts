// Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0
/**
 * Module list helpers.
 *
 * Extracted from `ModuleList.svelte` so the auto-expand and active-highlight
 * logic can be unit-tested without mounting the full component (which depends
 * on Svelte stores and the DOM).
 */

/**
 * Determine whether the sidebar should auto-expand a module because the
 * current navigation position has moved to a new module.
 *
 * Returns the new `expandedModuleId` and `lastAutoExpandedModuleId` values,
 * or `null` if no auto-expand should happen (i.e. the module was already
 * auto-expanded or there is no current position).
 */
export function computeAutoExpand(
	currentModuleId: string | undefined,
	lastAutoExpandedModuleId: string | null
): { expandedModuleId: string; lastAutoExpandedModuleId: string } | null {
	if (!currentModuleId) return null;
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
 */
export function lessonStatusIcon(
	lessonId: string,
	status: 'complete' | 'in_progress' | 'not_started' | undefined,
	optionalLessons: Set<string>
): string {
	if (status === 'complete') return '✓';
	if (status === 'in_progress') return '…';
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
