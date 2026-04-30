// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0

// ---------------------------------------------------------------------------
// Content block types — mirror learningfoundry.resolver.ResolvedContentBlock
// ---------------------------------------------------------------------------

export interface TextContent {
	markdown: string;
	path: string;
}

/** Known video players (YAML `provider`); extend when backend adds literals. */
export type VideoProvider = 'youtube';

export interface VideoContent {
	url: string;
	/** Omitted in older curriculum.json; treated as `youtube`. */
	provider?: VideoProvider;
	/** Player-specific payload (chapters, transcripts, …). Omitted when empty. */
	extensions?: Record<string, unknown>;
}

export interface QuizManifest {
	quizName: string;
	tree: unknown[];
	questions: QuizQuestion[];
	[key: string]: unknown;
}

export interface QuizQuestion {
	id: string;
	text: string;
	answers: QuizAnswer[];
	[key: string]: unknown;
}

export interface QuizAnswer {
	id: string;
	text: string;
	weight: number;
	[key: string]: unknown;
}

export interface ExerciseContent {
	type: 'exercise';
	source: string;
	ref: string;
	status: string;
	title: string;
	instructions: string;
	sections: unknown[];
	expected_outputs: unknown[];
	hints: unknown[];
	environment: string | null;
}

export interface VisualizationContent {
	type: 'visualization';
	source: string;
	ref: string;
	status: string;
	title: string;
	caption: string;
	render_type: string;
	content: string;
	content_type: string;
	alt_text: string;
}

export type ContentBlockType = 'text' | 'video' | 'quiz' | 'exercise' | 'visualization';

export interface ContentBlock {
	type: ContentBlockType;
	source: string | null;
	ref: string | null;
	content: TextContent | VideoContent | QuizManifest | ExerciseContent | VisualizationContent | Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Curriculum structure — mirror learningfoundry.resolver.ResolvedCurriculum
// ---------------------------------------------------------------------------

export interface Lesson {
	id: string;
	title: string;
	content_blocks: ContentBlock[];
}

export interface Module {
	id: string;
	title: string;
	description: string;
	pre_assessment: QuizManifest | null;
	post_assessment: QuizManifest | null;
	lessons: Lesson[];
}

export interface Curriculum {
	version: string;
	title: string;
	description: string;
	modules: Module[];
}

// ---------------------------------------------------------------------------
// Progress tracking
// ---------------------------------------------------------------------------

export type LessonStatus = 'not_started' | 'in_progress' | 'complete';
export type ModuleStatus = 'not_started' | 'in_progress' | 'complete';

export interface LessonProgress {
	lessonId: string;
	moduleId: string;
	status: LessonStatus;
	completedAt: string | null;
}

export interface QuizScore {
	quizRef: string;
	score: number;
	maxScore: number;
	questionCount: number;
	completedAt: string;
}

export interface ModuleProgress {
	moduleId: string;
	status: ModuleStatus;
	lessons: Record<string, LessonProgress>;
	preAssessment: QuizScore | null;
	postAssessment: QuizScore | null;
}

export interface CurriculumProgress {
	curriculumVersion: string;
	modules: Record<string, ModuleProgress>;
	lastVisited: { moduleId: string; lessonId: string } | null;
}
