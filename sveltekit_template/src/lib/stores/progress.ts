// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * Reactive progress store.
 *
 * Replaces the one-shot `$effect` progress fetch in `+layout.svelte`.
 * Lesson completions call `invalidateProgress` so the sidebar updates
 * immediately without a page reload.
 */
import { writable } from 'svelte/store';
import type { Curriculum, ModuleProgress } from '$lib/types/index.js';
import { getModuleProgress } from '$lib/db/index.js';

export const progressStore = writable<Record<string, ModuleProgress>>({});

export async function invalidateProgress(curriculum: Curriculum | null): Promise<void> {
	if (!curriculum) return;
	const entries = await Promise.all(
		curriculum.modules.map(async (m) => {
			const mp = await getModuleProgress(
				m.id,
				m.lessons.map((l) => l.id)
			);
			return [m.id, mp] as const;
		})
	);
	progressStore.set(Object.fromEntries(entries));
}
