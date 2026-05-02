// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Story I.u — real-DOM mount coverage for `ModuleList.svelte`. The
// helper-style cases in `module-list.test.ts` already cover the click /
// auto-expand decision logic; this file pins the markup that the helpers
// can't see — the Lucide Lock icon for locked modules, the locked-click
// suppression on the rendered button, and the active-module highlight
// classes the dashboard sidebar uses.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '@testing-library/svelte';
import type { Module, ModuleProgress } from '$lib/types/index.js';

const { currentPositionValue } = vi.hoisted(() => ({
	currentPositionValue: { value: null as { moduleId: string; lessonId: string } | null }
}));

vi.mock('$lib/stores/curriculum.js', () => {
	const noop = () => {};
	return {
		currentPosition: {
			subscribe: (fn: (v: { moduleId: string; lessonId: string } | null) => void) => {
				fn(currentPositionValue.value);
				return noop;
			},
			set: vi.fn()
		}
	};
});
vi.mock('$app/navigation', () => ({ goto: vi.fn() }));

function makeModule(id: string, title: string, lessonCount = 2): Module {
	return {
		id,
		title,
		description: '',
		pre_assessment: null,
		post_assessment: null,
		lessons: Array.from({ length: lessonCount }, (_, i) => ({
			id: `lesson-${String(i + 1).padStart(2, '0')}`,
			title: `L${i + 1}`,
			content_blocks: []
		}))
	};
}

function emptyProgress(mod: Module): ModuleProgress {
	const lessons: Record<string, ModuleProgress['lessons'][string]> = {};
	for (const l of mod.lessons) {
		lessons[l.id] = {
			moduleId: mod.id,
			lessonId: l.id,
			status: 'not_started',
			completedAt: null
		};
	}
	return {
		moduleId: mod.id,
		status: 'not_started',
		lessons,
		preAssessment: null,
		postAssessment: null
	};
}

describe('ModuleList mount — locked vs unlocked modules', () => {
	let ModuleList: typeof import('./ModuleList.svelte').default;

	beforeEach(async () => {
		currentPositionValue.value = null;
		ModuleList = (await import('./ModuleList.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('locked module renders a Lucide Lock SVG; unlocked module does not; clicking locked header does not expand its LessonList', async () => {
		const m1 = makeModule('mod-01', 'First');
		const m2 = makeModule('mod-02', 'Second');
		const progress = {
			'mod-01': emptyProgress(m1),
			'mod-02': emptyProgress(m2)
		};
		const lockedModules = new Set(['mod-02']);

		const { container } = render(ModuleList, {
			props: { modules: [m1, m2], progress, lockedModules }
		});

		const items = container.querySelectorAll('nav > ul > li');
		expect(items.length).toBe(2);

		const unlockedItem = items[0] as HTMLElement;
		const lockedItem = items[1] as HTMLElement;

		// Lucide Lock icon ships as an SVG with the `lucide-lock` class.
		expect(unlockedItem.querySelector('svg.lucide-lock')).toBeNull();
		expect(lockedItem.querySelector('svg.lucide-lock')).not.toBeNull();

		// `aria-disabled` on the rendered header button.
		const lockedBtn = lockedItem.querySelector('button') as HTMLButtonElement;
		expect(lockedBtn.getAttribute('aria-disabled')).toBe('true');
		lockedBtn.click();
		// Locked header click is a no-op — no `<LessonList>` panel ever
		// appears below the locked module.
		expect(lockedItem.querySelector('ul')).toBeNull();

		// Unlocked header click expands and reveals the inner LessonList <ul>.
		const unlockedBtn = unlockedItem.querySelector('button') as HTMLButtonElement;
		expect(unlockedItem.querySelector('ul')).toBeNull();
		unlockedBtn.click();
		// Re-query — the LessonList renders on next reactive tick, but
		// `<button.click()>` triggers Svelte's synchronous update path
		// since the state is in a $state rune.
		const { flushSync } = await import('svelte');
		flushSync();
		expect(unlockedItem.querySelector('ul')).not.toBeNull();
	});

	it('active module carries border-l-blue-500 bg-blue-50; inactive sibling does not', async () => {
		currentPositionValue.value = { moduleId: 'mod-01', lessonId: 'lesson-01' };

		const m1 = makeModule('mod-01', 'Active');
		const m2 = makeModule('mod-02', 'Inactive');
		const progress = {
			'mod-01': emptyProgress(m1),
			'mod-02': emptyProgress(m2)
		};

		const { container } = render(ModuleList, {
			props: { modules: [m1, m2], progress }
		});

		const items = container.querySelectorAll('nav > ul > li');
		const activeItem = items[0] as HTMLElement;
		const inactiveItem = items[1] as HTMLElement;

		expect(activeItem.className).toContain('border-l-blue-500');
		expect(activeItem.className).toContain('bg-blue-50');
		expect(inactiveItem.className).not.toContain('border-l-blue-500');
		expect(inactiveItem.className).not.toContain('bg-blue-50');
	});
});
