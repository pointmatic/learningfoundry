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

export interface AssessmentManifest {
	assessmentName: string;
	tree: unknown[];
	questions: AssessmentQuestion[];
	passThreshold?: number;
	[key: string]: unknown;
}

export interface AssessmentQuestion {
	id: string;
	text: string;
	answers: AssessmentAnswer[];
	[key: string]: unknown;
}

export interface AssessmentAnswer {
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

export type ContentBlockType = 'text' | 'video' | 'assessment' | 'exercise' | 'visualization';

export interface ContentBlock {
	type: ContentBlockType;
	source: string | null;
	ref: string | null;
	content: TextContent | VideoContent | AssessmentManifest | ExerciseContent | VisualizationContent | Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Curriculum structure — mirror learningfoundry.resolver.ResolvedCurriculum
// ---------------------------------------------------------------------------

/** Opening hook for a lesson — mirrors `learningfoundry.schema_v1.Hook`. */
export interface Hook {
	tagline: string;
	image_prompt?: string | null;
	[key: string]: unknown;
}

/** Pedagogical metadata on a lesson — mirrors `learningfoundry.schema_v1.LessonMeta`. */
export interface LessonMeta {
	role?: string | null;
	hook?: Hook | null;
	introduces?: string[];
	reinforces?: string[];
	duration_minutes?: number | null;
	[key: string]: unknown;
}

/** Pedagogical metadata on a module — mirrors `learningfoundry.schema_v1.ModuleMeta`. */
export interface ModuleMeta {
	theme?: string | null;
	big_problem?: string | null;
	objectives?: string[];
	experiential_summary?: string | null;
	target_audience?: string | null;
	[key: string]: unknown;
}

/** Pedagogical metadata on a curriculum — mirrors `learningfoundry.schema_v1.CurriculumMeta` (Story J.h). */
export interface CurriculumMeta {
	target_audience?: string | null;
	objectives?: string[];
	prerequisites?: string[];
	[key: string]: unknown;
}

export interface Lesson {
	id: string;
	title: string;
	content_blocks: ContentBlock[];
	/** When this lesson completes, mark sibling lessons in this module as optional and unlock the next module. */
	unlock_module_on_complete?: boolean;
	meta?: LessonMeta | null;
}

/**
 * Position of an assessment within a module's flow (Story J.e).
 * Either anchored to the start/end of the lesson list, or to a specific
 * lesson by id (`{ before_lesson: 'lesson-07' }` /
 * `{ after_lesson: 'lesson-07' }`).
 */
export type AssessmentPosition =
	| 'before_lessons'
	| 'after_lessons'
	| { before_lesson: string }
	| { after_lesson: string };

/**
 * A single assessment bound to a module at a declared position
 * (Story J.e). Replaces the legacy two-slot `pre_assessment` /
 * `post_assessment` fields. The order in `Module.assessments` is the
 * canonical iteration order resolved at build time.
 */
export interface AssessmentDefinition {
	role: string;
	position: AssessmentPosition;
	source: string;
	ref: string;
	pass_threshold: number | null;
	content: AssessmentManifest;
}

export interface Module {
	id: string;
	title: string;
	description: string;
	/** Assessments in canonical placement order — emitted by the resolver. */
	assessments: AssessmentDefinition[];
	lessons: Lesson[];
	/** Per-module override. `null`/omitted = inherit from curriculum/global locking config. */
	locked?: boolean | null;
	meta?: ModuleMeta | null;
}

export interface LockingConfig {
	sequential: boolean;
	lesson_sequential: boolean;
}

export interface Curriculum {
	version: string;
	title: string;
	description: string;
	modules: Module[];
	locking?: LockingConfig;
	/** Sum of `lesson.meta.duration_minutes` across the curriculum (Story J.c). `null` when no lesson contributes. */
	total_duration_minutes?: number | null;
	meta?: CurriculumMeta | null;
}

// ---------------------------------------------------------------------------
// Progress tracking
// ---------------------------------------------------------------------------

// Lifecycle order: not_started → opened (mount) → in_progress (first
// block engage) → complete. `optional` is orthogonal — it overlays the
// lifecycle for sibling lessons of an `unlock_module_on_complete` key
// lesson. The sidebar visually merges `opened` with `in_progress`
// (FR-P15 / Story I.p).
export type LessonStatus =
	| 'not_started'
	| 'opened'
	| 'in_progress'
	| 'complete'
	| 'optional';
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
