// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/// <reference types="vitest" />
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	// Vitest-only: resolve `svelte` to its browser export so component
	// `mount(...)` works in jsdom. Without this, Svelte 5 throws
	// `lifecycle_function_unavailable: mount(...) is not available on the
	// server`. Guarded by `process.env.VITEST` so production
	// `vite build` is unaffected (browser conditions can mis-bundle
	// SSR-only paths). Story I.q / FR-P15-Q3.
	resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined,
	test: {
		environment: 'jsdom',
		include: ['src/**/*.{test,spec}.{js,ts}'],
		globals: false,
		// Component-mount tests pay a one-time vite-transform cost (~4 s)
		// the first time a file dynamic-imports a Svelte component whose
		// graph pulls in lucide-svelte + marked + katex (LessonView,
		// Navigation, ResetCourseButton). The default 5 s testTimeout
		// leaves no headroom under parallel file load — bump it to 15 s
		// so first-test cold-compile can't tip a green run into a flake.
		testTimeout: 15_000
	}
});
