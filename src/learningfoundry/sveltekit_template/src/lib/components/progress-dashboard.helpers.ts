// Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0
/**
 * Progress dashboard helpers.
 *
 * Extracted from `ProgressDashboard.svelte` so curriculum-level progress
 * calculations can be unit-tested without mounting the component.
 */

import type { Curriculum, Module, ModuleProgress } from '$lib/types/index.js';
import { isModuleComplete } from '$lib/utils/locking.js';

/** Result of `moduleStatus`. Mirrors the `ModuleStatus` literal in the component. */
export type DashboardModuleStatus = 'not_started' | 'in_progress' | 'complete';

/**
 * Resolve the per-module dashboard status used to drive the
 * `Start module →` / `Continue →` / `✓ Complete` UI.
 *
 * Uses the rollup `mp.status` from `getModuleProgress` for the
 * in-progress branch (any non-`not_started` lesson rolls up as
 * `in_progress` at the module level). The complete branch defers to
 * `isModuleComplete` so optional-lessons handling is consistent.
 *
 * Anti-regression for v0.45.0–v0.52.0: the previous implementation
 * checked `done > 0` (count of `complete` lessons) and so left
 * "Start module →" stuck on modules whose lessons were merely
 * `opened` or `in_progress`.
 */
export function moduleStatus(
	mod: Module,
	progress: Record<string, ModuleProgress>,
	curriculum?: Curriculum | null
): DashboardModuleStatus {
	const mp = progress[mod.id];
	if (!mp || mod.lessons.length === 0) return 'not_started';
	const complete = curriculum
		? isModuleComplete(mod.id, curriculum, progress)
		: mp.status === 'complete';
	if (complete) return 'complete';
	return mp.status === 'in_progress' ? 'in_progress' : 'not_started';
}

/**
 * Count lessons with status `complete` in a module's progress record.
 */
export function completeLessonCount(
	mod: Module,
	progress: Record<string, ModuleProgress>
): number {
	const mp = progress[mod.id];
	if (!mp) return 0;
	return Object.values(mp.lessons).filter((l) => l.status === 'complete').length;
}

/**
 * Compute curriculum-level totals from an array of modules and their
 * progress records.
 */
export function curriculumTotals(
	modules: Module[],
	progress: Record<string, ModuleProgress>
): { totalLessons: number; totalComplete: number; overallPct: number } {
	const totalLessons = modules.reduce((n, m) => n + m.lessons.length, 0);
	const totalComplete = modules.reduce(
		(n, m) => n + completeLessonCount(m, progress),
		0
	);
	const overallPct =
		totalLessons === 0 ? 0 : Math.round((totalComplete / totalLessons) * 100);
	return { totalLessons, totalComplete, overallPct };
}
