// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { derived, readable, writable } from 'svelte/store';
import type { Curriculum, Lesson, Module } from '$lib/types/index.js';

// ---------------------------------------------------------------------------
// Raw curriculum data — loaded from /static/curriculum.json at startup
// ---------------------------------------------------------------------------

async function loadCurriculum(): Promise<Curriculum> {
	const res = await fetch('/curriculum.json');
	if (!res.ok) {
		throw new Error(`Failed to load curriculum.json: ${res.status} ${res.statusText}`);
	}
	return res.json() as Promise<Curriculum>;
}

// Readable store that fetches curriculum.json once on first subscriber.
export const curriculum = readable<Curriculum | null>(null, (set) => {
	loadCurriculum()
		.then(set)
		.catch((err) => {
			console.error('[learningfoundry] Failed to load curriculum:', err);
		});
});

// ---------------------------------------------------------------------------
// Navigation state
// ---------------------------------------------------------------------------

export interface NavPosition {
	moduleId: string;
	lessonId: string;
}

export const currentPosition = writable<NavPosition | null>(null);

// ---------------------------------------------------------------------------
// Derived helpers
// ---------------------------------------------------------------------------

export const modules = derived(curriculum, ($c) => $c?.modules ?? []);

export const currentModule = derived(
	[curriculum, currentPosition],
	([$c, $pos]): Module | null => {
		if (!$c || !$pos) return null;
		return $c.modules.find((m) => m.id === $pos.moduleId) ?? null;
	}
);

export const currentLesson = derived(
	[currentModule, currentPosition],
	([$mod, $pos]): Lesson | null => {
		if (!$mod || !$pos) return null;
		return $mod.lessons.find((l) => l.id === $pos.lessonId) ?? null;
	}
);

// Flat ordered list of all (moduleId, lessonId) pairs for sequential navigation.
export const lessonSequence = derived(curriculum, ($c): NavPosition[] => {
	if (!$c) return [];
	return $c.modules.flatMap((m: Module) => m.lessons.map((l: Lesson) => ({ moduleId: m.id, lessonId: l.id })));
});

export const currentIndex = derived(
	[lessonSequence, currentPosition],
	([$seq, $pos]): number => {
		if (!$pos) return -1;
		return $seq.findIndex((p) => p.moduleId === $pos.moduleId && p.lessonId === $pos.lessonId);
	}
);

export const previousLesson = derived(
	[lessonSequence, currentIndex],
	([$seq, $idx]): NavPosition | null => ($idx > 0 ? $seq[$idx - 1] : null)
);

export const nextLesson = derived(
	[lessonSequence, currentIndex],
	([$seq, $idx]): NavPosition | null => ($idx >= 0 && $idx < $seq.length - 1 ? $seq[$idx + 1] : null)
);

// ---------------------------------------------------------------------------
// Navigation helpers
// ---------------------------------------------------------------------------

/**
 * **Internal route-sync only — UI code must use `goto` directly.**
 *
 * Sets `currentPosition`. Used by the dynamic lesson route's URL→store
 * `$effect`; do **not** call from sidebars, dashboards, or navigation
 * buttons. UI code should import `goto` from `$app/navigation` and build
 * the path explicitly so SvelteKit's lifecycle (page params, scroll
 * restoration, lesson-route `{#key}` re-mount) fires predictably for
 * every user-initiated navigation.
 */
export function navigateTo(moduleId: string, lessonId: string): void {
	currentPosition.set({ moduleId, lessonId });
}

export function navigateNext(): void {
	currentPosition.update(($pos) => {
		if (!$pos) return $pos;
		let found = false;
		for (const mod of get(modules) as Module[]) {
			for (const lesson of mod.lessons as Lesson[]) {
				if (found) return { moduleId: mod.id, lessonId: lesson.id };
				if (mod.id === $pos.moduleId && lesson.id === $pos.lessonId) found = true;
			}
		}
		return $pos;
	});
}

export function navigatePrev(): void {
	currentPosition.update(($pos) => {
		if (!$pos) return $pos;
		let prev: NavPosition | null = null;
		for (const mod of get(modules) as Module[]) {
			for (const lesson of mod.lessons as Lesson[]) {
				if (mod.id === $pos.moduleId && lesson.id === $pos.lessonId) {
					return prev ?? $pos;
				}
				prev = { moduleId: mod.id, lessonId: lesson.id };
			}
		}
		return $pos;
	});
}

// get() helper for non-reactive reads inside update callbacks
function get<T>(store: { subscribe: (fn: (v: T) => void) => () => void }): T {
	let value!: T;
	const unsub = store.subscribe((v) => (value = v));
	unsub();
	return value;
}
