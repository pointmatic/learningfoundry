# learningfoundry-pushback-recommendations.md

LearningFoundry is generalizing its embed surface to `<AssessmentBlock>` so it
can host any assessment provider (Quizazz, an LLM interview, an interactive
game, etc.). The provider-side glue for Quizazz still uses `quizazz` /
`<QuizBlock>` / `quizRef` / `quizName` — those are **vendor surface** and stay.
But several spots in LearningFoundry's canonical
[`dependency-spec.md`](learningfoundry-dependency-spec.md) still describe
**LearningFoundry-domain** artifacts (the cross-boundary manifest noun, LF's own
DB columns, the generic completion-event interface, the LF-side mount point)
using vendor (`quiz...`) terminology. Those reads as if Quizazz were the only
provider LF will ever host.

This document is **Quizazz's recommendation to LearningFoundry** for what to
rename on the LF side of the boundary, so that LF's canonical spec generalizes
cleanly to non-Quizazz providers while leaving Quizazz's vendor surface
untouched. Nothing in this document implies a Quizazz-side change. The
guiding principle — codified in `project-essentials.md` — is
**"vendor terminology stops at the vendor boundary."** Concretely:

| Side of the boundary | Domain | Terminology |
|----------------------|--------|-------------|
| Quizazz (this repo)  | vendor | `quiz`, `quizName`, `quizRef`, `<QuizBlock>`, `quizazz-{quizName}` IndexedDB, `source: quizazz` selector |
| LearningFoundry      | host   | `assessment`, `assessmentName`, `assessmentRef`, `<AssessmentBlock>`, `assessment_scores` table |

The single translation surface on the Python side is already
`QuizazzProvider.compile_assessment()` (RR-1a). The recommendation below adds
the symmetric translation surface on the TypeScript side: `<AssessmentBlock>`
(new RR-1b).

---

## Quizazz-owned vendor surface — audit result

The audit explicitly confirms none of the following need to change. They are
the vendor surface and remain spelled `quiz...` on Quizazz's side:

- **`<QuizBlock>` component name** — Quizazz's component, kept as-is.
  `<AssessmentBlock>` is LearningFoundry's generic mount point; it delegates
  to `<QuizBlock>` when `source: quizazz`.
- **`quizRef` prop on `<QuizBlock>`** — vendor-surface prop, kept. LF's
  `<AssessmentBlock>` accepts `assessmentRef` and passes it through as
  `quizRef` to `<QuizBlock>`.
- **`quizName` key in the manifest emitted by Quizazz** — wire format, kept.
  `QuizazzProvider.compile_assessment()` already relabels it to
  `assessmentName` (RR-1a) before serialization.
- **`quizazz-{quizName}` IndexedDB naming** — vendor-internal storage; LF
  does not read these databases.
- **`source: quizazz` curriculum-YAML selector** — vendor selector
  identifying *which* provider; necessarily literal.

---

## Recommended changes to LearningFoundry's `dependency-spec.md`

The line numbers below refer to the version of LearningFoundry's
`docs/specs/quizazz/dependency-spec.md` mirrored at
[`learningfoundry-dependency-spec.md`](learningfoundry-dependency-spec.md) in
this repo at the time of writing (1.3.x). LearningFoundry should adjust as
needed when applying upstream.

### 1. BR-1 docstring — "compiled quiz manifest" → "compiled assessment manifest"

[`learningfoundry-dependency-spec.md`](learningfoundry-dependency-spec.md)
lines 39–40 currently read:

> Returns:
>     A dict representing the compiled **quiz** manifest, suitable for JSON
>     serialization and consumption by the quizazz frontend component.

The noun *crossing* the boundary — what LF holds in memory once the provider
returns — is LF-domain. Recommend:

> Returns:
>     A dict representing the compiled **assessment** manifest, suitable for
>     JSON serialization and consumption by the quizazz frontend component.

The Quizazz-side docstring on `compile_assessment` (in
`python/src/quizazz/api.py`) can keep its current language; this rename is for
the LF-canonical interface description, not for the Python implementation.

### 2. Data Flow Summary (runtime block) — show `<AssessmentBlock>` as the LF mount point

Lines 182–184 currently read:

> Runtime (SvelteKit):
>   LessonView renders QuizBlock component with manifest + quizRef

Recommend showing the LF-side mount point and its delegation explicitly:

> Runtime (SvelteKit):
>   LessonView renders `<AssessmentBlock>` with `manifest` + `assessmentRef`
>     → `<AssessmentBlock>` selects the provider implementation based on
>       `manifest.source` (or equivalent); for `source: quizazz` it mounts
>       `<QuizBlock>` and passes `quizRef={assessmentRef}` plus the manifest
>       (already relabeled `quizName` → `assessmentName` by `QuizazzProvider`)

### 3. Data Flow Summary — rename LF's DB columns to drop vendor terminology

Line 187 currently reads:

> learningfoundry writes `{quizRef, score, maxScore}` to its
> `assessment_scores` table

LF's own database columns shouldn't carry vendor terminology — that table will
be written by every provider that LF hosts. Recommend:

> learningfoundry writes `{assessmentRef, score, maxScore}` to its
> `assessment_scores` table

The rewrite from `quizRef` → `assessmentRef` happens in `<AssessmentBlock>`'s
completion handler before persistence (see RR-1b below).

### 4. `AssessmentCompleteEvent` — `quizRef` → `assessmentRef` at the generic level

Lines 113–120 currently read:

```typescript
interface AssessmentCompleteEvent {
  quizRef: string;        // The ref path passed in (vendor prop name preserved)
  score: number;
  maxScore: number;
  questionCount: number;
}
```

The interface is named `AssessmentCompleteEvent` — generic at the LF level —
so the field should also be generic. Quizazz's vendor event (the one
`<QuizBlock>` fires) continues to use `quizRef`; the rewrite to
`assessmentRef` happens in `<AssessmentBlock>`'s `oncomplete` handler before
it re-fires upward. Recommend:

```typescript
interface AssessmentCompleteEvent {
  assessmentRef: string;  // LF-domain; <AssessmentBlock> rewrites quizRef → assessmentRef
  score: number;
  maxScore: number;
  questionCount: number;
}
```

### 5. Add RR-1b: Prop and Event Relabel (parallel to RR-1a)

RR-1a establishes that `QuizazzProvider.compile_assessment()` is the **single
Python-side translation surface** for the manifest's top-level key
(`quizName` → `assessmentName`). The TypeScript side currently has no
equivalent "single translation surface" rule — every consumer is on its own
to keep vendor terminology out of LF-domain code.

Recommend a new section, parallel in spirit to RR-1a, immediately after
RR-1a:

> #### RR-1b: Prop and Event Relabel
>
> `<AssessmentBlock>` is the **single TypeScript-side translation surface**
> between LF-domain props/events and Quizazz's vendor surface. Specifically,
> `<AssessmentBlock>`:
>
> 1. Accepts `assessmentRef: string` from LF and passes it through to
>    `<QuizBlock>` as `quizRef={assessmentRef}`.
> 2. Receives `<QuizBlock>`'s `complete` event whose detail contains
>    `quizRef` and re-fires it upward with `assessmentRef` substituted, so
>    no LF-side consumer ever sees `quizRef`.
> 3. (Future) Provides the same two-step relabel for any additional
>    provider-specific props/events.
>
> Downstream LF code (`LessonView`, the progress dashboard, the
> `assessment_scores` repo) must never reference `quizRef`. If it does, the
> RR-1b translation surface regressed.
>
> This is symmetric to RR-1a, which makes `QuizazzProvider.compile_assessment()`
> the single Python-side translation surface for the manifest-key relabel.

### 6. Generalize package-distribution and versioning sections

The Package Distribution and Versioning sections currently read as if Quizazz
is the only provider LF will ever consume. Once `<AssessmentBlock>` exists
they should be scoped explicitly to "the `quizazz` provider":

- **Package Distribution table** (lines 195–199): retitle to *"Package
  Distribution (quizazz provider)"* or add a leading sentence noting that
  the table describes the `quizazz` provider specifically; the same table
  structure (Python package, SvelteKit component, optional-dep group)
  should be reproducible for any future provider.
- **Versioning and Compatibility** (lines 203–207): rephrase
  *"learningfoundry pins quizazz>=0.1 as an optional dependency"* and
  *"The manifest dict schema is the versioning boundary"* to make explicit
  that these are facts about the `quizazz` provider's contract with LF.
  The general rule — *"every provider's manifest schema is the boundary
  between that provider and LF"* — belongs in a parent section that
  individual provider specs (this one being the first) elaborate on.

These changes leave the substantive content intact; they just reframe it as
provider-specific rather than implicitly universal.

---

## What stays untouched on the Quizazz side

For completeness, listing the items that are **deliberately not** in this
recommendation set:

- The `compile_assessment(yaml_path, base_dir) -> dict` signature.
- The `quizName` key in the dict returned by `compile_assessment()`.
- The `<QuizBlock>` component, its `quizRef` prop, its `complete` /
  `error` callback props and `CustomEvent` channels, and its event-detail
  field name `quizRef`.
- IndexedDB naming `quizazz-{quizName}`.
- The `source: quizazz` selector value in curriculum YAML.

If LearningFoundry applies the recommendations above, the **only** Quizazz-side
follow-up is a one-line `cp` to refresh the local mirror at
[`learningfoundry-dependency-spec.md`](learningfoundry-dependency-spec.md);
no source or test changes.

---

## How this story handles the path-escape constraint

BR-1's last bullet states that Quizazz raises `quizazz.ValidationError` when
`yaml_path` resolves outside `base_dir`. This is already implemented in
[`python/src/quizazz/api.py`](../../python/src/quizazz/api.py) via
`_resolve_under_base()` and covered by
[`python/tests/test_api.py`](../../python/tests/test_api.py)'s
`TestPathEscapeGuard` (dotdot traversal, absolute path outside base, post-
symlink escape, plus a positive case for absolute path inside base). No
addition needed; the audit confirms the contract is met.
