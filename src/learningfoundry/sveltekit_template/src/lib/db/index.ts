// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
export { getDb, persistDb } from './database.js';
export {
	getLessonProgress,
	getModuleProgress,
	getQuizScore,
	markLessonComplete,
	markLessonInProgress,
	saveQuizScore,
	updateExerciseStatus
} from './progress.js';
