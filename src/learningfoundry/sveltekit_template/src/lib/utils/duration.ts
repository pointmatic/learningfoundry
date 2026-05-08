// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0

/**
 * Format an aggregate `duration_minutes` value (Story J.c) for display
 * on the curriculum index. Returns `null` when the input is `null` /
 * `undefined` / `0` / negative so the caller can branch on a single
 * value instead of mixing null-checks with empty strings.
 *
 * Convention: under an hour → `≈ Xm`; an hour or more → `≈ Xh` with
 * the remainder appended as ` Ym` only when non-zero. Examples:
 *   45  → `≈ 45m`
 *   60  → `≈ 1h`
 *   75  → `≈ 1h 15m`
 *   120 → `≈ 2h`
 */
export function formatDurationEstimate(minutes: number | null | undefined): string | null {
	if (minutes == null || minutes <= 0) return null;
	if (minutes < 60) return `≈ ${minutes}m`;
	const hours = Math.floor(minutes / 60);
	const rem = minutes % 60;
	return rem === 0 ? `≈ ${hours}h` : `≈ ${hours}h ${rem}m`;
}
