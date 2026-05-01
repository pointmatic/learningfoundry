// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
//
// Anti-regression coverage for the v0.48.0 sentinel zero-area trap.
//
// In v0.48.0 the end-of-block sentinel was rendered as
//   <div bind:this={sentinelEl} aria-hidden="true" data-textblock-end></div>
// — zero area, which makes `IntersectionObserver` compute
// `intersectionRatio = 0` against the configured `0.1` threshold and
// the `isIntersecting` branch never fires in real browsers. Net effect:
// no `textcomplete`, no `markLessonComplete`, no progress at all.
//
// We tried mounting `TextBlock` with `@testing-library/svelte` and with
// Svelte's server `render` API to capture the observed element directly,
// but Svelte 5 + vitest + the SvelteKit vite plugin compile components
// in client mode by default and the server renderer trips on
// `get_first_child`. Reworking that compilation path is its own
// infrastructure story; until then we lock the regression at the
// source-template layer with a string assertion. This is brittle to
// formatting but cheap, fast, and catches the specific class of bug.
// The e2e harness (`progress.spec.ts`, `text-block-bottom.spec.ts`)
// is the canonical cross-check that the markup actually behaves.
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const HERE = dirname(fileURLToPath(import.meta.url));
const TEXT_BLOCK_SRC = readFileSync(resolve(HERE, 'TextBlock.svelte'), 'utf-8');

describe('TextBlock end-of-block sentinel (source invariants)', () => {
	it('renders a sentinel with `data-textblock-end`', () => {
		expect(TEXT_BLOCK_SRC).toMatch(/data-textblock-end/);
	});

	it('sentinel carries a non-zero inline height (anti-regression)', () => {
		// The sentinel must have an explicit non-zero `height` so the
		// observer's `intersectionRatio` is meaningful against `threshold: 0.1`.
		const sentinelTag = TEXT_BLOCK_SRC.match(/<div[^>]*data-textblock-end[^>]*>/)?.[0];
		expect(sentinelTag, 'sentinel <div> not found in TextBlock.svelte').toBeDefined();
		expect(sentinelTag).toMatch(/style="[^"]*height:\s*1px/);
	});

	it('observes the sentinel, not the wrapper', () => {
		// `observer.observe(...)` must target `sentinelEl`, not any prior
		// wrapper binding. If a future refactor reintroduces a wrapper
		// binding and observes that, this assertion catches it before the
		// regression reaches the e2e layer.
		expect(TEXT_BLOCK_SRC).toMatch(/observer\.observe\(sentinelEl\)/);
	});
});
