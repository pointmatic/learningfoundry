// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import {
	getOptionalLessons,
	isLessonLocked,
	isModuleComplete,
	isModuleLocked,
	lockedAssessmentIds,
	lockedItemsInModule,
	lockedLessonIds,
	lockedModuleIds
} from './locking.js';
import type {
	AssessmentDefinition,
	Curriculum,
	Lesson,
	LessonProgress,
	LockingConfig,
	Module,
	ModuleAssessmentScore,
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
		assessments: [],
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
		assessmentScores: {}
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

// ---------------------------------------------------------------------------
// Story J.v — post-assessment threshold gating + soft pre-assessment.
// ---------------------------------------------------------------------------

function makeAssessment(
	id: string,
	role: string,
	position: AssessmentDefinition['position'],
	pass_threshold: number | null = null
): AssessmentDefinition {
	return {
		id,
		role,
		position,
		source: 'quizazz',
		ref: `a/${id}.yml`,
		pass_threshold,
		content: { assessmentName: id, tree: [], questions: [] }
	};
}

function makeProgressWithAssessments(
	moduleId: string,
	completeLessonIds: string[],
	scores: Record<string, { score: number; maxScore: number }>
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
	const assessmentScores: Record<string, ModuleAssessmentScore> = {};
	for (const [assessmentId, raw] of Object.entries(scores)) {
		assessmentScores[assessmentId] = {
			moduleId,
			assessmentId,
			score: raw.score,
			maxScore: raw.maxScore,
			questionCount: raw.maxScore,
			completedAt: '2026-05-22T00:00:00.000Z'
		};
	}
	return {
		moduleId,
		status: 'in_progress',
		lessons,
		assessmentScores
	};
}

describe('Post-assessment threshold gate locks the next module (Story J.v)', () => {
	const postWithThreshold = makeAssessment('post', 'post', 'after_lessons', 0.7);

	function buildCurriculum(): Curriculum {
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')], {
			assessments: [postWithThreshold]
		});
		const m2 = makeModule('mod-02', [makeLesson('lesson-02')]);
		return makeCurriculum([m1, m2], SEQUENTIAL);
	}

	it('next module locked when post-assessment has pass_threshold and no recorded score', () => {
		const cur = buildCurriculum();
		// Lesson complete, but no recorded score for the post-assessment.
		const progress = {
			'mod-01': makeProgressWithAssessments('mod-01', ['lesson-01'], {})
		};
		expect(isModuleComplete('mod-01', cur, progress)).toBe(false);
		expect(isModuleLocked(1, cur, progress)).toBe(true);
	});

	it('next module locked when recorded score is below the threshold', () => {
		const cur = buildCurriculum();
		const progress = {
			'mod-01': makeProgressWithAssessments('mod-01', ['lesson-01'], {
				post: { score: 3, maxScore: 5 } // 0.6 < 0.7
			})
		};
		expect(isModuleComplete('mod-01', cur, progress)).toBe(false);
		expect(isModuleLocked(1, cur, progress)).toBe(true);
	});

	it('next module unlocked when recorded score meets the threshold', () => {
		const cur = buildCurriculum();
		const progress = {
			'mod-01': makeProgressWithAssessments('mod-01', ['lesson-01'], {
				post: { score: 4, maxScore: 5 } // 0.8 >= 0.7
			})
		};
		expect(isModuleComplete('mod-01', cur, progress)).toBe(true);
		expect(isModuleLocked(1, cur, progress)).toBe(false);
	});
});

describe('Pre-assessment is soft-gate regardless of threshold (Story J.v)', () => {
	it('lesson 1 is NOT locked behind an unpassed pre-assessment with threshold', () => {
		const pre = makeAssessment('pre', 'pre', 'before_lessons', 0.7);
		const m1 = makeModule('mod-01', [makeLesson('lesson-01'), makeLesson('lesson-02')], {
			assessments: [pre]
		});
		const cur = makeCurriculum([m1]);
		// Pre-assessment scored at 0/5 (below threshold) — yet lesson-01
		// must remain accessible because diagnostic pre-assessments are
		// the J.v soft-gate exception.
		const progress = {
			'mod-01': makeProgressWithAssessments('mod-01', [], {
				pre: { score: 0, maxScore: 5 }
			})
		};
		const { lockedLessons, lockedAssessments } = lockedItemsInModule(
			'mod-01',
			cur,
			progress
		);
		expect(lockedLessons.has('lesson-01')).toBe(false);
		expect(lockedLessons.has('lesson-02')).toBe(false);
		// The pre-assessment row itself is also not locked (soft-gate).
		expect(lockedAssessments.has('pre')).toBe(false);
	});

	it('module is complete even with an unrecorded pre-assessment (soft-gate exempt)', () => {
		const pre = makeAssessment('pre', 'pre', 'before_lessons', 0.7);
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')], {
			assessments: [pre]
		});
		const cur = makeCurriculum([m1]);
		const progress = {
			'mod-01': makeProgressWithAssessments('mod-01', ['lesson-01'], {})
		};
		expect(isModuleComplete('mod-01', cur, progress)).toBe(true);
	});
});

describe('Two post-assessments in sequence (Story J.v)', () => {
	it('passing the first but not the second locks the second module', () => {
		// mod-01 has a passed post; mod-02 has an unpassed post. mod-03
		// follows mod-02 in sequential locking. The first pass should not
		// unlock the third module — the J.v "two post-assessments in
		// sequence" acceptance case.
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')], {
			assessments: [makeAssessment('post', 'post', 'after_lessons', 0.7)]
		});
		const m2 = makeModule('mod-02', [makeLesson('lesson-02')], {
			assessments: [makeAssessment('post', 'post', 'after_lessons', 0.7)]
		});
		const m3 = makeModule('mod-03', [makeLesson('lesson-03')]);
		const cur = makeCurriculum([m1, m2, m3], SEQUENTIAL);
		const progress = {
			'mod-01': makeProgressWithAssessments('mod-01', ['lesson-01'], {
				post: { score: 5, maxScore: 5 } // passed
			}),
			'mod-02': makeProgressWithAssessments('mod-02', ['lesson-02'], {
				post: { score: 2, maxScore: 5 } // failed
			})
		};
		// mod-02 is unlocked (mod-01 fully complete + post passed).
		expect(isModuleLocked(1, cur, progress)).toBe(false);
		// mod-03 stays locked — mod-02 isn't complete because of the unpassed post.
		expect(isModuleComplete('mod-02', cur, progress)).toBe(false);
		expect(isModuleLocked(2, cur, progress)).toBe(true);
	});
});

describe('Assessments without pass_threshold are informational and never gate (Story J.v)', () => {
	it('an unrecorded threshold-null assessment does not lock the next module', () => {
		const informational = makeAssessment('post', 'post', 'after_lessons', null);
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')], {
			assessments: [informational]
		});
		const m2 = makeModule('mod-02', [makeLesson('lesson-02')]);
		const cur = makeCurriculum([m1, m2], SEQUENTIAL);
		const progress = {
			'mod-01': makeProgressWithAssessments('mod-01', ['lesson-01'], {})
		};
		expect(isModuleComplete('mod-01', cur, progress)).toBe(true);
		expect(isModuleLocked(1, cur, progress)).toBe(false);
	});

	it('within a module, items after a threshold-null assessment are NOT locked even without a recorded score', () => {
		// `before_lessons` informational assessment + a lesson after it.
		// No threshold → no gate → lesson stays open.
		const informational = makeAssessment(
			'practice',
			'practice',
			'before_lessons',
			null
		);
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')], {
			assessments: [informational]
		});
		const cur = makeCurriculum([m1]);
		const { lockedLessons } = lockedItemsInModule('mod-01', cur, {});
		expect(lockedLessons.has('lesson-01')).toBe(false);
	});
});

describe('Within-module assessment gating (Story J.v)', () => {
	it('{before_lesson: lesson-X} threshold-gate locks lesson-X and everything after', () => {
		const gate = makeAssessment(
			'practice',
			'practice',
			{ before_lesson: 'lesson-02' },
			0.7
		);
		const m1 = makeModule(
			'mod-01',
			[makeLesson('lesson-01'), makeLesson('lesson-02'), makeLesson('lesson-03')],
			{ assessments: [gate] }
		);
		const cur = makeCurriculum([m1]);
		// No recorded score for the gate.
		const progress = {
			'mod-01': makeProgressWithAssessments('mod-01', [], {})
		};
		const { lockedLessons } = lockedItemsInModule('mod-01', cur, progress);
		// lesson-01 is before the gate → open.
		expect(lockedLessons.has('lesson-01')).toBe(false);
		// lesson-02 sits right after the gate → locked.
		expect(lockedLessons.has('lesson-02')).toBe(true);
		// lesson-03 also after the gate → locked.
		expect(lockedLessons.has('lesson-03')).toBe(true);
	});

	it('a later assessment after an unpassed earlier gate renders locked itself', () => {
		// `before_lessons` gate, then a `after_lessons` post-assessment.
		// The post-assessment is "after" the gate in flow order → locked.
		const gate = makeAssessment(
			'practice',
			'practice',
			'before_lessons',
			0.7
		);
		const post = makeAssessment('post', 'post', 'after_lessons', 0.7);
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')], {
			assessments: [gate, post]
		});
		const cur = makeCurriculum([m1]);
		const progress = {
			'mod-01': makeProgressWithAssessments('mod-01', [], {}) // neither passed
		};
		const { lockedAssessments } = lockedItemsInModule('mod-01', cur, progress);
		// The first gate is not locked (nothing precedes it).
		expect(lockedAssessments.has('practice')).toBe(false);
		// The post-assessment is downstream of the unpassed gate → locked.
		expect(lockedAssessments.has('post')).toBe(true);
	});

	it('lockedAssessmentIds returns the assessment-side projection', () => {
		const gate = makeAssessment(
			'practice',
			'practice',
			'before_lessons',
			0.7
		);
		const post = makeAssessment('post', 'post', 'after_lessons', null);
		const m1 = makeModule('mod-01', [makeLesson('lesson-01')], {
			assessments: [gate, post]
		});
		const cur = makeCurriculum([m1]);
		const progress = {
			'mod-01': makeProgressWithAssessments('mod-01', [], {})
		};
		expect(lockedAssessmentIds('mod-01', cur, progress)).toEqual(new Set(['post']));
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
