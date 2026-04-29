# learningfoundry

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org)
[![CI](https://github.com/pointmatic/learningfoundry/actions/workflows/ci.yml/badge.svg)](https://github.com/pointmatic/learningfoundry/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/pointmatic/learningfoundry/branch/main/graph/badge.svg)](https://codecov.io/gh/pointmatic/learningfoundry)

A curriculum engine that turns a YAML curriculum definition into a deployable SvelteKit learning application — with interactive assessments, executable notebooks, and data visualizations — in a single pipeline.

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Reference](#cli-reference)
- [Curriculum YAML Format](#curriculum-yaml-format)
- [Images and assets](#images-and-assets)
- [Configuration File](#configuration-file)
- [Development Setup](#development-setup)

---

## Overview

`learningfoundry` takes a single `curriculum.yml` file and generates a fully self-contained [SvelteKit](https://kit.svelte.dev/) learning application. The generated app supports:

- **Text** — Markdown content rendered in the browser
- **Video** — YouTube embeds
- **Quiz** — Interactive assessments via [quizazz](https://github.com/pointmatic/quizazz) (optional)
- **Exercise** — Executable notebooks via nbfoundry (stub provided)
- **Visualization** — D3-based charts via d3foundry (stub provided)

Learner progress is persisted locally in SQLite (via sql.js) — no backend required.

---

## Installation

```bash
pip install learningfoundry
```

**With optional quizazz support:**

```bash
pip install "learningfoundry[quizazz]"
```

**Requirements:**

- Python 3.12+
- [pnpm](https://pnpm.io) (for `preview` command and generated app development)
- Node.js 18+ (for the generated SvelteKit app)

---

## Quick Start

1. **Create a curriculum file** (see [Curriculum YAML Format](#curriculum-yaml-format)):

   ```bash
   cat > curriculum.yml << 'EOF'
   version: "1.0.0"
   curriculum:
     title: "My Course"
     description: "A short description."
     modules:
       - id: mod-01
         title: "Module One"
         lessons:
           - id: lesson-01
             title: "Getting Started"
             content_blocks:
               - type: text
                 ref: content/lesson-01.md
               - type: video
                 url: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
   EOF
   ```

2. **Validate** the curriculum:

   ```bash
   learningfoundry validate
   # OK — curriculum is valid.
   ```

3. **Build and preview** locally:

   ```bash
   learningfoundry preview
   # Preview server started at http://localhost:5173
   ```

   `learningfoundry preview` is the canonical "see your work" command — it builds the SvelteKit project, installs Node dependencies on first run (and again whenever they change), and starts a Vite dev server. On subsequent runs it skips the install step automatically.

   `learningfoundry build` alone is also available if you want to generate the SvelteKit project without serving it (e.g. to inspect output, deploy a static export via `cd dist && pnpm build`, or wire into your own toolchain).

---

## CLI Reference

### `learningfoundry build`

Parse → resolve → generate a SvelteKit project.

```
Usage: learningfoundry build [OPTIONS]

Options:
  -c, --config PATH       Path to the curriculum YAML file.  [default: curriculum.yml]
  --log-level LEVEL       Logging verbosity.  [default: INFO]
                          Choices: DEBUG, INFO, WARNING, ERROR
  -o, --output PATH       Output directory for the generated SvelteKit project.
                          [default: dist]
  --base-dir PATH         Base directory for content refs.
                          (default: curriculum file's parent directory)
  --help                  Show this message and exit.
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Curriculum validation error |
| 2 | Content resolution error (missing file, bad URL, etc.) |
| 3 | SvelteKit generation error |
| 4 | Configuration file error |

---

### `learningfoundry validate`

Validate a curriculum YAML without generating any output.

```
Usage: learningfoundry validate [OPTIONS]

Options:
  -c, --config PATH       Path to the curriculum YAML file.  [default: curriculum.yml]
  --log-level LEVEL       Logging verbosity.  [default: INFO]
  --base-dir PATH         Base directory for resolving content refs.
  --help                  Show this message and exit.
```

Prints `OK — curriculum is valid.` on success, or a list of errors and exits with code 1.

---

### `learningfoundry preview`

Build then launch a local Vite dev server.

```
Usage: learningfoundry preview [OPTIONS]

Options:
  -c, --config PATH       Path to the curriculum YAML file.  [default: curriculum.yml]
  --log-level LEVEL       Logging verbosity.  [default: INFO]
  -o, --output PATH       Output directory for the generated SvelteKit project.
                          [default: dist]
  --base-dir PATH         Base directory for content refs.
  --port INTEGER          Port for the local dev server.  [default: 5173]
  --help                  Show this message and exit.
```

Runs `learningfoundry build`, then `pnpm install` (skipped when every declared dependency is already present in `node_modules/`), then `pnpm run dev` in the generated project directory. Requires `pnpm` on `PATH`.

This serves the SvelteKit project from source via Vite's dev server; it does **not** serve the static `pnpm build` output in `dist/build/`. For static deploys, use `cd dist && pnpm build` and host the resulting `dist/build/` directory on any static host.

---

## Curriculum YAML Format

```yaml
version: "1.0.0"

curriculum:
  title: "Course Title"           # required
  description: "Course overview." # optional

  modules:
    - id: mod-01                  # required, kebab-case
      title: "Module One"         # required
      description: "..."          # optional

      # Optional pre/post assessments (requires quizazz-builder)
      pre_assessment:
        source: quizazz
        ref: assessments/mod-01-pre.yml

      post_assessment:
        source: quizazz
        ref: assessments/mod-01-post.yml

      lessons:
        - id: lesson-01           # required, kebab-case; unique within module
          title: "Lesson One"     # required

          content_blocks:

            # Text block — Markdown file
            - type: text
              ref: content/mod-01/lesson-01.md

            # Video block — YouTube URL only
            - type: video
              url: "https://www.youtube.com/watch?v=XXXXXXXXXXX"

            # Quiz block — requires learningfoundry[quizazz]
            - type: quiz
              source: quizazz
              ref: assessments/mod-01-quiz.yml

            # Exercise block — requires nbfoundry (stub included)
            - type: exercise
              source: nbfoundry
              ref: exercises/mod-01-exercise.yml

            # Visualization block — requires d3foundry (stub included)
            - type: visualization
              source: d3foundry
              ref: visualizations/mod-01-vis.yml
```

**Rules:**

- Module and lesson `id` values must be unique within their scope, and match the pattern `[a-z0-9][a-z0-9-]*`.
- Every curriculum must have at least one module; every module at least one lesson.
- All `ref` paths are resolved relative to `--base-dir` (default: directory containing the curriculum YAML).
- Only YouTube URLs are accepted for `video` blocks (`youtube.com/watch?v=` or `youtu.be/`).

---

## Images and assets

Lesson markdown can embed images directly. Place the image file alongside the markdown that uses it and reference it with a relative path:

```
content/
└── mod-01/
    ├── lesson-01.md
    ├── diagram.png
    └── figures/
        └── architecture.svg
```

```markdown
# Lesson One

![Architecture diagram](figures/architecture.svg "Hover title")

Here is a smaller inline diagram:

<img src="diagram.png" alt="Diagram" />
```

**How it works:**

- Relative URLs (`diagram.png`, `figures/architecture.svg`) are resolved against the markdown file's own directory. `learningfoundry build` copies each unique image into `dist/static/content/<sha256[:12]>/<basename>` and rewrites the markdown URL to the absolute path `/content/<sha256[:12]>/<basename>` so it resolves at every nested route in the generated app.
- Both the markdown form (`![alt](path)`, `![alt](path "title")`) and the HTML form (`<img src="path">`) are recognised.
- Absolute URLs (`https://`, `http://`, protocol-relative `//...`, root-absolute `/...`) and `data:` URIs pass through unchanged — useful for CDN-hosted assets you don't want copied into the build.
- Image references inside fenced code blocks (` ``` ` or `~~~`) are left as literal text, so code samples that *demonstrate* image syntax aren't silently rewritten.
- The same image referenced from N lessons is copied exactly once (deduped by content hash).
- A missing image fails the build with the lesson location and the expected on-disk path in the error message.

For production deployment to a CDN, just run `cd dist && pnpm build` — the `static/content/` tree gets bundled into the static export under `build/content/`, so deploying `build/` to any static host (Cloudflare Pages, Netlify, S3+CloudFront, …) serves the images at the same URLs the markdown references.

---

## Configuration File

An optional config file can set defaults for logging. The CLI always takes precedence.

**Default location:** `~/.config/learningfoundry/config.yml`

```yaml
logging:
  level: INFO      # DEBUG | INFO | WARNING | ERROR
  output: stdout   # stdout | stderr
```

Pass a custom config location with `-c / --config`.

---

## Development Setup

### Prerequisites

- Python 3.12+
- [pyve](https://github.com/pointmatic/pyve) (virtual env manager used in this project)
- pnpm 9+ and Node.js 18+

### Setup

```bash
git clone https://github.com/pointmatic/learningfoundry.git
cd learningfoundry

# Create the Python environment and install the package in editable mode
pyve init
pip install -e .

# Create the test runner environment and install dev dependencies
pyve testenv --init
pyve testenv --install -r requirements-dev.txt
```

### Running Tests

```bash
# Fast unit + integration tests (~2 min)
pyve test

# End-to-end SvelteKit smoke tests (requires pnpm, ~15 s extra)
pyve test tests/test_smoke_sveltekit.py -v
```

### Linting and Type Checking

```bash
pyve testenv run ruff check .
pyve testenv run mypy src/
```

### Project Structure

```
learningfoundry/
├── src/learningfoundry/
│   ├── cli.py              # Click CLI entry point
│   ├── config.py           # Configuration loading
│   ├── exceptions.py       # Exception hierarchy
│   ├── generator.py        # SvelteKit project generator
│   ├── integrations/       # Quiz / exercise / visualization providers
│   ├── logging_config.py   # Logging setup
│   ├── parser.py           # YAML parser + version dispatch
│   ├── pipeline.py         # run_build / run_validate / run_preview
│   ├── resolver.py         # Content reference resolver
│   └── schema_v1.py        # Pydantic v1 curriculum schema
├── sveltekit_template/     # SvelteKit app template (copied on build)
├── tests/                  # pytest test suite
├── requirements-dev.txt    # Dev dependencies
└── pyproject.toml          # Build config, ruff, mypy, pytest settings
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
