// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * CRUD operations for learner progress stored in the sql.js database.
 * All write operations call persistDb() to flush to IndexedDB.
 */
import { getDb, persistDb } from './database.js';
import type { LessonProgress, LessonStatus, ModuleProgress, QuizScore } from '$lib/types/index.js';

// ---------------------------------------------------------------------------
// Lesson progress
// ---------------------------------------------------------------------------

export async function markLessonComplete(moduleId: string, lessonId: string): Promise<void> {
	const db = await getDb();
	db.run(
		`INSERT INTO lesson_progress (module_id, lesson_id, status, completed_at)
     VALUES (?, ?, 'complete', ?)
     ON CONFLICT(module_id, lesson_id) DO UPDATE SET status='complete', completed_at=excluded.completed_at`,
		[moduleId, lessonId, new Date().toISOString()]
	);
	await persistDb();
}

export async function markLessonInProgress(moduleId: string, lessonId: string): Promise<void> {
	const db = await getDb();
	db.run(
		`INSERT INTO lesson_progress (module_id, lesson_id, status, completed_at)
     VALUES (?, ?, 'in_progress', NULL)
     ON CONFLICT(module_id, lesson_id) DO UPDATE SET
       status = CASE WHEN status = 'complete' THEN 'complete' ELSE 'in_progress' END`,
		[moduleId, lessonId]
	);
	await persistDb();
}

export async function getLessonProgress(
	moduleId: string,
	lessonId: string
): Promise<LessonProgress | null> {
	const db = await getDb();
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
}

// ---------------------------------------------------------------------------
// Quiz scores
// ---------------------------------------------------------------------------

export async function saveQuizScore(score: Omit<QuizScore, 'completedAt'>): Promise<void> {
	const db = await getDb();
	db.run(
		`INSERT INTO quiz_scores (quiz_ref, score, max_score, question_count, completed_at)
     VALUES (?, ?, ?, ?, ?)
     ON CONFLICT(quiz_ref) DO UPDATE SET
       score=excluded.score, max_score=excluded.max_score,
       question_count=excluded.question_count, completed_at=excluded.completed_at`,
		[score.quizRef, score.score, score.maxScore, score.questionCount, new Date().toISOString()]
	);
	await persistDb();
}

export async function getQuizScore(quizRef: string): Promise<QuizScore | null> {
	const db = await getDb();
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
}

// ---------------------------------------------------------------------------
// Exercise status
// ---------------------------------------------------------------------------

export async function updateExerciseStatus(
	exerciseRef: string,
	status: LessonStatus
): Promise<void> {
	const db = await getDb();
	db.run(
		`INSERT INTO exercise_status (exercise_ref, status, updated_at)
     VALUES (?, ?, ?)
     ON CONFLICT(exercise_ref) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at`,
		[exerciseRef, status, new Date().toISOString()]
	);
	await persistDb();
}

// ---------------------------------------------------------------------------
// Module progress summary
// ---------------------------------------------------------------------------

export async function getModuleProgress(
	moduleId: string,
	lessonIds: string[]
): Promise<ModuleProgress> {
	const db = await getDb();

	// Lesson rows for this module
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
	// Fill in not_started for any lessons not yet touched
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
	const moduleStatus =
		statuses.every((s) => s === 'complete')
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
}
