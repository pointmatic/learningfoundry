// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// J.m.1 + J.m.5 — adapter contract between vendor `<QuizBlock>` from
// `@pointmatic/quizazz` and learningfoundry's `<AssessmentBlock>` wrapper
// (score-persistence + pass-threshold event protocol). The vendor component
// is replaced with a stub so the test exercises the wrapper's translation
// logic without booting quizazz's real SvelteKit + sql.js + IndexedDB
// machinery.
//
// J.m.4 — wrapper now constructs an `AssessmentScore` (with
// `assessmentRef`) from the vendor event's `quizRef` field, persists via
// `progressRepo.saveAssessmentScore`, and fires the renamed
// `onassessmentcomplete` callback.
//
// J.m.5 — wrapper's local prop renamed `quizRef` → `assessmentRef`; the
// wrapper forwards it to the vendor as `quizRef={assessmentRef}` so the
// vendor surface stays in vendor terminology.
import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import AssessmentBlock from './AssessmentBlock.svelte';
import type { AssessmentManifest, AssessmentScore } from '$lib/types/index.js';

// `capturedProps.current` is a runtime-only mutable slot that the stub
// vendor component writes its props to. We cast to `any` here because
// the mocked vendor component's exact prop shape is uninteresting to
// type-check (the test asserts specific keys directly) and the alternative
// (`Record<string, unknown>` plus narrowing) trips `svelte-check`'s strict
// indexed-access rules.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const { saveAssessmentScoreMock, capturedProps } = vi.hoisted(() => ({
	saveAssessmentScoreMock: vi.fn().mockResolvedValue(undefined),
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	capturedProps: { current: null as any }
}));

vi.mock('$lib/db/index.js', () => ({
	progressRepo: {
		saveAssessmentScore: saveAssessmentScoreMock
	}
}));

// Stub the vendor `<QuizBlock>` with a Svelte 5 component that records the
// props passed to it (so we can read back `manifest` / `quizRef` /
// `oncomplete`) and renders nothing.
vi.mock('@pointmatic/quizazz', () => {
	function VendorQuizBlockStub(_anchor: unknown, props: Record<string, unknown>) {
		capturedProps.current = props;
		return {};
	}
	return { QuizBlock: VendorQuizBlockStub };
});

const manifest: AssessmentManifest = {
	assessmentName: 'Test Assessment',
	tree: [],
	questions: []
};

describe('AssessmentBlock adapter — vendor integration boundary', () => {
	it('forwards manifest and assessmentRef → quizRef to the vendor component', () => {
		capturedProps.current = null;
		render(AssessmentBlock, {
			props: { manifest, assessmentRef: 'mod-01-pre' }
		});
		expect(capturedProps.current).not.toBeNull();
		expect(capturedProps.current?.manifest).toBe(manifest);
		// `quizRef` is preserved as the vendor's prop name; the wrapper
		// forwards `assessmentRef` to the vendor under its vendor name.
		expect(capturedProps.current?.quizRef).toBe('mod-01-pre');
		expect(typeof capturedProps.current?.oncomplete).toBe('function');
	});

	it('translates vendor complete event into an AssessmentScore and persists via progressRepo', async () => {
		saveAssessmentScoreMock.mockClear();
		capturedProps.current = null;
		const oncomplete = vi.fn();
		render(AssessmentBlock, {
			props: { manifest, assessmentRef: 'mod-01-pre', oncomplete }
		});
		const vendorOncomplete = capturedProps.current?.oncomplete as (d: unknown) => Promise<void>;
		await vendorOncomplete({ quizRef: 'mod-01-pre', score: 3, maxScore: 5, questionCount: 5 });

		expect(saveAssessmentScoreMock).toHaveBeenCalledOnce();
		const persisted = saveAssessmentScoreMock.mock.calls[0][0] as AssessmentScore;
		// Vendor's `quizRef` field maps to our `assessmentRef`.
		expect(persisted.assessmentRef).toBe('mod-01-pre');
		expect(persisted.score).toBe(3);
		expect(persisted.maxScore).toBe(5);
		expect(persisted.questionCount).toBe(5);
		expect(typeof persisted.completedAt).toBe('string');

		expect(oncomplete).toHaveBeenCalledOnce();
		expect(oncomplete).toHaveBeenCalledWith(persisted);
	});

	it('fires onassessmentcomplete only when score / maxScore >= passThreshold', async () => {
		saveAssessmentScoreMock.mockClear();
		capturedProps.current = null;
		const onassessmentcomplete = vi.fn();
		render(AssessmentBlock, {
			props: {
				manifest,
				assessmentRef: 'mod-01-pre',
				passThreshold: 0.6,
				onassessmentcomplete
			}
		});
		const vendorOncomplete = capturedProps.current?.oncomplete as (d: unknown) => Promise<void>;

		await vendorOncomplete({ quizRef: 'r', score: 2, maxScore: 5, questionCount: 5 });
		expect(onassessmentcomplete).not.toHaveBeenCalled();

		await vendorOncomplete({ quizRef: 'r', score: 4, maxScore: 5, questionCount: 5 });
		expect(onassessmentcomplete).toHaveBeenCalledOnce();
	});

	it('fires onassessmentcomplete on zero-question assessments (avoids div-by-zero gate)', async () => {
		saveAssessmentScoreMock.mockClear();
		capturedProps.current = null;
		const onassessmentcomplete = vi.fn();
		render(AssessmentBlock, {
			props: {
				manifest,
				assessmentRef: 'mod-01-empty',
				passThreshold: 0.5,
				onassessmentcomplete
			}
		});
		const vendorOncomplete = capturedProps.current?.oncomplete as (d: unknown) => Promise<void>;
		await vendorOncomplete({ quizRef: 'mod-01-empty', score: 0, maxScore: 0, questionCount: 0 });
		expect(onassessmentcomplete).toHaveBeenCalledOnce();
	});
});
