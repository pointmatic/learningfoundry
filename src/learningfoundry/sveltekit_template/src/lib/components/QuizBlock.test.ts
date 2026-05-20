// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// J.m.1 — adapter contract between vendor `<QuizBlock>` from
// `@pointmatic/quizazz` and learningfoundry's score-persistence + pass-
// threshold event protocol. The vendor component is replaced with a stub
// so the test exercises the adapter's translation logic without booting
// quizazz's real SvelteKit + sql.js + IndexedDB machinery.
import { describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import QuizBlock from './QuizBlock.svelte';
import type { AssessmentManifest, QuizScore } from '$lib/types/index.js';

// `capturedProps.current` is a runtime-only mutable slot that the stub
// vendor component writes its props to. We cast to `any` here because
// the mocked vendor component's exact prop shape is uninteresting to
// type-check (the test asserts specific keys directly) and the alternative
// (`Record<string, unknown>` plus narrowing) trips `svelte-check`'s strict
// indexed-access rules.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const { saveQuizScoreMock, capturedProps } = vi.hoisted(() => ({
	saveQuizScoreMock: vi.fn().mockResolvedValue(undefined),
	// eslint-disable-next-line @typescript-eslint/no-explicit-any
	capturedProps: { current: null as any }
}));

vi.mock('$lib/db/index.js', () => ({
	progressRepo: {
		saveQuizScore: saveQuizScoreMock
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

describe('QuizBlock adapter — vendor integration boundary', () => {
	it('forwards manifest and quizRef props to the vendor component', () => {
		capturedProps.current = null;
		render(QuizBlock, {
			props: { manifest, quizRef: 'mod-01-pre' }
		});
		expect(capturedProps.current).not.toBeNull();
		expect(capturedProps.current?.manifest).toBe(manifest);
		expect(capturedProps.current?.quizRef).toBe('mod-01-pre');
		expect(typeof capturedProps.current?.oncomplete).toBe('function');
	});

	it('translates vendor complete event into a QuizScore and persists via progressRepo', async () => {
		saveQuizScoreMock.mockClear();
		capturedProps.current = null;
		const oncomplete = vi.fn();
		render(QuizBlock, {
			props: { manifest, quizRef: 'mod-01-pre', oncomplete }
		});
		const vendorOncomplete = capturedProps.current?.oncomplete as (d: unknown) => Promise<void>;
		await vendorOncomplete({ quizRef: 'mod-01-pre', score: 3, maxScore: 5, questionCount: 5 });

		expect(saveQuizScoreMock).toHaveBeenCalledOnce();
		const persisted = saveQuizScoreMock.mock.calls[0][0] as QuizScore;
		expect(persisted.quizRef).toBe('mod-01-pre');
		expect(persisted.score).toBe(3);
		expect(persisted.maxScore).toBe(5);
		expect(persisted.questionCount).toBe(5);
		expect(typeof persisted.completedAt).toBe('string');

		expect(oncomplete).toHaveBeenCalledOnce();
		expect(oncomplete).toHaveBeenCalledWith(persisted);
	});

	it('fires onquizcomplete only when score / maxScore >= passThreshold', async () => {
		saveQuizScoreMock.mockClear();
		capturedProps.current = null;
		const onquizcomplete = vi.fn();
		render(QuizBlock, {
			props: { manifest, quizRef: 'mod-01-pre', passThreshold: 0.6, onquizcomplete }
		});
		const vendorOncomplete = capturedProps.current?.oncomplete as (d: unknown) => Promise<void>;

		await vendorOncomplete({ quizRef: 'r', score: 2, maxScore: 5, questionCount: 5 });
		expect(onquizcomplete).not.toHaveBeenCalled();

		await vendorOncomplete({ quizRef: 'r', score: 4, maxScore: 5, questionCount: 5 });
		expect(onquizcomplete).toHaveBeenCalledOnce();
	});

	it('fires onquizcomplete on zero-question quizzes (avoids div-by-zero gate)', async () => {
		saveQuizScoreMock.mockClear();
		capturedProps.current = null;
		const onquizcomplete = vi.fn();
		render(QuizBlock, {
			props: { manifest, quizRef: 'mod-01-empty', passThreshold: 0.5, onquizcomplete }
		});
		const vendorOncomplete = capturedProps.current?.oncomplete as (d: unknown) => Promise<void>;
		await vendorOncomplete({ quizRef: 'mod-01-empty', score: 0, maxScore: 0, questionCount: 0 });
		expect(onquizcomplete).toHaveBeenCalledOnce();
	});
});
