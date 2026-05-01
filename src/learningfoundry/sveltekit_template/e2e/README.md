# Playwright e2e tests

These tests run against the static `pnpm preview` server (see
`playwright.config.ts`) and exercise the navigation/completion lifecycle
that vitest cannot reach because vitest mocks `$app/navigation` and
`IntersectionObserver`.

## Fixture curriculum

`fixtures/curriculum.json` is a hand-authored, self-contained curriculum
matching the runtime shape that `learningfoundry build` emits. The
specs install a `page.route('**/curriculum.json', …)` interception in
`beforeEach` so the app loads the fixture instead of whatever
`curriculum.json` happens to live in `static/` from the smoke build —
that decoupling keeps these tests stable against unrelated curriculum
edits.

The fixture contains three lessons:

- `mod-01/lesson-01` — short text block; sentinel fits in the
  viewport on first render and `textcomplete` fires after 1 s.
- `mod-01/lesson-02` — tall text block (`200vh` spacer) where the
  sentinel only intersects after `<main>` scrolls to the bottom;
  completion must not fire before scroll and must fire within 2 s of
  it.
- `mod-02/lesson-01` — trailing short lesson, gives navigation
  sequences a destination.

## Regenerating the fixture

The fixture was hand-authored to keep it tightly scoped to the
behaviours the specs care about. If you ever want to derive it from
YAML so it shares the validation path with author-facing curricula,
write a tiny `learningfoundry build` driver into `e2e/fixtures/yaml/`
and copy the resulting `curriculum.json` over this file. Until that
need shows up, hand-editing this file is the path of least surprise.

## Running locally

```bash
pnpm exec playwright install chromium   # one-time
pnpm e2e
```

The smoke test (`tests/test_smoke_sveltekit.py::test_pnpm_e2e_passes`)
runs the same suite after `pnpm build` and skips gracefully when the
Chromium browser is not installed.
