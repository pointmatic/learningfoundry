# concept.md — Quizazz

## Problem Space

### Problem Statement

Educators, course authors, and self-directed learners need a way to build targeted multiple-choice assessments around specific subject matter — and to use those assessments to gauge comprehension before, during, and after a learning experience. Existing quiz and flashcard tools (Anki, Quizlet, Kahoot, etc.) are SaaS products that lock content behind accounts, impose their own UX decisions, and cannot be embedded into custom learning pipelines. When assessments are a critical gating mechanism — determining whether a learner can skip a module or needs to revisit material — the assessment tool must be fully owned, offline-capable, and tightly integrated with the rest of the curriculum infrastructure.

The problem is compounded when questions are generated at scale by LLMs: generated answers tend to exhibit predictable length patterns that leak the correct answer's identity, and there is no built-in mechanism to enforce answer-length uniformity or to rate the quality of generated questions after delivery.

### Why the Problem Persists

- **SaaS lock-in**: The most capable quiz tools require accounts, subscriptions, and internet connectivity. Content lives on someone else's servers.
- **No integration path**: Off-the-shelf tools do not expose APIs or data formats suitable for embedding into a custom learning framework with pre/post-assessment gating logic.
- **LLM generation gaps**: LLMs can generate questions quickly, but the output needs structured validation, answer-length normalization, and quality feedback loops — none of which exist in general-purpose quiz platforms.
- **One-size-fits-all UX**: Existing tools impose navigation flows, scoring models, and review experiences that cannot be customized to match a specific pedagogical approach.

### Pain Points

- **Platform dependence**: Useful quiz tools require an external service, an account, and ongoing connectivity — making them unsuitable for offline, local-first, or self-hosted workflows.
- **Content lock-in**: Questions authored in a proprietary platform cannot easily be version-controlled, diffed, reviewed in pull requests, or fed into automated pipelines.
- **No assessment gating**: Existing tools treat quizzes as standalone activities with no mechanism to drive skip/retry logic in a broader curriculum.
- **Poor LLM integration**: There is no structured pipeline to validate, normalize, and quality-check LLM-generated questions before they reach learners.
- **Answer-length bias**: LLM-generated answers often have a predictable length signature (correct answers tend to be longer or shorter than distractors), making it possible to guess the answer without reading the content.
- **No quality feedback loop**: After a quiz is delivered, there is no systematic way to collect signals (complaint rate, star ratings) that feed back into question improvement.
- **Rigid UX**: Scoring models, navigation flows, and review experiences are fixed by the platform and cannot be tailored to a specific learning design.

### Target Users

- **Course authors and instructors** building structured curricula (e.g., graduate-level deep learning courses) who need pre- and post-module assessments that integrate with skip/retry gating logic.
- **Self-directed learners** building personal question banks on topics they are studying, quizzing themselves repeatedly, and tracking mastery over time.
- **Developers and technical educators** who want questions in version-controlled plain-text files (YAML), compilable to static assets, deployable anywhere, and generatable by LLMs.

### Value Criteria

- **Learner comprehension signal**: Pre/post-assessment scores reliably indicate whether a learner has sufficient understanding to skip a module or needs further study.
- **Question quality**: Low complaint rate on individual questions; high star ratings on overall quiz quality after completion.
- **Author efficiency**: Time from source material to deployable quiz is minimized through LLM-assisted generation with automated validation.
- **Integration fitness**: The tool slots cleanly into a larger learning framework as the assessment component, without requiring adapters or workarounds.

---

## Solution Space

### One-Liner

Quizazz delivers a fully-owned, offline-capable quiz engine with LLM-powered question generation, structured validation, and weighted-adaptive delivery — purpose-built to embed into custom learning pipelines.

### Solution Statement

Quizazz is a monorepo containing a Python-based question builder and a SvelteKit quiz delivery app. Course authors write questions in YAML (or generate them via LLM), and the builder validates, normalizes, and compiles them into self-contained static quiz packages. Each quiz runs entirely in the browser with no server dependency — scores persist locally in IndexedDB-backed SQLite, and a weighted-random algorithm prioritizes questions the learner struggles with most. The navigation tree, tag filtering, and topic scoping let authors structure large question banks into meaningful assessment units. Because every artifact is a plain file (YAML in, JSON out, static HTML/JS deployed), the system integrates naturally with git workflows, CI pipelines, and broader curriculum frameworks where pre/post-assessment scores drive module gating.

### Goals

- **Reliable comprehension signal**: Weighted-adaptive question selection surfaces weak areas, making assessment scores a meaningful input to skip/retry decisions in a curriculum.
- **High question quality at scale**: The builder validates every question against structural rules (minimum answers, category coverage, non-empty explanations), and future answer-length normalization will eliminate a common LLM generation artifact. Post-quiz quality ratings close the feedback loop.
- **Full ownership and portability**: No accounts, no SaaS, no network dependency at runtime. Questions live in YAML under version control; compiled quizzes deploy as static assets to any host.
- **Seamless curriculum integration**: The tool is designed as the assessment component of a larger learning framework, with clear data boundaries (YAML in, scores out) that other systems can consume.

### Scope

**In scope:**

- Multi-quiz YAML authoring with file-level metadata, subtopics, tags, and four-category answer classification
- Python builder: validation, compilation to JSON manifest, CLI for single-quiz and batch modes
- SvelteKit SPA: navigation tree with mastery scores, configurable quiz sessions, weighted-random selection, deferred scoring, mid-quiz review, per-question timer, per-quiz database isolation
- Upload of externally compiled quiz packages at runtime
- LLM-assisted question generation (builder pipeline — future phase, architecturally planned)
- Answer-length normalization to prevent guess-by-length (future phase)
- Post-quiz quality rating for feedback loop (future phase)

**Out of scope:**

- User accounts or authentication
- Server-side persistence or APIs
- Real-time multiplayer or collaborative features
- Question editing in the browser UI
- Mobile native wrappers
- Score decay / spaced repetition (deferred)
- Session history / longitudinal analytics (deferred)

### Constraints

- **Browser-only runtime**: The quiz app must run as a static SPA with no server component. All persistence is client-side (IndexedDB + sql.js WASM).
- **Offline-capable**: After initial page load, no network requests are required.
- **Plain-text authoring**: Questions must remain in human-readable, version-controllable YAML — no binary or proprietary formats.
- **Monorepo boundary**: The builder (Python) and app (SvelteKit/Node) are separate workspaces with a shared `data/` directory as the only coupling point.
- **Static deployment**: Compiled quizzes must be deployable to any static hosting provider (GitHub Pages, Netlify, S3, etc.) with zero server configuration.

---

## Pain Point → Solution Mapping

**Platform dependence**:
  - Quizazz runs entirely in the browser as a static SPA — no account, no subscription, no server required.
  - Compiled quiz packages can be served from any static host or opened locally from disk.

**Content lock-in**:
  - Questions are authored in YAML and stored in git alongside the rest of the project.
  - The compiled JSON manifest is a plain, documented format — portable and inspectable.

**No assessment gating**:
  - Pre/post-assessment scores are stored in a structured SQLite database with per-question granularity.
  - The data model is designed so an external learning framework can query scores to drive module skip/retry logic.

**Poor LLM integration**:
  - The builder validates every generated question against Pydantic models enforcing structural rules (category coverage, minimum answers, non-empty fields).
  - The CLI fails fast with clear error messages, making it safe to pipe LLM output directly into the build step.

**Answer-length bias**:
  - Future answer-length normalization will require short and long variants for every answer, with the quiz randomly selecting a uniform length profile (all short, all long, or random) per question — eliminating the length signal.

**No quality feedback loop**:
  - Post-quiz star ratings and per-question complaint signals (planned) will provide structured quality data that can feed back into question revision — whether manual or LLM-assisted.

**Rigid UX**:
  - Every aspect of the quiz experience is configurable: topic/subtopic scoping, tag filtering, question count, answer count, scoring weights, and navigation flow.
  - The codebase is fully owned and modifiable — no vendor constraints on UX decisions.
