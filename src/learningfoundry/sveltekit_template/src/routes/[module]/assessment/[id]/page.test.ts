// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Story J.s — assessment route page test. Mirrors the lesson page
// test's mocking strategy: vendor `<QuizBlock>` is stubbed so the
// route's prop-forwarding to `<AssessmentBlock>` can be asserted
// without booting quizazz's real machinery. The progress repo is
// stubbed because `<AssessmentBlock>` calls `saveAssessmentScore`
// internally on every completion event.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/svelte';
import { writable } from 'svelte/store';
import type {
	AssessmentManifest,
	AssessmentScore,
	Curriculum
} from '$lib/types/index.js';

const { pageState, capturedProps, saveAssessmentScoreMock } = vi.hoisted(() => ({
	pageState: { params: { module: 'mod-01', id: 'pre' } as Record<string, string> },
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	capturedProps: { current: null as any },
	saveAssessmentScoreMock: vi.fn().mockResolvedValue(undefined)
}));

vi.mock('$app/state', () => ({ page: pageState }));
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

// Stub the vendor `<QuizBlock>` — record props for assertions, render
// nothing. Same shape as `AssessmentBlock.test.ts`.
vi.mock('@pointmatic/quizazz', () => {
	function VendorQuizBlockStub(_anchor: unknown, props: Record<string, unknown>) {
		capturedProps.current = props;
		return {};
	}
	return { QuizBlock: VendorQuizBlockStub };
});

vi.mock('$lib/db/index.js', () => ({
	progressRepo: { saveAssessmentScore: saveAssessmentScoreMock },
	database: { getDb: vi.fn(), persist: vi.fn() }
}));

const curriculumStore = writable<Curriculum | null>(null);

vi.mock('$lib/stores/curriculum.js', async () => {
	const actual = await vi.importActual<typeof import('$lib/stores/curriculum.js')>(
		'$lib/stores/curriculum.js'
	);
	return {
		...actual,
		curriculum: curriculumStore,
		navigateTo: vi.fn()
	};
});

const manifest: AssessmentManifest = {
	assessmentName: 'Module 1 Pre-Assessment',
	tree: [],
	questions: []
};

function makeCurriculum(): Curriculum {
	return {
		version: '1.0.0',
		title: 'T',
		description: '',
		locking: { sequential: false, lesson_sequential: false },
		modules: [
			{
				id: 'mod-01',
				title: 'M1',
				description: '',
				locked: null,
				assessments: [
					{
						id: 'pre',
						role: 'pre',
						position: 'before_lessons',
						source: 'quizazz',
						ref: 'assessments/mod-01-pre.yml',
						pass_threshold: null,
						content: manifest
					},
					{
						id: 'post',
						role: 'post',
						position: 'after_lessons',
						source: 'quizazz',
						ref: 'assessments/mod-01-post.yml',
						pass_threshold: 0.8,
						content: { ...manifest, assessmentName: 'M1 Post' }
					}
				],
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

describe('assessment route page (Story J.s)', () => {
	beforeEach(() => {
		curriculumStore.set(null);
		pageState.params = { module: 'mod-01', id: 'pre' };
		capturedProps.current = null;
	});

	afterEach(() => {
		// `@testing-library/svelte` does not auto-cleanup in this vitest
		// config — without explicit cleanup, the prior render's mounted
		// vendor stub stays alive and reactively re-writes
		// `capturedProps.current` (set in `beforeEach` to `null`) when
		// the next test mutates `curriculumStore` / `pageState.params`.
		cleanup();
		vi.clearAllMocks();
	});

	it('mounts <AssessmentBlock> with assessmentRef + manifest from the matched assessment', async () => {
		curriculumStore.set(makeCurriculum());

		const Page = (await import('./+page.svelte')).default;
		render(Page);

		expect(capturedProps.current).not.toBeNull();
		// The route forwards `ref` → `<AssessmentBlock>` → vendor as `quizRef`.
		expect(capturedProps.current?.quizRef).toBe('assessments/mod-01-pre.yml');
		expect(capturedProps.current?.manifest).toBe(manifest);
	});

	it('renders the capitalized role label in the page header', async () => {
		curriculumStore.set(makeCurriculum());
		pageState.params = { module: 'mod-01', id: 'post' };

		const Page = (await import('./+page.svelte')).default;
		const { container } = render(Page);

		expect(container.textContent).toMatch(/Post Assessment/);
	});

	it('renders "Assessment not found." when the id does not match any module assessment', async () => {
		curriculumStore.set(makeCurriculum());
		pageState.params = { module: 'mod-01', id: 'practice-99' };

		const Page = (await import('./+page.svelte')).default;
		const { container } = render(Page);

		expect(container.textContent).toMatch(/not found/i);
		// The vendor stub must not have been mounted on the unknown-id branch.
		expect(capturedProps.current).toBeNull();
	});

	it('renders "Assessment not found." when the module id does not match', async () => {
		curriculumStore.set(makeCurriculum());
		pageState.params = { module: 'mod-99', id: 'pre' };

		const Page = (await import('./+page.svelte')).default;
		const { container } = render(Page);

		expect(container.textContent).toMatch(/not found/i);
		expect(capturedProps.current).toBeNull();
	});

	it('completion callback signature accepts AssessmentScore (J.u-ready shape)', async () => {
		curriculumStore.set(makeCurriculum());

		const Page = (await import('./+page.svelte')).default;
		render(Page);

		// The vendor stub captured the `oncomplete` <AssessmentBlock> was
		// given. Drive a completion through it; the wrapper persists,
		// then invokes the route's stub callback with an `AssessmentScore`.
		const vendorOncomplete = capturedProps.current?.oncomplete as (
			d: unknown
		) => Promise<void>;
		await vendorOncomplete({
			quizRef: 'assessments/mod-01-pre.yml',
			score: 4,
			maxScore: 5,
			questionCount: 5
		});

		// AssessmentBlock persisted the score (its standard behaviour);
		// the route's no-op `handleComplete` ran without throwing — that
		// is the J.u-ready signature contract (`(score: AssessmentScore) => Promise<void>`).
		expect(saveAssessmentScoreMock).toHaveBeenCalledOnce();
		const persisted = saveAssessmentScoreMock.mock.calls[0][0] as AssessmentScore;
		expect(persisted.assessmentRef).toBe('assessments/mod-01-pre.yml');
		expect(persisted.score).toBe(4);
	});
});
