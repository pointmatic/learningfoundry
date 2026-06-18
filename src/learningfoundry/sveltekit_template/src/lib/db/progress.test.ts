// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ProgressRepo } from './progress.js';
import { WasmAssetMissingError } from './database.js';
import type { Database } from './database.js';

// I.w replaces the prior `vi.mock('./database.js', ...)` pattern with
// construction of a real `ProgressRepo` against a fake `Database` whose
// `getDb()` returns a stub carrying `exec` / `run` spies. The SQL-shape
// assertions below are unchanged — those contracts (especially the
// upgrade-only conflict CASE clause from Story I.p) remain locked.

const execMock = vi.fn();
const runMock = vi.fn();
const persistMock = vi.fn().mockResolvedValue(undefined);

function makeRepo(): ProgressRepo {
	const fakeDb = { exec: execMock, run: runMock };
	const fakeDatabase = {
		getDb: () => Promise.resolve(fakeDb),
		persist: () => persistMock()
	} as unknown as Database;
	return new ProgressRepo(fakeDatabase);
}

describe('resetProgress', () => {
	let repo: ProgressRepo;
	beforeEach(() => {
		execMock.mockClear();
		runMock.mockClear();
		persistMock.mockClear();
		repo = makeRepo();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('truncates lesson_progress, assessment_scores, module_assessment_scores, and exercise_status in a single transaction', async () => {
		await repo.resetProgress();
		expect(execMock).toHaveBeenCalledTimes(1);
		const sql = String(execMock.mock.calls[0][0]);
		expect(sql).toMatch(/BEGIN;/);
		expect(sql).toMatch(/DELETE FROM lesson_progress;/);
		expect(sql).toMatch(/DELETE FROM assessment_scores;/);
		expect(sql).toMatch(/DELETE FROM module_assessment_scores;/);
		expect(sql).toMatch(/DELETE FROM exercise_status;/);
		expect(sql).toMatch(/COMMIT;/);
	});

	it('persists after the truncate', async () => {
		await repo.resetProgress();
		expect(persistMock).toHaveBeenCalledTimes(1);
	});
});

describe('markLessonOpened (Story I.p / FR-P15)', () => {
	let repo: ProgressRepo;
	beforeEach(() => {
		runMock.mockClear();
		persistMock.mockClear();
		repo = makeRepo();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('writes status=opened on a fresh row', async () => {
		await repo.markLessonOpened('mod-01', 'lesson-01');
		expect(runMock).toHaveBeenCalledTimes(1);
		const sql = String(runMock.mock.calls[0][0]);
		expect(sql).toMatch(/INSERT INTO lesson_progress/);
		expect(sql).toMatch(/'opened'/);
	});

	it('uses an upgrade-only conflict clause that preserves more advanced statuses', async () => {
		// We can't run a real DB here, but the SQL itself is the contract.
		// Validate the CASE expression preserves opened/in_progress/complete.
		await repo.markLessonOpened('mod-01', 'lesson-01');
		const sql = String(runMock.mock.calls[0][0]);
		expect(sql).toMatch(
			/ON CONFLICT.*DO UPDATE SET\s+status = CASE WHEN status IN \('opened', 'in_progress', 'complete'\)/s
		);
	});

	it('persists after the write', async () => {
		await repo.markLessonOpened('mod-01', 'lesson-01');
		expect(persistMock).toHaveBeenCalledTimes(1);
	});
});

describe('markLessonInProgress (Story I.p caller-contract narrowing)', () => {
	let repo: ProgressRepo;
	beforeEach(() => {
		runMock.mockClear();
		persistMock.mockClear();
		repo = makeRepo();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('still writes in_progress with the complete-preserving conflict clause', async () => {
		// SQL itself is unchanged — only the caller contract narrowed
		// (now invoked on first block-engagement, not on mount). Lock
		// the SQL shape so a future "simplify" doesn't strip the
		// complete-preserving CASE.
		await repo.markLessonInProgress('mod-01', 'lesson-01');
		const sql = String(runMock.mock.calls[0][0]);
		expect(sql).toMatch(/'in_progress'/);
		expect(sql).toMatch(
			/ON CONFLICT.*DO UPDATE SET\s+status = CASE WHEN status = 'complete' THEN 'complete' ELSE 'in_progress' END/s
		);
	});
});

// ---------------------------------------------------------------------------
// Story J.u — per-module-assessment write path. Distinct from the
// content-block `saveAssessmentScore` path because it persists into the
// `module_assessment_scores` table keyed on `(moduleId, assessmentId)` so
// two modules referencing the same `assessmentRef` don't collide.
// ---------------------------------------------------------------------------

describe('markAssessmentComplete (Story J.u)', () => {
	let repo: ProgressRepo;
	beforeEach(() => {
		runMock.mockClear();
		persistMock.mockClear();
		repo = makeRepo();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('writes to module_assessment_scores with the (module_id, assessment_id) PK', async () => {
		await repo.markAssessmentComplete('mod-01', 'pre', {
			assessmentRef: 'assessments/mod-01-pre.yml',
			score: 4,
			maxScore: 5,
			questionCount: 5
		});
		expect(runMock).toHaveBeenCalledTimes(1);
		const sql = String(runMock.mock.calls[0][0]);
		expect(sql).toMatch(/INSERT INTO module_assessment_scores/);
		expect(sql).toMatch(
			/ON CONFLICT\(module_id, assessment_id\) DO UPDATE SET/
		);
		const params = runMock.mock.calls[0][1] as unknown[];
		expect(params[0]).toBe('mod-01');
		expect(params[1]).toBe('pre');
		expect(params[2]).toBe(4);
		expect(params[3]).toBe(5);
		expect(params[4]).toBe(5);
		// completedAt is the new Date().toISOString() — assert shape only.
		expect(typeof params[5]).toBe('string');
	});

	it('persists after the write', async () => {
		await repo.markAssessmentComplete('mod-01', 'pre', {
			assessmentRef: 'r',
			score: 0,
			maxScore: 0,
			questionCount: 0
		});
		expect(persistMock).toHaveBeenCalledTimes(1);
	});

	it('does not write the assessmentRef field (table has no ref column)', async () => {
		// Two writes from different modules with the same inbound
		// `assessmentRef` produce two independent rows keyed on
		// `(module_id, assessment_id)` — the ref is intentionally dropped at
		// the boundary. This is the collision-isolation contract from the
		// J.u story spec.
		await repo.markAssessmentComplete('mod-01', 'pre', {
			assessmentRef: 'shared-quiz.yml',
			score: 3,
			maxScore: 5,
			questionCount: 5
		});
		await repo.markAssessmentComplete('mod-02', 'pre', {
			assessmentRef: 'shared-quiz.yml',
			score: 4,
			maxScore: 5,
			questionCount: 5
		});
		expect(runMock).toHaveBeenCalledTimes(2);
		const sql0 = String(runMock.mock.calls[0][0]);
		expect(sql0).not.toMatch(/assessment_ref/);
		const params0 = runMock.mock.calls[0][1] as unknown[];
		const params1 = runMock.mock.calls[1][1] as unknown[];
		// Distinct module ids ensure the ON CONFLICT clause won't merge the
		// two rows even though the inbound refs match.
		expect(params0[0]).toBe('mod-01');
		expect(params1[0]).toBe('mod-02');
		// Neither param tuple contains the shared ref.
		expect(params0).not.toContain('shared-quiz.yml');
		expect(params1).not.toContain('shared-quiz.yml');
	});
});

describe('getAssessmentScore by (moduleId, assessmentId) (Story J.u)', () => {
	let repo: ProgressRepo;
	beforeEach(() => {
		execMock.mockClear();
		repo = makeRepo();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('reads from module_assessment_scores with the (module_id, assessment_id) where clause', async () => {
		execMock.mockReturnValueOnce([]);
		await repo.getAssessmentScore('mod-01', 'pre');
		expect(execMock).toHaveBeenCalledTimes(1);
		const sql = String(execMock.mock.calls[0][0]);
		expect(sql).toMatch(/FROM module_assessment_scores/);
		expect(sql).toMatch(/WHERE module_id = \? AND assessment_id = \?/);
		const params = execMock.mock.calls[0][1] as unknown[];
		expect(params).toEqual(['mod-01', 'pre']);
	});

	it('returns the row as a ModuleAssessmentScore when one exists', async () => {
		execMock.mockReturnValueOnce([
			{
				columns: [
					'module_id',
					'assessment_id',
					'score',
					'max_score',
					'question_count',
					'completed_at'
				],
				values: [['mod-01', 'pre', 4, 5, 5, '2026-05-22T00:00:00.000Z']]
			}
		]);
		const result = await repo.getAssessmentScore('mod-01', 'pre');
		expect(result).toEqual({
			moduleId: 'mod-01',
			assessmentId: 'pre',
			score: 4,
			maxScore: 5,
			questionCount: 5,
			completedAt: '2026-05-22T00:00:00.000Z'
		});
	});

	it('returns null when no row matches', async () => {
		execMock.mockReturnValueOnce([]);
		const result = await repo.getAssessmentScore('mod-99', 'practice');
		expect(result).toBeNull();
	});
});

describe('getExerciseStatus (Story K.j.1)', () => {
	let repo: ProgressRepo;
	beforeEach(() => {
		execMock.mockClear();
		repo = makeRepo();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('reads status from exercise_status with the exercise_ref where clause', async () => {
		execMock.mockReturnValueOnce([]);
		await repo.getExerciseStatus('mod-01-ex');
		expect(execMock).toHaveBeenCalledTimes(1);
		const sql = String(execMock.mock.calls[0][0]);
		expect(sql).toMatch(/FROM exercise_status/);
		expect(sql).toMatch(/WHERE exercise_ref = \?/);
		const params = execMock.mock.calls[0][1] as unknown[];
		expect(params).toEqual(['mod-01-ex']);
	});

	it('returns the persisted status when a row exists', async () => {
		execMock.mockReturnValueOnce([
			{ columns: ['status'], values: [['complete']] }
		]);
		const result = await repo.getExerciseStatus('mod-01-ex');
		expect(result).toBe('complete');
	});

	it('returns null when no row matches', async () => {
		execMock.mockReturnValueOnce([]);
		const result = await repo.getExerciseStatus('never-started');
		expect(result).toBeNull();
	});
});

describe('getModuleProgress assessmentScores (Story J.u)', () => {
	let repo: ProgressRepo;
	beforeEach(() => {
		execMock.mockClear();
		repo = makeRepo();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('populates assessmentScores keyed by assessmentId from module_assessment_scores', async () => {
		// First call: lesson_progress (empty). Second call:
		// module_assessment_scores (two rows). Order matches the SQL
		// sequence in `getModuleProgress`.
		execMock.mockReturnValueOnce([]);
		execMock.mockReturnValueOnce([
			{
				columns: ['assessment_id', 'score', 'max_score', 'question_count', 'completed_at'],
				values: [
					['pre', 3, 5, 5, '2026-05-22T00:00:00.000Z'],
					['post', 4, 5, 5, '2026-05-22T01:00:00.000Z']
				]
			}
		]);
		const mp = await repo.getModuleProgress('mod-01', ['lesson-01']);
		expect(Object.keys(mp.assessmentScores).sort()).toEqual(['post', 'pre']);
		expect(mp.assessmentScores['pre']).toEqual({
			moduleId: 'mod-01',
			assessmentId: 'pre',
			score: 3,
			maxScore: 5,
			questionCount: 5,
			completedAt: '2026-05-22T00:00:00.000Z'
		});
		expect(mp.assessmentScores['post'].score).toBe(4);
	});

	it('returns an empty assessmentScores map when no rows match', async () => {
		execMock.mockReturnValueOnce([]); // lesson_progress
		execMock.mockReturnValueOnce([]); // module_assessment_scores
		const mp = await repo.getModuleProgress('mod-01', ['lesson-01']);
		expect(mp.assessmentScores).toEqual({});
	});
});

// ---------------------------------------------------------------------------
// Story I.bb — `WasmAssetMissingError` is swallowed at the ProgressRepo
// boundary so UI components don't have to defend on every call site. The
// layout-level banner (`RecordingPausedBanner`) is the user-facing surface.
// ---------------------------------------------------------------------------

describe('ProgressRepo — WasmAssetMissingError handling (Story I.bb)', () => {
	function makeRepoWithBrokenDb(): ProgressRepo {
		const fakeDatabase = {
			getDb: () => Promise.reject(new WasmAssetMissingError('/sql-wasm.wasm')),
			persist: () => Promise.resolve()
		} as unknown as Database;
		return new ProgressRepo(fakeDatabase);
	}

	it('markLessonComplete resolves quietly when wasm is missing', async () => {
		const repo = makeRepoWithBrokenDb();
		await expect(repo.markLessonComplete('mod-01', 'lesson-01')).resolves.toBeUndefined();
	});

	it('markLessonOpened resolves quietly when wasm is missing', async () => {
		const repo = makeRepoWithBrokenDb();
		await expect(repo.markLessonOpened('mod-01', 'lesson-01')).resolves.toBeUndefined();
	});

	it('markLessonInProgress resolves quietly when wasm is missing', async () => {
		const repo = makeRepoWithBrokenDb();
		await expect(repo.markLessonInProgress('mod-01', 'lesson-01')).resolves.toBeUndefined();
	});

	it('saveAssessmentScore resolves quietly when wasm is missing', async () => {
		const repo = makeRepoWithBrokenDb();
		await expect(
			repo.saveAssessmentScore({
				assessmentRef: 'q1',
				score: 1,
				maxScore: 1,
				questionCount: 1
			})
		).resolves.toBeUndefined();
	});

	it('updateExerciseStatus resolves quietly when wasm is missing', async () => {
		const repo = makeRepoWithBrokenDb();
		await expect(repo.updateExerciseStatus('ex1', 'complete')).resolves.toBeUndefined();
	});

	it('getExerciseStatus returns null when wasm is missing', async () => {
		const repo = makeRepoWithBrokenDb();
		await expect(repo.getExerciseStatus('ex1')).resolves.toBeNull();
	});

	it('resetProgress resolves quietly when wasm is missing', async () => {
		const repo = makeRepoWithBrokenDb();
		await expect(repo.resetProgress()).resolves.toBeUndefined();
	});

	it('getLessonProgress returns null when wasm is missing', async () => {
		const repo = makeRepoWithBrokenDb();
		await expect(repo.getLessonProgress('mod-01', 'lesson-01')).resolves.toBeNull();
	});

	it('getAssessmentScoreByRef returns null when wasm is missing', async () => {
		const repo = makeRepoWithBrokenDb();
		await expect(repo.getAssessmentScoreByRef('q1')).resolves.toBeNull();
	});

	it('markAssessmentComplete resolves quietly when wasm is missing', async () => {
		const repo = makeRepoWithBrokenDb();
		await expect(
			repo.markAssessmentComplete('mod-01', 'pre', {
				assessmentRef: 'assessments/pre.yml',
				score: 1,
				maxScore: 1,
				questionCount: 1
			})
		).resolves.toBeUndefined();
	});

	it('getAssessmentScore (moduleId, assessmentId) returns null when wasm is missing', async () => {
		const repo = makeRepoWithBrokenDb();
		await expect(repo.getAssessmentScore('mod-01', 'pre')).resolves.toBeNull();
	});

	it('getModuleProgress returns an empty not_started shape so the dashboard renders', async () => {
		const repo = makeRepoWithBrokenDb();
		const mp = await repo.getModuleProgress('mod-01', ['lesson-01', 'lesson-02']);
		expect(mp.moduleId).toBe('mod-01');
		expect(mp.status).toBe('not_started');
		expect(Object.keys(mp.lessons)).toEqual(['lesson-01', 'lesson-02']);
		expect(mp.lessons['lesson-01'].status).toBe('not_started');
		expect(mp.lessons['lesson-02'].completedAt).toBeNull();
		expect(mp.assessmentScores).toEqual({});
	});

	it('non-WASM errors still propagate', async () => {
		const fakeDatabase = {
			getDb: () => Promise.reject(new Error('something else broke')),
			persist: () => Promise.resolve()
		} as unknown as Database;
		const repo = new ProgressRepo(fakeDatabase);
		await expect(repo.markLessonComplete('mod-01', 'lesson-01')).rejects.toThrow(
			'something else broke'
		);
		await expect(repo.getLessonProgress('mod-01', 'lesson-01')).rejects.toThrow(
			'something else broke'
		);
	});
});
