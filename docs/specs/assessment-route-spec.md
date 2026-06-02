# LearningFoundry spec: render module-level assessments as routes

Status: **proposed** (consumer repo blocked on this for end-to-end demo)
Target package: `learningfoundry` SvelteKit template (no Python changes)
Discovered against: learningfoundry v0.74.0, quizazz v1.4.0

## Problem

Module-level `assessments[]` entries appear in `LessonList.svelte`'s sidebar
as static `<li>` chips with no `onclick` handler and no `<a>` link. Clicking
does nothing; whatever lesson is currently loaded stays visible. The
interactive `<AssessmentBlock>` component (`$lib/components/AssessmentBlock.svelte`)
exists and works correctly — it's just never reached from a module-level
assessment position.

Observed against a curriculum where Module 1 declares pre + post
assessments via Story J.e's unified `assessments[]` shape. Sidebar renders
`◆ Pre Assessment` and `◆ Post Assessment 70%`. Clicking is a no-op.

## Root cause

Story J.e's schema + resolver work landed but the SvelteKit template wasn't
extended to consume the new positions. Data flows through correctly — every
assessment compiles into `dist/static/curriculum.json` with full quizazz
manifest — but the route layer is missing.

Concretely:

- No route file at `sveltekit_template/src/routes/[module]/assessment/...`
- `LessonList.svelte` assessment branch (search for `data-testid="assessment-row"`)
  outputs a plain `<li>` chip with no button, no link
- `progressRepo` has `markLessonComplete` but no `markAssessmentComplete`
- `locking.ts` already plumbs `assessments[]` through `interleaveModuleFlow`
  for sidebar ordering but doesn't gate progression on assessment completion

The `<AssessmentBlock>` → `<QuizBlock>` chain is invoked today only when a
**lesson content block** has `type: assessment`. Module-level assessments
have nowhere to render.

## Proposed design

### Route

New file: `sveltekit_template/src/routes/[module]/assessment/[index]/+page.svelte`

URL shape: `/{moduleId}/assessment/{index}` where `index` is the zero-based
position in the module's `assessments[]` array.

Rationale for index over role:

- `AssessmentDefinition` has no schema-level `id` field today.
- `role` is an open string the curriculum author defines; nothing in the schema
  prevents two assessments per module sharing a role (e.g. two `practice`
  entries). Index is the only field guaranteed unique and stable for the
  lifetime of the YAML.
- If we later add an optional `id` field to `AssessmentDefinition`, the route
  becomes `[module]/assessment/[id]/` and index URLs can 404 or redirect.

Page structure parallels `[module]/[lesson]/+page.svelte`:

```svelte
<script lang="ts">
  import { page } from '$app/stores';
  import { curriculum } from '$lib/stores/curriculum';
  import AssessmentBlock from '$lib/components/AssessmentBlock.svelte';
  import { progressRepo } from '$lib/stores/progress';
  import type { AssessmentScore } from '$lib/types';

  let moduleId = $derived($page.params.module);
  let index = $derived(Number($page.params.index));
  let module = $derived($curriculum?.modules.find((m) => m.id === moduleId));
  let assessment = $derived(module?.assessments[index]);

  async function handleComplete(score: AssessmentScore) {
    await progressRepo.markAssessmentComplete(moduleId, index, score);
  }
</script>

{#if assessment}
  <article class="mx-auto max-w-3xl space-y-8 py-6">
    <header>
      <h1 class="text-2xl font-bold text-gray-900">
        {capitalizeRole(assessment.role)} Assessment
      </h1>
    </header>
    <AssessmentBlock
      assessmentRef={assessment.ref}
      manifest={assessment.manifest}
      onassessmentcomplete={handleComplete}
    />
  </article>
{:else}
  <p>Assessment not found.</p>
{/if}
```

### Sidebar nav

`LessonList.svelte` assessment branch — replace the static `<li>` with a
clickable button matching the lesson branch's idioms:

```svelte
{:else}
  {@const assessment = item.assessment}
  {@const threshold = formatPassThreshold(assessment.pass_threshold)}
  {@const isActive =
    $currentPosition?.moduleId === moduleId &&
    $currentPosition?.assessmentIndex === i}
  {@const locked = lockedAssessments.has(i)}
  <li>
    <button
      onclick={() => handleAssessmentClick(i)}
      class="flex w-full items-center gap-2 rounded px-3 py-1.5 text-left text-sm transition-colors
        {locked
          ? 'cursor-not-allowed text-gray-300'
          : isActive
            ? 'bg-amber-100 font-medium text-amber-800'
            : 'text-gray-700 hover:bg-gray-100'}"
      aria-disabled={locked}
      data-testid="assessment-row"
      data-role={assessment.role}
    >
      <span class="shrink-0 text-xs text-amber-600">◆</span>
      <span class="truncate font-medium">{capitalizeRole(assessment.role)} Assessment</span>
      {#if threshold}
        <span class="ml-auto shrink-0 text-[11px] text-gray-400" data-testid="assessment-threshold">
          {threshold}
        </span>
      {/if}
    </button>
  </li>
{/if}
```

The amber active-state palette intentionally differs from the blue used for
lessons — visually distinguishes "assessment in progress" from "lesson in
progress" at a glance.

### Progress store

Extend `progressRepo` (`$lib/stores/progress.ts`):

```ts
export interface AssessmentScore {
  raw: number;          // 0.0 - 1.0
  passed: boolean;      // raw >= pass_threshold (or true if no threshold)
  completedAt: string;  // ISO timestamp
}

export const progressRepo = {
  // ...existing methods...
  async markAssessmentComplete(
    moduleId: string,
    index: number,
    score: AssessmentScore,
  ): Promise<void> { /* persist + invalidate */ },
  async getAssessmentScore(
    moduleId: string,
    index: number,
  ): Promise<AssessmentScore | null> { /* read */ },
};
```

The `$progressStore` value extends to include
`assessmentScores: Map<string, AssessmentScore>` keyed by `${moduleId}:${index}`.

### Locking integration

`locking.ts` should treat an assessment with `pass_threshold` as a gate:
items appearing after it in `interleaveModuleFlow` are locked until the
assessment is complete AND `score.passed === true`. Assessments without a
threshold are informational and don't gate.

Pre-assessments (`position: before_lessons`) are a soft gate by convention —
see "One sharp edge" below.

### Tests to add or extend

- **New**: `routes/[module]/assessment/[index]/page.test.ts`. Mirror
  `[lesson]/page.test.ts`. Mock `@pointmatic/quizazz`, assert
  `<AssessmentBlock>` receives correct `assessmentRef`, assert completion
  callback fires `markAssessmentComplete` with the right score shape.
- **Extend**: `LessonList.test.ts`. The existing "assessment row renders"
  test asserts a chip; flip it to assert a button with the correct click
  target and href-equivalent navigation behavior.
- **Extend**: `locking.test.ts`. New cases:
  - Post-assessment with `pass_threshold: 0.7` and no recorded score → next
    module locked.
  - Post-assessment with recorded score below threshold → next module locked.
  - Post-assessment with recorded score above threshold → next module unlocked.
  - Pre-assessment with `pass_threshold: 0.7` and no recorded score → lesson 1
    is **not** locked (soft-gate convention).

## Files touched

```
NEW    sveltekit_template/src/routes/[module]/assessment/[index]/+page.svelte
NEW    sveltekit_template/src/routes/[module]/assessment/[index]/page.test.ts
EDIT   sveltekit_template/src/lib/components/LessonList.svelte
EDIT   sveltekit_template/src/lib/components/LessonList.test.ts
EDIT   sveltekit_template/src/lib/stores/progress.ts
EDIT   sveltekit_template/src/lib/stores/progress.test.ts
EDIT   sveltekit_template/src/lib/utils/locking.ts
EDIT   sveltekit_template/src/lib/utils/locking.test.ts
EDIT   sveltekit_template/src/lib/types/index.ts   (add AssessmentScore if missing)
```

No Python changes. No schema changes.

## One sharp edge

The `pre` role with `pass_threshold` is semantically weird — you can't lock a
learner out of the first lesson they haven't seen yet. Two interpretations:

1. **Soft gate** (recommended): pre-assessment with threshold runs but
   doesn't block. Score is recorded; failing it just means "you have
   prerequisite gaps to be aware of." Authors signal this by using
   `role: pre` + `position: before_lessons`.
2. **Hard gate**: pre-assessment with threshold blocks lesson 1 until passed.
   Authors who want this should instead use `role: practice` +
   `position: { before_lesson: m01-l01-... }` — same gating effect, more
   honest naming, and locking logic doesn't need a special case.

Recommend implementing #1 only (i.e. the `pre` role is treated as soft
regardless of `pass_threshold`). Document the workaround for #2.

## Out of scope (defer to follow-up issues)

- Schema-level `id` field on `AssessmentDefinition` for pretty URLs.
- Re-attempt UI / score history visualization (quizazz handles re-attempts
  internally; we just persist the latest score).
- Cross-module assessment dependencies (e.g. M3 post gates M5 pre).
- Skippable pre-assessments with explicit "skip" UI affordance.

## Bonus: why this generalizes well

Once the assessment route lands, the SvelteKit template covers every Story
J.e position: `before_lessons`, `after_lessons`, `{before_lesson: X}`,
`{after_lesson: X}`. The interleaved-flow logic in `locking.ts` already
handles ordering correctly; we're just adding the missing destination.

This also unblocks Story J.f (assessments rendered at their resolved
positions) end-to-end — sidebar interleave was the visible half, route +
gating is the functional half.
