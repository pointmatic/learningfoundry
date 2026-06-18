// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * Repository for learner progress. Wraps a `Database` instance and
 * exposes CRUD operations on the lesson_progress / assessment_scores /
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
	AssessmentScore,
	LessonProgress,
	LessonStatus,
	ModuleAssessmentScore,
	ModuleProgress
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
	// Assessment scores
	// -------------------------------------------------------------------

	async saveAssessmentScore(
		score: Omit<AssessmentScore, 'completedAt'>
	): Promise<void> {
		try {
			const db = await this.#database.getDb();
			db.run(
				`INSERT INTO assessment_scores
         (assessment_ref, score, max_score, question_count, completed_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(assessment_ref) DO UPDATE SET
         score=excluded.score, max_score=excluded.max_score,
         question_count=excluded.question_count, completed_at=excluded.completed_at`,
				[
					score.assessmentRef,
					score.score,
					score.maxScore,
					score.questionCount,
					new Date().toISOString()
				]
			);
			await this.#database.persist();
		} catch (err) {
			if (isWasmMissing(err)) return;
			throw err;
		}
	}

	/**
	 * Read a content-block-level assessment score by its global `ref`.
	 * Story J.u renamed this from `getAssessmentScore` to free that name
	 * for the new `(moduleId, assessmentId)` keyed lookup below — the
	 * two paths persist into different tables (`assessment_scores` vs.
	 * `module_assessment_scores`) for the reasons documented on the
	 * `module_assessment_scores` DDL in `database.ts`.
	 */
	async getAssessmentScoreByRef(assessmentRef: string): Promise<AssessmentScore | null> {
		try {
			const db = await this.#database.getDb();
			const result = db.exec(
				`SELECT assessment_ref, score, max_score, question_count, completed_at
       FROM assessment_scores WHERE assessment_ref = ?`,
				[assessmentRef]
			);
			if (!result.length || !result[0].values.length) return null;
			const [assessment_ref, sc, max_sc, q_count, completed_at] = result[0]
				.values[0] as [string, number, number, number, string];
			return {
				assessmentRef: assessment_ref,
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
	// Module-level assessment scores (Story J.u)
	// -------------------------------------------------------------------

	/**
	 * Persist a score for a module-level assessment. Distinct from
	 * `saveAssessmentScore` (which keys on the global `assessmentRef`)
	 * because two modules can reference the same quizazz YAML — the
	 * natural key here is `(moduleId, assessmentId)`. Called by the
	 * `[module]/assessment/[id]/+page.svelte` route's completion handler.
	 *
	 * Accepts the same `AssessmentScore` shape that `<AssessmentBlock>`
	 * already builds, then translates at the boundary so callers don't
	 * have to manually construct a `ModuleAssessmentScore` — `assessmentRef`
	 * is intentionally dropped (the module-level table doesn't carry it;
	 * the `(moduleId, assessmentId)` pair is the identity).
	 */
	async markAssessmentComplete(
		moduleId: string,
		assessmentId: string,
		score: Omit<AssessmentScore, 'completedAt'>
	): Promise<void> {
		try {
			const db = await this.#database.getDb();
			db.run(
				`INSERT INTO module_assessment_scores
         (module_id, assessment_id, score, max_score, question_count, completed_at)
       VALUES (?, ?, ?, ?, ?, ?)
       ON CONFLICT(module_id, assessment_id) DO UPDATE SET
         score=excluded.score, max_score=excluded.max_score,
         question_count=excluded.question_count, completed_at=excluded.completed_at`,
				[
					moduleId,
					assessmentId,
					score.score,
					score.maxScore,
					score.questionCount,
					new Date().toISOString()
				]
			);
			await this.#database.persist();
		} catch (err) {
			if (isWasmMissing(err)) return;
			throw err;
		}
	}

	/**
	 * Read a module-level assessment score by `(moduleId, assessmentId)`.
	 * Returns `null` when no score has been recorded — locking (J.v) reads
	 * this and treats `null` as "not yet attempted."
	 */
	async getAssessmentScore(
		moduleId: string,
		assessmentId: string
	): Promise<ModuleAssessmentScore | null> {
		try {
			const db = await this.#database.getDb();
			const result = db.exec(
				`SELECT module_id, assessment_id, score, max_score, question_count, completed_at
       FROM module_assessment_scores
       WHERE module_id = ? AND assessment_id = ?`,
				[moduleId, assessmentId]
			);
			if (!result.length || !result[0].values.length) return null;
			const [mod_id, ass_id, sc, max_sc, q_count, completed_at] = result[0]
				.values[0] as [string, string, number, number, number, string];
			return {
				moduleId: mod_id,
				assessmentId: ass_id,
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

	/**
	 * Read the persisted status for an exercise, or `null` if it has never been
	 * recorded. The banner uses this on load to derive its completed slate
	 * (Story K.j.1). Resolves `null` when the wasm asset is missing.
	 */
	async getExerciseStatus(exerciseRef: string): Promise<LessonStatus | null> {
		try {
			const db = await this.#database.getDb();
			const result = db.exec(
				`SELECT status FROM exercise_status WHERE exercise_ref = ?`,
				[exerciseRef]
			);
			if (!result.length || !result[0].values.length) return null;
			return result[0].values[0][0] as LessonStatus;
		} catch (err) {
			if (isWasmMissing(err)) return null;
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
				 DELETE FROM assessment_scores;
				 DELETE FROM module_assessment_scores;
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

			// Story J.u — load every module-level assessment score for this
			// module in one query, keyed by `assessmentId` on the way out.
			const assessmentResult = db.exec(
				`SELECT assessment_id, score, max_score, question_count, completed_at
       FROM module_assessment_scores WHERE module_id = ?`,
				[moduleId]
			);
			const assessmentScores: Record<string, ModuleAssessmentScore> = {};
			if (assessmentResult.length) {
				for (const row of assessmentResult[0].values as [
					string,
					number,
					number,
					number,
					string
				][]) {
					const [assessmentId, sc, max_sc, q_count, completedAt] = row;
					assessmentScores[assessmentId] = {
						moduleId,
						assessmentId,
						score: sc,
						maxScore: max_sc,
						questionCount: q_count,
						completedAt
					};
				}
			}

			return {
				moduleId,
				status: moduleStatus,
				lessons: lessonMap,
				assessmentScores
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
					assessmentScores: {}
				};
			}
			throw err;
		}
	}
}
