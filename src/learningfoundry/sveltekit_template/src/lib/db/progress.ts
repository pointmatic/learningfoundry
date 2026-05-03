// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * Repository for learner progress. Wraps a `Database` instance and
 * exposes CRUD operations on the lesson_progress / quiz_scores /
 * exercise_status tables. All write methods call `database.persist()`
 * to flush to IndexedDB.
 *
 * Story I.bb — `WasmAssetMissingError` handling: when the sql.js WASM
 * asset is unavailable, every read and write would otherwise reject at
 * `database.getDb()`. The layout-level `dbInit` store surfaces a
 * recoverable banner; per-call rejections are an information duplicate
 * once the banner is up, so this module *swallows* `WasmAssetMissingError`:
 *
 * - Writes resolve as no-ops (the data was never going to land anyway).
 * - Reads return their "no progress yet" sentinel (`null` for single-row
 *   getters, an empty `ModuleProgress` for `getModuleProgress`).
 *
 * Other rejections still propagate — only the typed wasm-missing case is
 * suppressed. UI components don't need to defend against that case on
 * every call site.
 */
import { WasmAssetMissingError } from './database.js';
import type { Database } from './database.js';
import type {
	LessonProgress,
	LessonStatus,
	ModuleProgress,
	QuizScore
} from '$lib/types/index.js';

function isWasmMissing(err: unknown): err is WasmAssetMissingError {
	return err instanceof WasmAssetMissingError;
}

export class ProgressRepo {
	#database: Database;

	constructor(database: Database) {
		this.#database = database;
	}

	// -------------------------------------------------------------------
	// Lesson progress
	// -------------------------------------------------------------------

	async markLessonComplete(moduleId: string, lessonId: string): Promise<void> {
		try {
			const db = await this.#database.getDb();
			db.run(
				`INSERT INTO lesson_progress (module_id, lesson_id, status, completed_at)
       VALUES (?, ?, 'complete', ?)
       ON CONFLICT(module_id, lesson_id) DO UPDATE SET status='complete', completed_at=excluded.completed_at`,
				[moduleId, lessonId, new Date().toISOString()]
			);
			await this.#database.persist();
		} catch (err) {
			if (isWasmMissing(err)) return;
			throw err;
		}
	}

	/**
	 * Promote a lesson row to `opened` if it does not already carry a more
	 * advanced status. Upgrade-only — never demotes `in_progress` or
	 * `complete`. Called from `LessonView.onMount` (Story I.p / FR-P15).
	 */
	async markLessonOpened(moduleId: string, lessonId: string): Promise<void> {
		try {
			const db = await this.#database.getDb();
			db.run(
				`INSERT INTO lesson_progress (module_id, lesson_id, status, completed_at)
       VALUES (?, ?, 'opened', NULL)
       ON CONFLICT(module_id, lesson_id) DO UPDATE SET
         status = CASE WHEN status IN ('opened', 'in_progress', 'complete')
                       THEN status
                       ELSE 'opened' END`,
				[moduleId, lessonId]
			);
			await this.#database.persist();
		} catch (err) {
			if (isWasmMissing(err)) return;
			throw err;
		}
	}

	/**
	 * Promote a lesson row to `in_progress`. Called from `LessonView` when
	 * the FIRST block-completion event fires for the current mount session
	 * — not on mount itself (Story I.p / FR-P15). `complete` is preserved.
	 */
	async markLessonInProgress(moduleId: string, lessonId: string): Promise<void> {
		try {
			const db = await this.#database.getDb();
			db.run(
				`INSERT INTO lesson_progress (module_id, lesson_id, status, completed_at)
       VALUES (?, ?, 'in_progress', NULL)
       ON CONFLICT(module_id, lesson_id) DO UPDATE SET
         status = CASE WHEN status = 'complete' THEN 'complete' ELSE 'in_progress' END`,
				[moduleId, lessonId]
			);
			await this.#database.persist();
		} catch (err) {
			if (isWasmMissing(err)) return;
			throw err;
		}
	}

	async getLessonProgress(
		moduleId: string,
		lessonId: string
	): Promise<LessonProgress | null> {
		try {
			const db = await this.#database.getDb();
			const result = db.exec(
				`SELECT module_id, lesson_id, status, completed_at
       FROM lesson_progress WHERE module_id = ? AND lesson_id = ?`,
				[moduleId, lessonId]
			);
			if (!result.length || !result[0].values.length) return null;
			const [mod_id, les_id, status, completed_at] = result[0].values[0] as [
				string,
				string,
				LessonStatus,
				string | null
			];
			return { moduleId: mod_id, lessonId: les_id, status, completedAt: completed_at };
		} catch (err) {
			if (isWasmMissing(err)) return null;
			throw err;
		}
	}

	// -------------------------------------------------------------------
	// Quiz scores
	// -------------------------------------------------------------------

	async saveQuizScore(score: Omit<QuizScore, 'completedAt'>): Promise<void> {
		try {
			const db = await this.#database.getDb();
			db.run(
				`INSERT INTO quiz_scores (quiz_ref, score, max_score, question_count, completed_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(quiz_ref) DO UPDATE SET
         score=excluded.score, max_score=excluded.max_score,
         question_count=excluded.question_count, completed_at=excluded.completed_at`,
				[score.quizRef, score.score, score.maxScore, score.questionCount, new Date().toISOString()]
			);
			await this.#database.persist();
		} catch (err) {
			if (isWasmMissing(err)) return;
			throw err;
		}
	}

	async getQuizScore(quizRef: string): Promise<QuizScore | null> {
		try {
			const db = await this.#database.getDb();
			const result = db.exec(
				`SELECT quiz_ref, score, max_score, question_count, completed_at
       FROM quiz_scores WHERE quiz_ref = ?`,
				[quizRef]
			);
			if (!result.length || !result[0].values.length) return null;
			const [quiz_ref, sc, max_sc, q_count, completed_at] = result[0].values[0] as [
				string,
				number,
				number,
				number,
				string
			];
			return {
				quizRef: quiz_ref,
				score: sc,
				maxScore: max_sc,
				questionCount: q_count,
				completedAt: completed_at
			};
		} catch (err) {
			if (isWasmMissing(err)) return null;
			throw err;
		}
	}

	// -------------------------------------------------------------------
	// Exercise status
	// -------------------------------------------------------------------

	async updateExerciseStatus(exerciseRef: string, status: LessonStatus): Promise<void> {
		try {
			const db = await this.#database.getDb();
			db.run(
				`INSERT INTO exercise_status (exercise_ref, status, updated_at)
       VALUES (?, ?, ?)
       ON CONFLICT(exercise_ref) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at`,
				[exerciseRef, status, new Date().toISOString()]
			);
			await this.#database.persist();
		} catch (err) {
			if (isWasmMissing(err)) return;
			throw err;
		}
	}

	// -------------------------------------------------------------------
	// Reset (course-scoped)
	// -------------------------------------------------------------------

	/**
	 * Truncate every progress table for the current curriculum and persist.
	 * Course-level reset only; per-module / per-lesson reset is deferred.
	 */
	async resetProgress(): Promise<void> {
		try {
			const db = await this.#database.getDb();
			db.exec(
				`BEGIN;
				 DELETE FROM lesson_progress;
				 DELETE FROM quiz_scores;
				 DELETE FROM exercise_status;
				 COMMIT;`
			);
			await this.#database.persist();
		} catch (err) {
			if (isWasmMissing(err)) return;
			throw err;
		}
	}

	// -------------------------------------------------------------------
	// Module progress summary
	// -------------------------------------------------------------------

	async getModuleProgress(moduleId: string, lessonIds: string[]): Promise<ModuleProgress> {
		try {
			const db = await this.#database.getDb();

			const lessonResult = db.exec(
				`SELECT lesson_id, status, completed_at FROM lesson_progress WHERE module_id = ?`,
				[moduleId]
			);
			const lessonMap: Record<string, LessonProgress> = {};
			if (lessonResult.length) {
				for (const row of lessonResult[0].values as [string, LessonStatus, string | null][]) {
					const [lessonId, status, completedAt] = row;
					lessonMap[lessonId] = { moduleId, lessonId, status, completedAt };
				}
			}
			for (const lessonId of lessonIds) {
				if (!(lessonId in lessonMap)) {
					lessonMap[lessonId] = {
						moduleId,
						lessonId,
						status: 'not_started',
						completedAt: null
					};
				}
			}

			const statuses = Object.values(lessonMap).map((l) => l.status);
			// `opened` (Story I.p) falls into the `s !== 'not_started'` branch and
			// surfaces as module-level `in_progress` — intentional, matches the
			// sidebar visual mapping (FR-P15).
			const moduleStatus = statuses.every((s) => s === 'complete')
				? 'complete'
				: statuses.some((s) => s !== 'not_started')
					? 'in_progress'
					: 'not_started';

			return {
				moduleId,
				status: moduleStatus,
				lessons: lessonMap,
				preAssessment: null,
				postAssessment: null
			};
		} catch (err) {
			if (isWasmMissing(err)) {
				// Read-path fallback: render an empty "not_started" module so the
				// dashboard shows the empty state rather than an error page.
				const lessonMap: Record<string, LessonProgress> = {};
				for (const lessonId of lessonIds) {
					lessonMap[lessonId] = {
						moduleId,
						lessonId,
						status: 'not_started',
						completedAt: null
					};
				}
				return {
					moduleId,
					status: 'not_started',
					lessons: lessonMap,
					preAssessment: null,
					postAssessment: null
				};
			}
			throw err;
		}
	}
}
