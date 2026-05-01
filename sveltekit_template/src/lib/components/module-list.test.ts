// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import {
	computeAutoExpand,
	lessonStatusIcon,
	resolveLessonClick,
	resolveModuleHeaderClick
} from './module-list.helpers.js';

describe('resolveModuleHeaderClick (locked module behavior)', () => {
	it('locked module click is no-op', () => {
		const result = resolveModuleHeaderClick(
			'mod-01',
			null,
			new Set(['mod-01'])
		);
		expect(result.kind).toBe('noop');
	});

	it('clicking the currently-expanded module collapses it', () => {
		const result = resolveModuleHeaderClick('mod-01', 'mod-01', new Set());
		expect(result.kind).toBe('collapse');
	});

	it('clicking a non-expanded unlocked module expands it', () => {
		const result = resolveModuleHeaderClick('mod-02', 'mod-01', new Set());
		expect(result).toEqual({ kind: 'expand', id: 'mod-02' });
	});
});

describe('resolveLessonClick', () => {
	it('locked lesson click is no-op', () => {
		expect(resolveLessonClick('lesson-02', new Set(['lesson-02']))).toBe('noop');
	});

	it('unlocked lesson click navigates', () => {
		expect(resolveLessonClick('lesson-01', new Set())).toBe('navigate');
	});
});

describe('lessonStatusIcon (optional rendering)', () => {
	it('shows ✓ for complete', () => {
		expect(lessonStatusIcon('l1', 'complete', new Set())).toBe('✓');
	});

	it('shows … for in_progress', () => {
		expect(lessonStatusIcon('l1', 'in_progress', new Set())).toBe('…');
	});

	it('shows … for opened (Story I.p — visually merged with in_progress)', () => {
		expect(lessonStatusIcon('l1', 'opened', new Set())).toBe('…');
	});

	it('shows ◇ for optional not-yet-started', () => {
		expect(lessonStatusIcon('l1', 'not_started', new Set(['l1']))).toBe('◇');
	});

	it('shows ◇ for optional with no progress record', () => {
		expect(lessonStatusIcon('l1', undefined, new Set(['l1']))).toBe('◇');
	});

	it('complete still wins over optional', () => {
		expect(lessonStatusIcon('l1', 'complete', new Set(['l1']))).toBe('✓');
	});

	it('shows ○ for default not-started, non-optional', () => {
		expect(lessonStatusIcon('l1', 'not_started', new Set())).toBe('○');
	});
});

describe('computeAutoExpand (FR-P14 sidebar reset on null position)', () => {
	it('expanding into a new module: returns expand instruction', () => {
		const result = computeAutoExpand('mod-01', null);
		expect(result).toEqual({
			expandedModuleId: 'mod-01',
			lastAutoExpandedModuleId: 'mod-01'
		});
	});

	it('staying in the same module: returns null (no-op)', () => {
		expect(computeAutoExpand('mod-01', 'mod-01')).toBeNull();
	});

	it('null position with no prior auto-expand: null (no-op, prevents re-run loop)', () => {
		expect(computeAutoExpand(null, null)).toBeNull();
	});

	it('null position after auto-expand: resets both expanded and last-auto', () => {
		expect(computeAutoExpand(null, 'mod-01')).toEqual({
			expandedModuleId: null,
			lastAutoExpandedModuleId: null
		});
	});

	it('after a Finish reset, subsequent auto-expand into a new module still works', () => {
		// First: position cleared from mod-01 → both reset to null.
		expect(computeAutoExpand(null, 'mod-01')).toEqual({
			expandedModuleId: null,
			lastAutoExpandedModuleId: null
		});
		// Then: navigating into mod-02 should auto-expand it (regression
		// check that I.f's manual-toggle preservation is still intact).
		expect(computeAutoExpand('mod-02', null)).toEqual({
			expandedModuleId: 'mod-02',
			lastAutoExpandedModuleId: 'mod-02'
		});
	});
});
