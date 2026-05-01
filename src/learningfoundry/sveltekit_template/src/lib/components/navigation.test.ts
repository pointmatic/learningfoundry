// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { describe, expect, it } from 'vitest';
import { lessonHref, resolveGoNext, resolveGoPrev } from './navigation.helpers.js';

describe('resolveGoNext (Next/Finish button)', () => {
	it('routes to /{module}/{lesson} when there is a next lesson', () => {
		const action = resolveGoNext(false, { moduleId: 'mod-01', lessonId: 'lesson-02' });
		expect(action).toEqual({ kind: 'goto', url: '/mod-01/lesson-02' });
	});

	it('routes to / when next is null (Finish on last lesson)', () => {
		const action = resolveGoNext(false, null);
		expect(action).toEqual({ kind: 'goto', url: '/' });
	});

	it('disabled state is a no-op even with a next lesson', () => {
		const action = resolveGoNext(true, { moduleId: 'mod-01', lessonId: 'lesson-02' });
		expect(action).toEqual({ kind: 'noop' });
	});

	it('disabled state is a no-op when next is null', () => {
		const action = resolveGoNext(true, null);
		expect(action).toEqual({ kind: 'noop' });
	});
});

describe('resolveGoPrev (Previous button)', () => {
	it('routes to /{module}/{lesson} when there is a previous lesson', () => {
		const action = resolveGoPrev({ moduleId: 'mod-01', lessonId: 'lesson-01' });
		expect(action).toEqual({ kind: 'goto', url: '/mod-01/lesson-01' });
	});

	it('no-op when prev is null (first lesson)', () => {
		expect(resolveGoPrev(null)).toEqual({ kind: 'noop' });
	});
});

describe('lessonHref', () => {
	it('formats /{module}/{lesson}', () => {
		expect(lessonHref('mod-01', 'lesson-01')).toBe('/mod-01/lesson-01');
	});
});
