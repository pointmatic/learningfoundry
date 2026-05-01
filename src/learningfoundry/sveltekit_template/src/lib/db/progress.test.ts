// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// `vi.mock` is hoisted to the top of the file, so any references inside
// the factory must come from `vi.hoisted` (which is also hoisted).
const { execMock, persistMock } = vi.hoisted(() => ({
	execMock: vi.fn(),
	persistMock: vi.fn().mockResolvedValue(undefined)
}));

vi.mock('./database.js', () => ({
	getDb: vi.fn().mockResolvedValue({ exec: execMock, run: vi.fn() }),
	persistDb: () => persistMock()
}));

import { resetProgress } from './progress.js';

describe('resetProgress', () => {
	beforeEach(() => {
		execMock.mockClear();
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
