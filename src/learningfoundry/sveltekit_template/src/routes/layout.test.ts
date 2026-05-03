// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import {
	activeModuleClass,
	computeAutoExpand,
	resolveNextAction,
} from '$lib/components/module-list.helpers.js';
import { clearActivePosition } from './layout.helpers.js';
import { currentPosition, expandedModuleId } from '$lib/stores/curriculum.js';

// ---------------------------------------------------------------------------
// Bug 1 — Finish button calls goto('/') on last lesson
// ---------------------------------------------------------------------------

describe('resolveNextAction (Bug 1 — Finish navigation)', () => {
	it('returns "navigate" when there is a next lesson', () => {
		expect(resolveNextAction(true, true)).toBe('navigate');
		expect(resolveNextAction(true, false)).toBe('navigate');
	});

	it('returns "complete" on last lesson when onComplete is provided', () => {
		// This is the fix: +page.svelte now passes oncomplete={handleLessonComplete}
		// so Navigation.goNext() calls onComplete → goto('/')
		expect(resolveNextAction(false, true)).toBe('complete');
	});

	it('returns "noop" on last lesson when onComplete is missing', () => {
		// Before the fix, +page.svelte did not pass oncomplete — Finish was a no-op.
		expect(resolveNextAction(false, false)).toBe('noop');
	});
});

// ---------------------------------------------------------------------------
// Bug 2 — Sidebar expand/contract reverts immediately
// ---------------------------------------------------------------------------

describe('computeAutoExpand (Bug 2 — sidebar expand revert)', () => {
	it('auto-expands when navigating to a new module', () => {
		const result = computeAutoExpand('mod-02', null);
		expect(result).toEqual({
			expandedModuleId: 'mod-02',
			lastAutoExpandedModuleId: 'mod-02',
		});
	});

	it('auto-expands when currentPosition.moduleId changes to a different module', () => {
		const result = computeAutoExpand('mod-03', 'mod-01');
		expect(result).toEqual({
			expandedModuleId: 'mod-03',
			lastAutoExpandedModuleId: 'mod-03',
		});
	});

	it('does NOT re-fire when the current module was already auto-expanded', () => {
		// This is the core of the fix: once auto-expanded, a manual toggle
		// to another module should not be reverted by the effect.
		const result = computeAutoExpand('mod-01', 'mod-01');
		expect(result).toBeNull();
	});

	it('is a no-op when currentPosition is undefined and nothing was auto-expanded', () => {
		expect(computeAutoExpand(undefined, null)).toBeNull();
	});

	// FR-P14 (Story I.n): when the position transitions from a real
	// module to undefined/null after a prior auto-expand (e.g. Finish on
	// the last lesson), the sidebar collapses by resetting both fields.
	it('resets when currentPosition is undefined after a prior auto-expand', () => {
		expect(computeAutoExpand(undefined, 'mod-01')).toEqual({
			expandedModuleId: null,
			lastAutoExpandedModuleId: null
		});
	});
});

// ---------------------------------------------------------------------------
// Bug 3 — No active module highlight
// ---------------------------------------------------------------------------

describe('activeModuleClass (Bug 3 — active module highlight)', () => {
	it('applies highlight class to the module matching currentPosition', () => {
		const cls = activeModuleClass('mod-01', 'mod-01');
		expect(cls).toContain('border-l-2');
		expect(cls).toContain('border-l-blue-500');
		expect(cls).toContain('bg-blue-50');
	});

	it('returns empty string for non-active modules', () => {
		expect(activeModuleClass('mod-02', 'mod-01')).toBe('');
	});

	it('returns empty string when currentPosition is undefined', () => {
		expect(activeModuleClass('mod-01', undefined)).toBe('');
	});

	it('only applies to the exact matching module', () => {
		const modules = ['mod-01', 'mod-02', 'mod-03'];
		const currentId = 'mod-02';
		const results = modules.map((id) => activeModuleClass(id, currentId));
		expect(results.filter((c) => c !== '')).toHaveLength(1);
		expect(results[1]).toContain('border-l-blue-500');
	});
});

// ---------------------------------------------------------------------------
// Bug 4 — Sidebar still shows expanded module + highlighted lesson when the
// learner clicks the course title to return to the dashboard.
//
// Cascading behaviour: ModuleList's `$effect` watches `$currentPosition`
// and uses `computeAutoExpand` to collapse on a *non-null → null*
// transition (already covered by the test above at line ~67); the
// active-highlight CSS reads `$currentPosition?.moduleId` directly.
//
// Story I.aa.1 added a second store reset: `expandedModuleId` is cleared
// directly so a *manually*-expanded module also collapses. The effect
// path alone could not handle this case because Svelte 5's `$store`
// short-circuits a `set(null)` on an already-null value via `Object.is`.
// ---------------------------------------------------------------------------

describe('clearActivePosition (Story I.y / I.aa.1 — sidebar collapse on home nav)', () => {
	it('sets currentPosition to null', () => {
		currentPosition.set({ moduleId: 'mod-01', lessonId: 'lesson-01' });
		expect(get(currentPosition)).not.toBeNull();
		clearActivePosition();
		expect(get(currentPosition)).toBeNull();
	});

	it('leaves currentPosition null when it was already null', () => {
		currentPosition.set(null);
		clearActivePosition();
		expect(get(currentPosition)).toBeNull();
	});

	it('clears expandedModuleId so a manually-expanded module collapses on title click (Story I.aa.1)', () => {
		expandedModuleId.set('mod-01');
		currentPosition.set(null);
		clearActivePosition();
		expect(get(expandedModuleId)).toBeNull();
	});

	it('clears expandedModuleId regardless of whether a lesson was active (covers both I.y and I.aa.1 paths)', () => {
		expandedModuleId.set('mod-02');
		currentPosition.set({ moduleId: 'mod-02', lessonId: 'lesson-01' });
		clearActivePosition();
		expect(get(expandedModuleId)).toBeNull();
		expect(get(currentPosition)).toBeNull();
	});
});
