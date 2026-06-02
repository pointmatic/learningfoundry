// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	// Keep sql.js out of vite's deps pre-bundle **in test mode only**.
	// The package's `sql-wasm.wasm` is a binary asset; vitest 4.x's
	// optimizer parses it as JS and chokes on the `\0asm` magic header
	// ("Cannot find package 'a'"). The per-test
	// `test.deps.optimizer.web.exclude` alone is ineffective under
	// vitest 4.x, so this top-level exclude is required for vitest.
	//
	// **In dev/prod the exclude must NOT apply.** It disables Vite's
	// CJS→ESM dep pre-bundling for sql.js, which is the layer that
	// converts the package's UMD `dist/sql-wasm-browser.js` into a
	// browser-loadable ESM module with a synthetic `default` export.
	// Without that conversion, `(await import('sql.js')).default` is
	// `undefined` in the dev-server browser for sql.js@1.13+, and
	// `Database.getDb()` rejects with `CjsEsmInteropError` (see
	// `src/lib/db/database.ts` and
	// `docs/specs/bug-sql-js-browser-esm-spec.md`). Story J.w originally
	// added the exclude unscoped; the present scoping was added during
	// the bug-sql-js-browser-esm-spec debug cycle.
	optimizeDeps: process.env.VITEST ? { exclude: ['sql.js'] } : undefined,
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
		testTimeout: 15_000,
		// Skip vite's deps-optimizer for sql.js in tests. The browser
		// build runs a wasm fetch as a module-level side effect, which
		// the optimizer triggers when pre-bundling — and the fetch fails
		// in jsdom because `/sql-wasm.wasm` has no base URL. Excluding
		// keeps sql.js untouched until a test imports it (where vi.mock
		// can cleanly replace it).
		deps: { optimizer: { web: { exclude: ['sql.js'] } } }
	}
});
