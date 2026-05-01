// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import {
	getOptionalLessons,
	isLessonLocked,
	isModuleComplete,
	isModuleLocked,
	lockedLessonIds,
	lockedModuleIds
} from './locking.js';
import type {
	Curriculum,
	Lesson,
	LessonProgress,
	LockingConfig,
	Module,
	ModuleProgress
} from '$lib/types/index.js';

function makeLesson(id: string, opts: Partial<Lesson> = {}): Lesson {
	return { id, title: id, content_blocks: [], ...opts };
}

function makeModule(id: string, lessons: Lesson[], opts: Partial<Module> = {}): Module {
	return {
		id,
		title: id,
		description: '',
		pre_assessment: null,
		post_assessment: null,
		lessons,
		...opts
	};
}

function makeCurriculum(modules: Module[], locking?: LockingConfig): Curriculum {
	return {
		version: '1',
		title: 'test',
		description: '',
		modules,
		...(locking !== undefined ? { locking } : {})
	};
}

function makeProgress(
	moduleId: string,
	completeLessonIds: string[]
): ModuleProgress {
	const lessons: Record<string, LessonProgress> = {};
	for (const lid of completeLessonIds) {
		lessons[lid] = {
			moduleId,
			lessonId: lid,
			status: 'complete',
			completedAt: null
		};
	}
	return {
		moduleId,
		status: 'in_progress',
		lessons,
		preAssessment: null,
		postAssessment: null
	};
}

const SEQUENTIAL: LockingConfig = { sequential: true, lesson_sequential: false };
const LESSON_SEQ: LockingConfig = { sequential: false, lesson_sequential: true };

describe('isModuleLocked', () => {
	it('first module is never locked by sequential rule alone', () => {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')]);
		const m2 = makeModule('mod-02', [makeLesson('lesson-02')]);
		const cur = makeCurriculum([m1, m2], SEQUENTIAL);
		expect(isModuleLocked(0, cur, {})).toBe(false);
	});

	it('second module is locked when sequential and previous incomplete', () => {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')]);
		const m2 = makeModule('mod-02', [makeLesson('lesson-02')]);
		const cur = makeCurriculum([m1, m2], SEQUENTIAL);
		expect(isModuleLocked(1, cur, {})).toBe(true);
	});

	it('second module unlocked when previous complete', () => {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')]);
		const m2 = makeModule('mod-02', [makeLesson('lesson-02')]);
		const cur = makeCurriculum([m1, m2], SEQUENTIAL);
		const progress = { 'mod-01': makeProgress('mod-01', ['lesson-01']) };
		expect(isModuleLocked(1, cur, progress)).toBe(false);
	});

	it('locked: false override beats sequential rule', () => {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')]);
		const m2 = makeModule('mod-02', [makeLesson('lesson-02')], { locked: false });
		const cur = makeCurriculum([m1, m2], SEQUENTIAL);
		expect(isModuleLocked(1, cur, {})).toBe(false);
	});

	it('locked: true override forces locked even when previous complete', () => {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')]);
		const m2 = makeModule('mod-02', [makeLesson('lesson-02')], { locked: true });
		const cur = makeCurriculum([m1, m2], SEQUENTIAL);
		const progress = { 'mod-01': makeProgress('mod-01', ['lesson-01']) };
		expect(isModuleLocked(1, cur, progress)).toBe(true);
	});

	it('not locked when sequential is off and no override', () => {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')]);
		const m2 = makeModule('mod-02', [makeLesson('lesson-02')]);
		const cur = makeCurriculum([m1, m2]);
		expect(isModuleLocked(1, cur, {})).toBe(false);
	});
});

describe('isLessonLocked', () => {
	it('first lesson never locked', () => {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01'), makeLesson('lesson-02')]);
		const cur = makeCurriculum([m1], LESSON_SEQ);
		expect(isLessonLocked('mod-01', 0, cur, {})).toBe(false);
	});

	it('lesson 2 locked when lesson_sequential and lesson 1 incomplete', () => {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01'), makeLesson('lesson-02')]);
		const cur = makeCurriculum([m1], LESSON_SEQ);
		expect(isLessonLocked('mod-01', 1, cur, {})).toBe(true);
	});

	it('lesson 2 unlocked when lesson 1 complete', () => {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01'), makeLesson('lesson-02')]);
		const cur = makeCurriculum([m1], LESSON_SEQ);
		const progress = { 'mod-01': makeProgress('mod-01', ['lesson-01']) };
		expect(isLessonLocked('mod-01', 1, cur, progress)).toBe(false);
	});

	it('not locked when lesson_sequential is off', () => {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01'), makeLesson('lesson-02')]);
		const cur = makeCurriculum([m1]);
		expect(isLessonLocked('mod-01', 1, cur, {})).toBe(false);
	});
});

describe('getOptionalLessons', () => {
	it('returns empty set before key lesson complete', () => {
		const m1 = makeModule('mod-01', [
			makeLesson('lesson-01', { unlock_module_on_complete: true }),
			makeLesson('lesson-02'),
			makeLesson('lesson-03')
		]);
		const cur = makeCurriculum([m1]);
		const result = getOptionalLessons('mod-01', cur, {});
		expect(result.size).toBe(0);
	});

	it('returns all sibling IDs after key lesson complete', () => {
		const m1 = makeModule('mod-01', [
			makeLesson('lesson-01', { unlock_module_on_complete: true }),
			makeLesson('lesson-02'),
			makeLesson('lesson-03')
		]);
		const cur = makeCurriculum([m1]);
		const progress = { 'mod-01': makeProgress('mod-01', ['lesson-01']) };
		const result = getOptionalLessons('mod-01', cur, progress);
		expect(result).toEqual(new Set(['lesson-02', 'lesson-03']));
		expect(result.has('lesson-01')).toBe(false);
	});

	it('returns empty set when no key lesson exists', () => {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01'), makeLesson('lesson-02')]);
		const cur = makeCurriculum([m1]);
		const progress = { 'mod-01': makeProgress('mod-01', ['lesson-01', 'lesson-02']) };
		expect(getOptionalLessons('mod-01', cur, progress).size).toBe(0);
	});
});

describe('isModuleComplete', () => {
	it('false while non-optional lessons incomplete', () => {
		const m1 = makeModule('mod-01', [
			makeLesson('lesson-01'),
			makeLesson('lesson-02')
		]);
		const cur = makeCurriculum([m1]);
		const progress = { 'mod-01': makeProgress('mod-01', ['lesson-01']) };
		expect(isModuleComplete('mod-01', cur, progress)).toBe(false);
	});

	it('true when all non-optional lessons done', () => {
		const m1 = makeModule('mod-01', [
			makeLesson('lesson-01'),
			makeLesson('lesson-02')
		]);
		const cur = makeCurriculum([m1]);
		const progress = { 'mod-01': makeProgress('mod-01', ['lesson-01', 'lesson-02']) };
		expect(isModuleComplete('mod-01', cur, progress)).toBe(true);
	});

	it('optional lessons do not block completion', () => {
		const m1 = makeModule('mod-01', [
			makeLesson('lesson-01', { unlock_module_on_complete: true }),
			makeLesson('lesson-02'),
			makeLesson('lesson-03')
		]);
		const cur = makeCurriculum([m1]);
		// Key lesson complete → siblings optional → module complete
		const progress = { 'mod-01': makeProgress('mod-01', ['lesson-01']) };
		expect(isModuleComplete('mod-01', cur, progress)).toBe(true);
	});

	it('false when module has zero lessons', () => {
		const m1 = makeModule('mod-01', []);
		const cur = makeCurriculum([m1]);
		expect(isModuleComplete('mod-01', cur, {})).toBe(false);
	});
});

describe('lockedModuleIds / lockedLessonIds (set helpers)', () => {
	it('lockedModuleIds tracks all sequentially-locked modules', () => {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')]);
		const m2 = makeModule('mod-02', [makeLesson('lesson-02')]);
		const m3 = makeModule('mod-03', [makeLesson('lesson-03')]);
		const cur = makeCurriculum([m1, m2, m3], SEQUENTIAL);
		expect(lockedModuleIds(cur, {})).toEqual(new Set(['mod-02', 'mod-03']));
	});

	it('lockedLessonIds returns lessons locked within a single module', () => {
		const m1 = makeModule('mod-01', [
			makeLesson('lesson-01'),
			makeLesson('lesson-02'),
			makeLesson('lesson-03')
		]);
		const cur = makeCurriculum([m1], LESSON_SEQ);
		expect(lockedLessonIds('mod-01', cur, {})).toEqual(
			new Set(['lesson-02', 'lesson-03'])
		);
	});
});
