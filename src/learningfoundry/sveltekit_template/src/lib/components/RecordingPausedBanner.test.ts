// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Story I.bb — banner mount coverage. Verifies the layout-level recovery
// banner renders only when `dbInit` is in the `wasm-missing` state, and
// stays hidden for `pending` / `ready`. The dbInit store is mocked via a
// real svelte/store writable so the component re-renders on transitions
// the way it would in the layout.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('$lib/stores/db-init.js', async () => {
	const { writable } = await import('svelte/store');
	return { dbInit: writable('pending') };
});

describe('RecordingPausedBanner (Story I.bb)', () => {
	let RecordingPausedBanner: typeof import('./RecordingPausedBanner.svelte').default;
	let dbInit: import('svelte/store').Writable<
		'pending' | 'ready' | 'wasm-missing' | 'failed'
	>;

	beforeEach(async () => {
		const dbInitModule = await import('$lib/stores/db-init.js');
		dbInit = dbInitModule.dbInit as typeof dbInit;
		dbInit.set('pending');
		RecordingPausedBanner = (await import('./RecordingPausedBanner.svelte')).default;
	});

	afterEach(() => {
		vi.clearAllMocks();
	});

	it('does not render when dbInit is pending', async () => {
		const { render } = await import('@testing-library/svelte');
		const { container } = render(RecordingPausedBanner);
		expect(container.querySelector('[data-testid="recording-paused-banner"]')).toBeNull();
	});

	it('does not render when dbInit is ready (working wasm — layout mount with healthy DB)', async () => {
		const { render } = await import('@testing-library/svelte');
		dbInit.set('ready');
		const { container } = render(RecordingPausedBanner);
		expect(container.querySelector('[data-testid="recording-paused-banner"]')).toBeNull();
	});

	it('renders banner with refresh CTA when dbInit is wasm-missing (404 wasm fetch — layout mount with broken asset)', async () => {
		const { render } = await import('@testing-library/svelte');
		dbInit.set('wasm-missing');
		const { container } = render(RecordingPausedBanner);

		const banner = container.querySelector('[data-testid="recording-paused-banner"]');
		expect(banner).not.toBeNull();
		expect(banner?.textContent).toContain('Progress recording is paused');

		const button = container.querySelector('button');
		expect(button).not.toBeNull();
		expect(button?.textContent?.trim()).toBe('Refresh');
	});

	it('reactively appears when dbInit transitions pending → wasm-missing', async () => {
		const { render } = await import('@testing-library/svelte');
		const { container } = render(RecordingPausedBanner);
		expect(container.querySelector('[data-testid="recording-paused-banner"]')).toBeNull();

		dbInit.set('wasm-missing');
		// Let Svelte 5's reactive flush run.
		await Promise.resolve();
		await Promise.resolve();

		expect(container.querySelector('[data-testid="recording-paused-banner"]')).not.toBeNull();
	});
});
