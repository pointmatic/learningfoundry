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

type Pos = { moduleId: string; lessonId: string } | null;

const { currentPositionValue, subscribers } = vi.hoisted(() => ({
	currentPositionValue: { value: null as Pos },
	subscribers: [] as Array<(v: Pos) => void>
}));

vi.mock('$lib/stores/curriculum.js', async () => {
	const { writable } = await import('svelte/store');
	return {
		currentPosition: {
			subscribe: (fn: (v: Pos) => void) => {
				subscribers.push(fn);
				fn(currentPositionValue.value);
				return () => {
					const i = subscribers.indexOf(fn);
					if (i >= 0) subscribers.splice(i, 1);
				};
			},
			set: vi.fn((v: Pos) => {
				currentPositionValue.value = v;
				for (const fn of subscribers) fn(v);
			})
		},
		// Real writable — `ModuleList` subscribes via `$expandedModuleId`
		// and `clearActivePosition` writes via `.set(null)`. Story I.aa.1
		// state-lift validates by exercising those code paths exactly.
		expandedModuleId: writable<string | null>(null)
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
		subscribers.length = 0;
		const { expandedModuleId } = await import('$lib/stores/curriculum.js');
		expandedModuleId.set(null);
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

	// Story I.aa.2 — visual regression guard. The lock icon + aria-disabled
	// is covered above; this pins the rest of the locked-module styling
	// (cursor-not-allowed on the button, gray-400 text) so a future
	// refactor of the Tailwind classes can't silently regress the visual
	// indicator that tells learners a module is gated.
	it('locked module button carries cursor-not-allowed and gray-400 styling', () => {
		const m1 = makeModule('mod-01', 'First');
		const m2 = makeModule('mod-02', 'Locked');
		const progress = {
			'mod-01': emptyProgress(m1),
			'mod-02': emptyProgress(m2)
		};
		const { container } = render(ModuleList, {
			props: { modules: [m1, m2], progress, lockedModules: new Set(['mod-02']) }
		});
		const lockedBtn = (
			container.querySelectorAll('nav > ul > li')[1] as HTMLElement
		).querySelector('button') as HTMLButtonElement;
		expect(lockedBtn.className).toContain('cursor-not-allowed');
		expect(lockedBtn.className).toContain('text-gray-400');
	});

	// Story I.aa.1 — orthogonal coverage to Story I.y. The previous fix
	// handled "active lesson present, click course title": the position
	// transitioned from non-null → null and the auto-expand $effect's
	// reset branch fired. This test pins the case where the learner
	// manually expanded a module from the dashboard (currentPosition
	// stays null the whole time) and *then* clicks the course title:
	// `clearActivePosition` is responsible for collapsing the module
	// directly via `expandedModuleId.set(null)`, because Svelte 5's
	// `$store` deref filters a same-value `set(null)` and the $effect
	// would not re-run.
	it('clearActivePosition collapses a manually-expanded module even when currentPosition was already null (course-title click on dashboard)', async () => {
		const m1 = makeModule('mod-01', 'First');
		const progress = { 'mod-01': emptyProgress(m1) };

		const { container } = render(ModuleList, {
			props: { modules: [m1], progress }
		});

		const item = container.querySelector('nav > ul > li') as HTMLElement;
		const btn = item.querySelector('button') as HTMLButtonElement;

		// Manually expand by clicking the module header.
		btn.click();
		const { flushSync } = await import('svelte');
		flushSync();
		expect(item.querySelector('ul')).not.toBeNull();

		// Simulate the course-title link click — the layout handler that
		// runs is `clearActivePosition()`.
		const { clearActivePosition } = await import(
			'../../routes/layout.helpers.js'
		);
		clearActivePosition();
		flushSync();

		expect(item.querySelector('ul')).toBeNull();
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
