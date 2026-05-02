// Copyright 2026 Pointmatic
// SPDX-License-Identifier: Apache-2.0
/**
 * Playwright global teardown — companion to `global-setup.ts`.
 *
 * Removes `static/curriculum.json` so the template's `static/` directory
 * stays free of test fixtures for `pnpm dev`.
 */
import { existsSync, unlinkSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export default function globalTeardown(): void {
	const here = dirname(fileURLToPath(import.meta.url));
	const target = resolve(here, '../static/curriculum.json');
	if (existsSync(target)) unlinkSync(target);
}
