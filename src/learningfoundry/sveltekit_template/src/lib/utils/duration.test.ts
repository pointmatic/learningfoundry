// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import { formatDurationEstimate } from './duration.js';

describe('formatDurationEstimate (Story J.c)', () => {
	it('returns null for null / undefined / 0 / negative — caller hides on null', () => {
		expect(formatDurationEstimate(null)).toBeNull();
		expect(formatDurationEstimate(undefined)).toBeNull();
		expect(formatDurationEstimate(0)).toBeNull();
		expect(formatDurationEstimate(-5)).toBeNull();
	});

	it('formats sub-hour totals as `≈ Xm`', () => {
		expect(formatDurationEstimate(1)).toBe('≈ 1m');
		expect(formatDurationEstimate(45)).toBe('≈ 45m');
		expect(formatDurationEstimate(59)).toBe('≈ 59m');
	});

	it('formats whole-hour totals as `≈ Xh` (no `0m` suffix)', () => {
		expect(formatDurationEstimate(60)).toBe('≈ 1h');
		expect(formatDurationEstimate(120)).toBe('≈ 2h');
		expect(formatDurationEstimate(180)).toBe('≈ 3h');
	});

	it('formats mixed totals as `≈ Xh Ym`', () => {
		expect(formatDurationEstimate(75)).toBe('≈ 1h 15m');
		expect(formatDurationEstimate(125)).toBe('≈ 2h 5m');
	});
});
