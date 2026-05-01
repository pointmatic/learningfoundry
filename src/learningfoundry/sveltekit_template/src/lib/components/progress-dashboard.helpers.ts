// Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0
/**
 * Progress dashboard helpers.
 *
 * Extracted from `ProgressDashboard.svelte` so curriculum-level progress
 * calculations can be unit-tested without mounting the component.
 */

import type { Module, ModuleProgress } from '$lib/types/index.js';

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
