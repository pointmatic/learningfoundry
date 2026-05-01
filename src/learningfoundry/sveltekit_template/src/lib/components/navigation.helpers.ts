// Copyright 2026 Pointmatic — SPDX-License-Identifier: Apache-2.0
/**
 * Pure resolver for the Next/Finish and Previous button actions.
 *
 * Extracted so the routing decision can be unit-tested without mounting
 * `Navigation.svelte` and stubbing all of its store dependencies. The
 * component just calls these helpers and dispatches the resulting `goto`
 * call to `$app/navigation`.
 */
import type { NavPosition } from '$lib/stores/curriculum.js';

export type NavAction = { kind: 'noop' } | { kind: 'goto'; url: string };

/** Resolve the action for the Next/Finish button click. */
export function resolveGoNext(
	disabled: boolean,
	next: NavPosition | null
): NavAction {
	if (disabled) return { kind: 'noop' };
	if (next) return { kind: 'goto', url: `/${next.moduleId}/${next.lessonId}` };
	return { kind: 'goto', url: '/' };
}

/** Resolve the action for the Previous button click. */
export function resolveGoPrev(prev: NavPosition | null): NavAction {
	if (!prev) return { kind: 'noop' };
	return { kind: 'goto', url: `/${prev.moduleId}/${prev.lessonId}` };
}

/** URL path for an in-app lesson link. */
export function lessonHref(moduleId: string, lessonId: string): string {
	return `/${moduleId}/${lessonId}`;
}
