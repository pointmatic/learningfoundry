// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Story J.u — `computeAssessmentPassed` resolves the `passed: boolean`
// derived contract for module-level assessments. The function is read-time
// to keep the active YAML threshold authoritative; persisting `passed` at
// write time would freeze it to whatever threshold was in effect at
// completion and silently desync if an author retunes the threshold.
import { describe, expect, it } from 'vitest';
import { computeAssessmentPassed } from './assessment-passed.js';

describe('computeAssessmentPassed (Story J.u)', () => {
	it('returns true when passThreshold is null (informational assessment doesn\'t gate)', () => {
		expect(computeAssessmentPassed({ score: 0, maxScore: 5 }, null)).toBe(true);
		expect(computeAssessmentPassed({ score: 5, maxScore: 5 }, null)).toBe(true);
	});

	it('returns true when passThreshold is undefined (same semantics as null)', () => {
		expect(computeAssessmentPassed({ score: 0, maxScore: 5 }, undefined)).toBe(true);
	});

	it('returns true when score / maxScore meets the threshold exactly', () => {
		// 4/5 = 0.8, threshold = 0.8 → passes (>= comparison, not strict >).
		expect(computeAssessmentPassed({ score: 4, maxScore: 5 }, 0.8)).toBe(true);
	});

	it('returns true when score / maxScore exceeds the threshold', () => {
		expect(computeAssessmentPassed({ score: 5, maxScore: 5 }, 0.8)).toBe(true);
	});

	it('returns false when score / maxScore falls below the threshold', () => {
		expect(computeAssessmentPassed({ score: 3, maxScore: 5 }, 0.8)).toBe(false);
	});

	it('returns false when maxScore is 0 and a threshold is set (no evidence of competence)', () => {
		// Without this guard the division would be NaN and `>= threshold`
		// would be false anyway — but the explicit check documents the
		// intent: an author setting a threshold expects a gate, not a
		// vacuous pass from a zero-question assessment.
		expect(computeAssessmentPassed({ score: 0, maxScore: 0 }, 0.5)).toBe(false);
	});

	it('returns true when maxScore is 0 and no threshold is set (informational empty assessment)', () => {
		// Threshold-null branch takes precedence — no gate, no contradiction.
		expect(computeAssessmentPassed({ score: 0, maxScore: 0 }, null)).toBe(true);
	});

	it('returns true for a 0.0 threshold even at score=0 (zero is a valid trivial threshold)', () => {
		expect(computeAssessmentPassed({ score: 0, maxScore: 5 }, 0.0)).toBe(true);
	});
});
