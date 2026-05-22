// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import {
	capitalizeRole,
	computeAutoExpand,
	formatPassThreshold,
	interleaveModuleFlow,
	lessonStatusIcon,
	resolveLessonClick,
	resolveModuleHeaderClick
} from './module-list.helpers.js';
import type { AssessmentDefinition, Lesson } from '$lib/types/index.js';

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

// ---------------------------------------------------------------------------
// Story J.f — module-flow interleave + role / threshold formatting helpers
// ---------------------------------------------------------------------------

function lesson(id: string): Lesson {
	return { id, title: id, content_blocks: [] };
}

function assessment(
	role: string,
	position: AssessmentDefinition['position'],
	pass_threshold: number | null = null
): AssessmentDefinition {
	return {
		id: role,
		role,
		position,
		source: 'quizazz',
		ref: `a/${role}.yml`,
		pass_threshold,
		content: { assessmentName: role, tree: [], questions: [] }
	};
}

describe('interleaveModuleFlow (Story J.f)', () => {
	it('empty assessments returns lessons untouched', () => {
		const flow = interleaveModuleFlow([lesson('l-1'), lesson('l-2')], []);
		expect(flow.map((i) => i.kind)).toEqual(['lesson', 'lesson']);
	});

	it('before_lessons assessments render at the start', () => {
		const flow = interleaveModuleFlow(
			[lesson('l-1')],
			[assessment('pre', 'before_lessons')]
		);
		expect(flow.map((i) => i.kind)).toEqual(['assessment', 'lesson']);
	});

	it('after_lessons assessments render at the end', () => {
		const flow = interleaveModuleFlow(
			[lesson('l-1')],
			[assessment('post', 'after_lessons')]
		);
		expect(flow.map((i) => i.kind)).toEqual(['lesson', 'assessment']);
	});

	it('before_lesson and after_lesson interleave around the named lesson', () => {
		const flow = interleaveModuleFlow(
			[lesson('l-1'), lesson('l-2')],
			[
				assessment('practice-a', { before_lesson: 'l-2' }),
				assessment('practice-b', { after_lesson: 'l-1' })
			]
		);
		// Order: l-1, after_lesson:l-1, before_lesson:l-2, l-2.
		const items = flow.map((i) =>
			i.kind === 'lesson' ? `lesson:${i.lesson.id}` : `assess:${i.assessment.role}`
		);
		expect(items).toEqual([
			'lesson:l-1',
			'assess:practice-b',
			'assess:practice-a',
			'lesson:l-2'
		]);
	});

	it('all three position forms compose in canonical order', () => {
		const flow = interleaveModuleFlow(
			[lesson('l-1'), lesson('l-2')],
			[
				assessment('post', 'after_lessons'),
				assessment('practice', { before_lesson: 'l-2' }),
				assessment('pre', 'before_lessons')
			]
		);
		const roles = flow.flatMap((i) =>
			i.kind === 'assessment' ? [i.assessment.role] : []
		);
		expect(roles).toEqual(['pre', 'practice', 'post']);
	});

	it('lesson-anchored ref to a missing lesson is silently dropped', () => {
		// Defensive belt — parser already rejects unknown refs at build
		// time. The component must not crash if one slips through.
		const flow = interleaveModuleFlow(
			[lesson('l-1')],
			[assessment('orphan', { before_lesson: 'lesson-99' })]
		);
		expect(flow.map((i) => i.kind)).toEqual(['lesson']);
	});

	it('preserves author order among same-bucket entries', () => {
		const flow = interleaveModuleFlow(
			[lesson('l-1')],
			[
				assessment('a', 'before_lessons'),
				assessment('b', 'before_lessons'),
				assessment('c', 'before_lessons')
			]
		);
		const roles = flow.flatMap((i) =>
			i.kind === 'assessment' ? [i.assessment.role] : []
		);
		expect(roles).toEqual(['a', 'b', 'c']);
	});
});

describe('capitalizeRole / formatPassThreshold (Story J.f)', () => {
	it('capitalizeRole capitalises only the first letter', () => {
		expect(capitalizeRole('pre')).toBe('Pre');
		expect(capitalizeRole('practice')).toBe('Practice');
		expect(capitalizeRole('post')).toBe('Post');
		expect(capitalizeRole('checkpoint-1')).toBe('Checkpoint-1');
		expect(capitalizeRole('')).toBe('');
	});

	it('formatPassThreshold returns null for unset / out-of-range', () => {
		expect(formatPassThreshold(null)).toBeNull();
		expect(formatPassThreshold(undefined)).toBeNull();
		expect(formatPassThreshold(0)).toBeNull();
		expect(formatPassThreshold(-0.1)).toBeNull();
		expect(formatPassThreshold(1.1)).toBeNull();
	});

	it('formatPassThreshold renders as integer percent', () => {
		expect(formatPassThreshold(0.7)).toBe('70% to pass');
		expect(formatPassThreshold(0.85)).toBe('85% to pass');
		expect(formatPassThreshold(1)).toBe('100% to pass');
	});
});
