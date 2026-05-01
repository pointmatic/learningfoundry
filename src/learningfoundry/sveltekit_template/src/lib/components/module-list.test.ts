// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import {
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
