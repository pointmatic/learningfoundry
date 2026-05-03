// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Story I.aa.2 — locking failsafe at the lesson route. The sidebar
// already filters locked modules from clicks (Story I.i / I.j), but a
// learner who types or bookmarks a locked-lesson URL would otherwise
// land on the full LessonView, bypassing the locking model entirely.
// The route must render a "locked" placeholder instead.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import type { Curriculum, ModuleProgress } from '$lib/types/index.js';

const { pageState } = vi.hoisted(() => ({
	pageState: { params: { module: 'mod-02', lesson: 'lesson-01' } }
}));

vi.mock('$app/state', () => ({ page: pageState }));
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

// Real writables so the page reactively reads the curriculum + progress.
const curriculumStore = writable<Curriculum | null>(null);
const progressStore = writable<Record<string, ModuleProgress>>({});

vi.mock('$lib/stores/curriculum.js', async () => {
	const actual = await vi.importActual<
		typeof import('$lib/stores/curriculum.js')
	>('$lib/stores/curriculum.js');
	return {
		...actual,
		curriculum: curriculumStore,
		navigateTo: vi.fn()
	};
});

vi.mock('$lib/stores/progress.js', async () => {
	const actual = await vi.importActual<
		typeof import('$lib/stores/progress.js')
	>('$lib/stores/progress.js');
	return {
		...actual,
		progressStore,
		invalidateProgress: vi.fn()
	};
});

// LessonView's onMount writes through the SQLite repo on lesson open,
// which would touch `localStorage` / IDB / the wasm fetch — none wired
// up under this test. Stub the repo to no-op so we can assert purely on
// the route's render decision.
vi.mock('$lib/db/index.js', () => ({
	progressRepo: {
		markLessonOpened: vi.fn().mockResolvedValue(undefined),
		markLessonInProgress: vi.fn().mockResolvedValue(undefined),
		markLessonComplete: vi.fn().mockResolvedValue(undefined),
		recordQuizScore: vi.fn().mockResolvedValue(undefined),
		recordExerciseStatus: vi.fn().mockResolvedValue(undefined),
		getLessonProgress: vi.fn().mockResolvedValue(null),
		listAllProgress: vi.fn().mockResolvedValue([])
	},
	database: { getDb: vi.fn(), persist: vi.fn() }
}));

function makeCurriculum(): Curriculum {
	return {
		version: '1.0.0',
		title: 'T',
		description: '',
		locking: { sequential: true, lesson_sequential: false },
		modules: [
			{
				id: 'mod-01',
				title: 'M1',
				description: '',
				locked: null,
				pre_assessment: null,
				post_assessment: null,
				lessons: [
					{
						id: 'lesson-01',
						title: 'L1',
						unlock_module_on_complete: false,
						content_blocks: []
					}
				]
			},
			{
				id: 'mod-02',
				title: 'M2',
				description: '',
				locked: null,
				pre_assessment: null,
				post_assessment: null,
				lessons: [
					{
						id: 'lesson-01',
						title: 'L1',
						unlock_module_on_complete: false,
						content_blocks: []
					}
				]
			}
		]
	} as Curriculum;
}

describe('lesson route — locking failsafe (Story I.aa.2)', () => {
	beforeEach(() => {
		curriculumStore.set(null);
		progressStore.set({});
		pageState.params = { module: 'mod-02', lesson: 'lesson-01' };
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('renders a Locked placeholder (not the LessonView) when navigating directly to a lesson in a sequentially-locked module', async () => {
		curriculumStore.set(makeCurriculum());
		progressStore.set({});  // Module 1 not complete → Module 2 locked.

		const Page = (await import('./+page.svelte')).default;
		const { container } = render(Page);

		// LessonView mounts an <article> root; locked placeholder must not.
		expect(container.querySelector('article')).toBeNull();
		// Placeholder should announce the locked state.
		expect(container.textContent).toMatch(/locked/i);
		// And offer a return path to the dashboard.
		const link = container.querySelector('a[href="/"]');
		expect(link).not.toBeNull();
	});

	it('renders the LessonView when the requested lesson is in an unlocked module', async () => {
		curriculumStore.set(makeCurriculum());
		progressStore.set({});
		pageState.params = { module: 'mod-01', lesson: 'lesson-01' };

		const Page = (await import('./+page.svelte')).default;
		const { container } = render(Page);

		// Module 1 is the first sequential module → not locked.
		expect(container.querySelector('article')).not.toBeNull();
		expect(container.textContent ?? '').not.toMatch(/this lesson is locked/i);
	});
});
