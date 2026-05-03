// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { currentPosition, expandedModuleId } from '$lib/stores/curriculum.js';

/**
 * Reset the active navigation position. Wired to the sidebar's
 * course-title link click so that returning to the dashboard collapses
 * the previously-expanded module and drops the active-lesson highlight.
 *
 * Resets two stores:
 * - `currentPosition`: drops the active-module highlight (the highlight
 *   CSS in `ModuleList` reads `$currentPosition?.moduleId` directly, so
 *   clearing the store removes the highlight in the same render pass).
 *   On a `non-null → null` transition, the auto-expand `$effect` in
 *   `ModuleList` also collapses the previously auto-expanded module
 *   (Story I.y / FR-P14).
 * - `expandedModuleId` (Story I.aa.1): collapses any module that was
 *   *manually* expanded from the dashboard. Necessary because Svelte 5
 *   short-circuits a `set(null)` on an already-null `$store` deref via
 *   `Object.is`-equality, so the effect path alone could not collapse a
 *   module when `currentPosition` was already null at the time of click.
 *
 * Same `currentPosition` reset that `ResetCourseButton` and `Navigation`
 * (FR-P14 Finish) already perform; those call sites also indirectly
 * collapse the sidebar via the auto-expand effect's reset branch (which
 * fires because their reset is a `non-null → null` transition).
 */
export function clearActivePosition(): void {
	currentPosition.set(null);
	expandedModuleId.set(null);
}
