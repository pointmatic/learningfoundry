// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
import { defineConfig, devices } from '@playwright/test';

const PORT = Number(process.env.PLAYWRIGHT_PORT ?? 4173);

export default defineConfig({
	testDir: './e2e',
	fullyParallel: false,
	reporter: [['list']],
	// Restore the template's `static/` to a clean state after the suite —
	// see `webServer.command` for why we plant `curriculum.json` there.
	globalTeardown: './e2e/global-teardown.ts',
	use: {
		baseURL: `http://localhost:${PORT}`,
		trace: 'retain-on-failure'
	},
	webServer: {
		// Plant the curriculum fixture, build, then preview — all inside
		// one shell so the build happens AFTER the fixture is in place.
		// (Playwright runs `globalSetup` *after* the webServer starts, so
		// using globalSetup for the copy results in `pnpm build` running
		// before the fixture exists — preview then serves a stale build
		// and every test 404s on `/curriculum.json`.)
		command:
			`cp e2e/fixtures/curriculum.json static/curriculum.json && ` +
			`pnpm build && pnpm preview --port ${PORT} --strictPort`,
		port: PORT,
		reuseExistingServer: !process.env.CI,
		timeout: 120_000
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] }
		}
	]
});
