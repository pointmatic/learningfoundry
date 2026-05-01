// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * Pure helpers for the reactive progress store.
 *
 * Used by `ResetCourseButton.svelte` to decide whether to enable the
 * destructive action: a course is "untouched" only when every lesson
 * across every module is `not_started`. Quiz scores and exercise
 * statuses are reflected back into `lesson_progress` via the
 * `markLessonInProgress` / `markLessonComplete` cascades, so this single
 * predicate covers all three tables. If a future feature lets either
 * advance independently of lesson state, extend this helper to read
 * from those tables directly.
 */
import type { ModuleProgress } from '$lib/types/index.js';

export function hasAnyProgress(
	store: Record<string, ModuleProgress>
): boolean {
	for (const mp of Object.values(store)) {
		for (const lp of Object.values(mp.lessons)) {
			if (lp.status !== 'not_started') return true;
		}
	}
	return false;
}
