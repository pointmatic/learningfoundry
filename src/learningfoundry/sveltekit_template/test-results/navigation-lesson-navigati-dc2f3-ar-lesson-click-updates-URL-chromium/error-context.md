# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: navigation.spec.ts >> lesson navigation routing >> sidebar lesson click updates URL
- Location: e2e/navigation.spec.ts:10:2

# Error details

```
Test timeout of 30000ms exceeded.
```

```
Error: locator.click: Test timeout of 30000ms exceeded.
Call log:
  - waiting for locator('aside nav button').first()

```

# Page snapshot

```yaml
- generic [ref=e3]:
  - complementary [ref=e4]:
    - link "LearningFoundry" [ref=e5] [cursor=pointer]:
      - /url: /
    - paragraph [ref=e6]: Loading…
    - button "Reset course progress" [disabled] [ref=e8]:
      - img [ref=e9]
      - text: Reset course progress
  - main [ref=e10]:
    - paragraph [ref=e12]: Loading curriculum…
```

# Test source

```ts
  1  | // Copyright 2026 Pointmatic
  2  | // SPDX-License-Identifier: Apache-2.0
  3  | //
  4  | // FR-P9 regression coverage: in-app navigation must update the URL.
  5  | // Before v0.46.0 the sidebar / Next button updated `currentPosition` but
  6  | // not the route, so `LessonView` was never re-mounted on lesson change.
  7  | import { expect, test } from '@playwright/test';
  8  | 
  9  | test.describe('lesson navigation routing', () => {
  10 | 	test('sidebar lesson click updates URL', async ({ page }) => {
  11 | 		await page.goto('/');
  12 | 		// Open the first module by clicking its header in the sidebar.
  13 | 		const firstModuleHeader = page.locator('aside nav button').first();
> 14 | 		await firstModuleHeader.click();
     |                           ^ Error: locator.click: Test timeout of 30000ms exceeded.
  15 | 
  16 | 		// Click the first lesson row in the now-expanded module.
  17 | 		const firstLessonRow = page.locator('aside nav ul ul button').first();
  18 | 		await firstLessonRow.click();
  19 | 
  20 | 		// URL must reflect the click; before v0.46.0 it stayed at "/".
  21 | 		await expect(page).toHaveURL(/\/[^/]+\/[^/]+$/);
  22 | 	});
  23 | 
  24 | 	test('dashboard "Start module" deep-links into a lesson', async ({ page }) => {
  25 | 		await page.goto('/');
  26 | 		const startBtn = page.getByRole('button', { name: /start module|continue/i }).first();
  27 | 		await startBtn.click();
  28 | 		await expect(page).toHaveURL(/\/[^/]+\/[^/]+$/);
  29 | 	});
  30 | });
  31 | 
```