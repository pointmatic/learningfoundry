// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { currentPosition } from '$lib/stores/curriculum.js';

/**
 * Reset the active navigation position. Wired to the sidebar's
 * course-title link click so that returning to the dashboard collapses
 * the previously-expanded module and drops the active-lesson highlight.
 *
 * The cascade: `ModuleList`'s `$effect` watches `$currentPosition` and
 * calls `computeAutoExpand`, which on a null position (and a prior
 * auto-expand) emits `{ expandedModuleId: null, lastAutoExpandedModuleId:
 * null }`. The active-module highlight CSS in `ModuleList` reads
 * `$currentPosition?.moduleId` directly, so clearing the store also
 * removes the highlight in the same render pass.
 *
 * Same store reset that `ResetCourseButton` and `Navigation` (FR-P14
 * Finish) already perform — see those components for the established
 * pattern.
 */
export function clearActivePosition(): void {
	currentPosition.set(null);
}
