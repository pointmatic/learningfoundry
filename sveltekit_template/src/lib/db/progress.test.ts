// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// `vi.mock` is hoisted to the top of the file, so any references inside
// the factory must come from `vi.hoisted` (which is also hoisted).
const { execMock, runMock, persistMock } = vi.hoisted(() => ({
	execMock: vi.fn(),
	runMock: vi.fn(),
	persistMock: vi.fn().mockResolvedValue(undefined)
}));

vi.mock('./database.js', () => ({
	getDb: vi.fn().mockResolvedValue({ exec: execMock, run: runMock }),
	persistDb: () => persistMock()
}));

import { markLessonInProgress, markLessonOpened, resetProgress } from './progress.js';

describe('resetProgress', () => {
	beforeEach(() => {
		execMock.mockClear();
		runMock.mockClear();
		persistMock.mockClear();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('truncates lesson_progress, quiz_scores, and exercise_status in a single transaction', async () => {
		await resetProgress();
		expect(execMock).toHaveBeenCalledTimes(1);
		const sql = String(execMock.mock.calls[0][0]);
		expect(sql).toMatch(/BEGIN;/);
		expect(sql).toMatch(/DELETE FROM lesson_progress;/);
		expect(sql).toMatch(/DELETE FROM quiz_scores;/);
		expect(sql).toMatch(/DELETE FROM exercise_status;/);
		expect(sql).toMatch(/COMMIT;/);
	});

	it('persists after the truncate', async () => {
		await resetProgress();
		expect(persistMock).toHaveBeenCalledTimes(1);
	});
});

describe('markLessonOpened (Story I.p / FR-P15)', () => {
	beforeEach(() => {
		runMock.mockClear();
		persistMock.mockClear();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('writes status=opened on a fresh row', async () => {
		await markLessonOpened('mod-01', 'lesson-01');
		expect(runMock).toHaveBeenCalledTimes(1);
		const sql = String(runMock.mock.calls[0][0]);
		expect(sql).toMatch(/INSERT INTO lesson_progress/);
		expect(sql).toMatch(/'opened'/);
	});

	it('uses an upgrade-only conflict clause that preserves more advanced statuses', async () => {
		// We can't run a real DB here, but the SQL itself is the contract.
		// Validate the CASE expression preserves opened/in_progress/complete.
		await markLessonOpened('mod-01', 'lesson-01');
		const sql = String(runMock.mock.calls[0][0]);
		// Conflict path: leave existing status alone if it's already
		// opened/in_progress/complete; otherwise (e.g. some future
		// hypothetical status) coerce to 'opened'.
		expect(sql).toMatch(
			/ON CONFLICT.*DO UPDATE SET\s+status = CASE WHEN status IN \('opened', 'in_progress', 'complete'\)/s
		);
	});

	it('persists after the write', async () => {
		await markLessonOpened('mod-01', 'lesson-01');
		expect(persistMock).toHaveBeenCalledTimes(1);
	});
});

describe('markLessonInProgress (Story I.p caller-contract narrowing)', () => {
	beforeEach(() => {
		runMock.mockClear();
		persistMock.mockClear();
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('still writes in_progress with the complete-preserving conflict clause', async () => {
		// SQL itself is unchanged — only the caller contract narrowed
		// (now invoked on first block-engagement, not on mount). Lock
		// the SQL shape so a future "simplify" doesn't strip the
		// complete-preserving CASE.
		await markLessonInProgress('mod-01', 'lesson-01');
		const sql = String(runMock.mock.calls[0][0]);
		expect(sql).toMatch(/'in_progress'/);
		expect(sql).toMatch(
			/ON CONFLICT.*DO UPDATE SET\s+status = CASE WHEN status = 'complete' THEN 'complete' ELSE 'in_progress' END/s
		);
	});
});
