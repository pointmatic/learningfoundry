# stories.md -- learningfoundry (python)

This document breaks the `learningfoundry` project into an ordered sequence of small, independently completable stories grouped into phases. Each story has a checklist of concrete tasks. Stories are organized by phase and reference modules defined in `tech-spec.md`.

Stories with code changes include a version number (e.g., v0.1.0). Stories with only documentation or polish changes omit the version number. The version follows semantic versioning and is bumped per story. Stories are marked with `[Planned]` initially and changed to `[Done]` when completed.

For a high-level concept (why), see `concept.md`. For requirements and behavior (what), see `features.md`. For implementation details (how), see `tech-spec.md`. For project-specific must-know facts, see `project-essentials.md` (`plan_phase` appends new facts per phase).

---

## Phase I: Functional and UX Improvements

---

### Story I.a: v0.37.0 Local Image Support — Co-located Assets and Markdown Rewriting [Done]

learningfoundry has no first-class image support. Authors today have only two options, both bad:
- Use absolute CDN URLs (`![](https://cdn.example.com/foo.png)`) — works at runtime, but couples curriculum content to external infrastructure and breaks for offline / pre-publish iteration.
- Hand-drop files into `sveltekit_template/static/` — wrong layer (the template is the project-wide source of truth, not a per-curriculum asset bag), and `static/` is not in `_PRESERVED_PATHS`, so any drop gets blown away on the next `learningfoundry build`.

The desired UX is **co-location** — authors keep images alongside the markdown files that reference them, the same way they would in any other documentation system:

```
my-curriculum/
  curriculum.yml
  content/
    mod-01/
      lesson-01.md
      lesson-01-figures/
        diagram.png
        screenshot-1.png
```

In `lesson-01.md`:
```markdown
![Architecture overview](lesson-01-figures/diagram.png)
```

The pipeline detects the relative image reference, copies the asset into the generated SvelteKit project at a deterministic location, and rewrites the markdown URL to an absolute path that resolves at any nested route. CDN/absolute URLs (`https://...`, `http://...`, protocol-relative `//...`, and any URL starting with `/`) pass through unchanged.

**Resolution semantics:**
- Image paths are resolved relative to the markdown file's directory (not `base_dir`, not the curriculum file's location). `![](figures/foo.png)` in `content/mod-01/lesson-01.md` resolves to `content/mod-01/figures/foo.png` on disk.
- Missing image files raise `ContentResolutionError` with the lesson location in the message (consistent with the existing pattern for missing markdown text refs).
- Each unique source image is copied exactly once even if referenced by multiple lessons — the destination path is content-keyed (`static/content/<sha256[:12]>/<basename>`) so duplicates dedupe automatically.
- The rewritten markdown URL is `/content/<sha256[:12]>/<basename>` — absolute, so it works at `/`, `/mod-01/`, `/mod-01/lesson-01/`, etc.
- `static/content/` is added to `_PRESERVED_PATHS` so re-builds don't re-copy unchanged assets.

**Out of scope (deferred to a follow-up story):**
- Dedicated `type: image` content block (caption, sizing, lazy-load attributes, first-class alt text). Markdown `![alt](path)` covers 80% of cases; a dedicated block is its own design problem.
- Image optimisation / responsive `srcset` generation. The pipeline copies bytes verbatim for v0.37.0.
- Video / audio / other binary asset types. Same pattern would apply but each is its own story.

**Tasks:**

- [x] Create `src/learningfoundry/asset_resolver.py` — pure function `resolve_markdown_assets(markdown: str, markdown_path: Path) -> tuple[str, list[Asset]]`:
  - [x] Walk the markdown text for `![alt](path)` and the rarer `<img src="path">` HTML form
  - [x] Skip absolute URLs (`http://`, `https://`, `//`, leading `/`, `data:` URIs, mailto/tel)
  - [x] Resolve relative paths against `markdown_path.parent`; raise `ContentResolutionError` for missing files
  - [x] Compute `sha256` of source bytes, take first 12 hex chars
  - [x] Return rewritten markdown + list of `Asset(source: Path, dest_relative: str)` records where `dest_relative` is `content/<hash12>/<basename>`
- [x] Update `src/learningfoundry/resolver.py`:
  - [x] `ResolvedTextBlock` gains `assets: list[Asset]` field (default `[]`)
  - [x] `_resolve_text_block()` calls `resolve_markdown_assets()` and stores both the rewritten markdown and the asset list
- [x] Update `src/learningfoundry/generator.py`:
  - [x] After `_atomic_copy()`, walk the resolved curriculum collecting all `Asset` records and copy each `source` to `output_dir / "static" / asset.dest_relative` (skip if dest already exists with matching size — the hash in the path makes this safe)
  - [x] Add `"static/content"` to `_PRESERVED_PATHS` so subsequent rebuilds preserve already-copied assets
- [x] `src/learningfoundry/exceptions.py` — confirm `ContentResolutionError` is the right type for missing images (it is — same family as missing markdown text refs)
- [x] `tests/test_asset_resolver.py` (new):
  - [x] Relative image ref → resolved path + rewritten URL
  - [x] Absolute URL passthrough (`https://`, `http://`, `//`, leading `/`)
  - [x] `data:` URI passthrough
  - [x] Missing image raises `ContentResolutionError` with markdown path in message
  - [x] Multiple references to same image → deduped (one Asset, two rewrites pointing at same dest)
  - [x] HTML `<img src="...">` form alongside markdown `![]()` form
  - [x] Path traversal attempt (`../../../etc/passwd`) — either rejected or resolves to a path that's normalised within the curriculum tree (decide based on what's safest)
- [x] `tests/test_resolver.py` — new cases: text block with images populates `ResolvedTextBlock.assets`; missing image raises `ContentResolutionError` with lesson location
- [x] `tests/test_generator.py` — new cases: assets land in `output_dir/static/content/<hash>/<basename>`; `static/content/` is in `_PRESERVED_PATHS`; rebuild does not re-copy unchanged assets
- [x] `tests/test_smoke_sveltekit.py` — extend the all-block-types fixture with a co-located image; assert it appears in the smoke-built site's `static/content/` directory
- [x] `docs/specs/features.md` updates:
  - [x] **Inputs → Markdown content files** (~line 114): document the image co-location convention. Authors place image files alongside the markdown that references them; relative paths in `![alt](path)` and `<img src="path">` are resolved against the markdown file's directory. Absolute URLs (`https://`, `http://`, `//`, leading `/`, `data:`) pass through unchanged.
  - [x] **Outputs → Static SvelteKit application** (~line 138): mention the generated `static/content/<hash12>/<basename>` directory containing copied image assets, served at `/content/...`.
  - [x] **FR-2: Content Resolution** (~line 176): extend with an "Image asset resolution" sub-requirement — the resolver scans every text block's markdown for image refs, hashes each unique source file, records `(source, dest_relative)` pairs on `ResolvedTextBlock.assets`, and rewrites the markdown to use absolute `/content/<hash12>/<basename>` URLs. Missing image files raise `ContentResolutionError` with the lesson location.
- [x] `docs/specs/tech-spec.md` updates:
  - [x] **Package Structure** (~line 88): add `src/learningfoundry/asset_resolver.py` to the module list with a one-line description.
  - [x] **Key Component Design** — add a new `### asset_resolver.py — Markdown Image Asset Resolution` subsection between `resolver.py` (~line 385) and `integrations/protocols.py` (~line 442). Document: public API (`resolve_markdown_assets()`, `Asset` dataclass), the regex strategy for `![alt](path)` and `<img src="...">`, fenced-code-block skipping, absolute-URL passthrough rules, hash-based dedup convention (`sha256[:12]`), and `ContentResolutionError` semantics.
  - [x] **`resolver.py` — Content Resolution** (~line 385): update the section to note that text-block resolution now includes calling `resolve_markdown_assets()`, and `ResolvedTextBlock` carries the resolved markdown plus an `assets: list[Asset]` field.
  - [x] **`generator.py` — SvelteKit Project Generation** (~line 613): document the new asset-copy step (after `_atomic_copy()`, walk the resolved curriculum collecting `Asset` records and copy each into `static/content/<hash12>/<basename>`); document the extension of `_PRESERVED_PATHS` to include `static/content`.
  - [x] **Data Models → Resolved Curriculum** (~line 710): add `assets: list[Asset]` to the `ResolvedTextBlock` description and define the `Asset` dataclass shape (`source: Path`, `dest_relative: str`).
- [x] `README.md` — new "Images and assets" section under Curriculum YAML Format documenting the co-location pattern, the `/content/<hash>/<file>` rewrite, and that absolute URLs pass through. Mention that for production CDN deploys, authors can simply use absolute URLs in markdown — no learningfoundry change needed.
- [x] Bump version to v0.37.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`
- [x] Update `CHANGELOG.md` with v0.37.0 entry under Added (image asset pipeline) and Changed (`_PRESERVED_PATHS` extended)
- [x] Verify: `pyve test` passes, `pyve test -m smoke` passes, `ruff` and `mypy` clean

---

### Story I.b: v0.38.0 Reset Main Scroll on Lesson Navigation [Done]

The lesson layout puts a fixed-height shell (`h-screen overflow-hidden`) with two inner scroll containers — a sidebar `<aside>` and a content `<main>` (`+layout.svelte`). SvelteKit's built-in scroll restoration only manages `window.scrollY`, so navigating from the bottom of one lesson (where the Next button lives) to the next lesson leaves `<main>` scrolled to the bottom — the new page renders, but the user lands at the footer of the lesson and has to manually scroll up to see the lesson title. Same root cause when clicking a lesson in the sidebar from the middle of the previous lesson.

**Fix:** register an `afterNavigate` hook in `+layout.svelte` that resets the `<main>` element's `scrollTop` to `0` on every forward (non-`popstate`) navigation. Skipping `popstate` preserves the browser's natural back/forward scroll-restoration UX so a user pressing Back lands where they were before clicking through.

**Out of scope (deferred to a follow-up story):**
- Per-lesson scroll memory (revisiting a partially-read lesson lands where you left off). Needs a per-lesson scroll-position store keyed on `(moduleId, lessonId)`.
- Smooth-scroll animation on reset. The instant default is fine for forward nav.

**Tasks:**

- [x] `src/learningfoundry/sveltekit_template/src/routes/+layout.svelte`:
  - [x] `bind:this={mainEl}` on the existing `<main>` element
  - [x] Import `afterNavigate` from `$app/navigation`
  - [x] Register `afterNavigate(({ type }) => { if (mainEl && type !== 'popstate') mainEl.scrollTop = 0; })`
- [x] `src/learningfoundry/sveltekit_template/src/routes/layout.test.ts` (new): vitest unit test that verifies the `afterNavigate` callback resets `scrollTop` to `0` for forward navigations and leaves it alone for `popstate`. Mock `$app/navigation`'s `afterNavigate` to capture the registered callback, then exercise it with both navigation types against a stub element.
- [x] Bump version to v0.38.0 in `pyproject.toml` and `src/learningfoundry/__init__.py`.
- [x] `CHANGELOG.md` — v0.38.0 entry under "Fixed".
- [x] Verify: `pyve test` passes, `pyve test tests/test_smoke_sveltekit.py` passes (covers `pnpm test` → vitest in the generated template), `ruff` and `mypy` clean.

---

## Future

<!--
This section captures items intentionally deferred from the active phases above:
- Stories not yet planned in detail
- Phases beyond the current scope
- Project-level out-of-scope items
The `archive_stories` mode preserves this section verbatim when archiving stories.md.
-->

- **lmentry integration** — Direct LLM invocation for content generation (currently done externally)
- **nbfoundry real integration** — Replace `NbfoundryStub` with Marimo notebook generation when nbfoundry is published
- **d3foundry real integration** — Replace `D3foundryStub` with D3.js visualization generation when d3foundry is published
- **Pre/post assessment gating** — Module access control based on quiz scores
- **Progress export/import** — Sync or backup learner progress
- **Spaced repetition / adaptive sequencing**
- **Multi-curriculum dashboard**
