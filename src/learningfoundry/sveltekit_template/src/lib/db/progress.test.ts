// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ProgressRepo } from './progress.js';
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

	it('truncates lesson_progress, quiz_scores, and exercise_status in a single transaction', async () => {
		await repo.resetProgress();
		expect(execMock).toHaveBeenCalledTimes(1);
		const sql = String(execMock.mock.calls[0][0]);
		expect(sql).toMatch(/BEGIN;/);
		expect(sql).toMatch(/DELETE FROM lesson_progress;/);
		expect(sql).toMatch(/DELETE FROM quiz_scores;/);
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
