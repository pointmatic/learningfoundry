# features.md — LMentry (Python)

This document defines **what** LMentry does — its requirements, inputs, outputs, and behavior — without specifying how it is implemented. It is the source of truth for project scope. For architecture and module design, see [`tech_spec.md`](tech_spec.md). For the phased implementation plan, see [`stories.md`](stories.md).

---

## Project Goal

LMentry is a Python 3.11+ CLI tool and library, published to [PyPI](https://pypi.org/), that wraps [LiteLLM](https://github.com/BerriAI/litellm) to provide a batteries-included, developer-friendly interface to 100+ LLM APIs. For newcomers, it means going from zero to a working LLM call in under two minutes — guided setup, secure key storage, and an interactive chat to explore models immediately. For developers building AI-enabled features, it provides a programmatic API with adaptive throttling, fallback chains, cost tracking, response caching, and arena-style model comparison — the infrastructure needed to evaluate, integrate, and operate LLMs in production code without reinventing the plumbing every time.

### CLI Tools — Explore & Evaluate

No-code tools for getting started, exploring models, and making informed decisions.

1. **Guided provider setup ("hold-my-hand" mode)** — An interactive CLI wizard that walks the developer through creating an account, obtaining an API key, and storing it securely. For each provider, the wizard:
   - Displays step-by-step instructions and the signup/key-creation URL.
   - Optionally opens the URL in the default browser.
   - Accepts the pasted key, validates it against the provider's API, and reports which models the key unlocks.
   - Saves the key to a secure `.env` file with restrictive permissions (`chmod 600`) and ensures `.env` is listed in `.gitignore`.
   - **Ollama setup** — the wizard also offers to set up [Ollama](https://ollama.com/) for local model support. It detects whether Ollama is already installed, guides the developer through installation if not (platform-appropriate instructions or direct download), verifies the Ollama service is running, and pulls a recommended small model (e.g., Phi-3 or Qwen2.5) so local features like use-case classification and prompt pre-screening are ready immediately — no paid API key required.

2. **Interactive chat (REPL)** — A built-in CLI chat mode that lets the developer converse with any configured model without writing code. Supports:
   - Single-model chat (`lmentry chat gpt-4o`).
   - Multi-model chat for side-by-side comparison (`lmentry chat gpt-4o claude-3.5-sonnet`).
   - Streaming responses.
   - Conversation history within a session.

3. **Arena-style model comparison** — Run the same prompt (or prompt suite) against N models and produce a structured comparison report including:
   - Response text (side-by-side or sequential).
   - Latency (time to first token, total time).
   - Token usage (prompt tokens, completion tokens).
   - Estimated cost per response.
   - Optional quality scoring via a judge model.

4. **Model discovery and recommendation** — Given a configured provider key, list all available models with metadata (context window, pricing, capabilities). Beyond listing, provide opinionated recommendations backed by real benchmark data:
   - `lmentry models` — list all available models with pricing and capabilities.
   - `lmentry recommend <use-case>` — suggest the best models for a task category (e.g., `code-generation`, `summarization`, `classification`, `vision`, `cheap-and-fast`, `highest-quality`).
   - **Benchmark-driven** — recommendations are informed by public benchmark data (SWE-bench, HumanEval, MMLU, MT-Bench, etc.). A bundled catalog maps models to benchmark scores by category. The catalog can be refreshed independently (`lmentry models --update-catalog`).
   - Recommendations factor in: benchmark scores, cost, latency, context window, and which keys the developer has configured.
   - Example: `lmentry recommend code-generation` → "For code generation, we recommend **claude-3.5-sonnet** (best quality, SWE-bench 49%) or **gpt-4o-mini** (best value, SWE-bench 33%). You have keys for both."
   - **Optional local model integration** — if Ollama is set up (see item 1), use a local model for use-case classification, prompt pre-screening, and sanity checks to avoid burning paid tokens.

5. **Token and cost estimation** — Before and after each call, display:
   - Estimated token count for the prompt.
   - Estimated cost based on the provider's published pricing.
   - Running session totals.

### Library API — Build & Operate

Programmatic features for integrating LLMs into applications with production-grade reliability.

6. **Adaptive throttling** — Integrate [gentlify](https://pypi.org/project/gentlify/) to provide automatic, adaptive rate limiting and backoff so developers on low-tier plans don't hit rate-limit walls.

7. **Fallback chains** — Allow the developer to define an ordered list of models. If the primary model fails or exceeds a latency threshold, automatically fall back to the next model in the chain.

8. **Structured output support** — Built-in helpers for requesting and validating JSON/structured responses from models, with schema validation (e.g., via Pydantic).

9. **Response caching** — Optional exact-match caching of prompt/response pairs during development to avoid redundant API calls and reduce cost. Cache is local and clearable.

10. **Cost tracking and budgets** — Track cumulative spend per provider, per model, and per session. Support configurable budget caps with warnings and hard stops.

11. **Logging and observability** — Every LLM call is logged with: timestamp, model, provider, token usage, latency, cost estimate, a stable hash of the full prompt, and truncated prompt/response. The prompt hash allows correlating log entries with specific inputs even when the prompt text is truncated. Logs are written to a configurable location. Verbosity is controllable (`--quiet`, `--verbose`, `--debug`).

12. **Error handling** — Graceful handling of: invalid/expired keys, network failures, rate limits (with retry), malformed responses, unsupported models, and provider outages. All errors produce actionable messages.

### Cross-Cutting Requirements

Apply to both CLI and library usage.

13. **Secure secrets management** — API keys are never stored in plain text in user-visible locations. Keys are written to `.env` files with `600` permissions, and the tool warns if `.env` is not in `.gitignore`. Support reading keys from environment variables, `.env` files, or a custom path.

14. **Configuration file** — Support a `lmentry.toml` (or similar) config file for persistent settings: default model, fallback chains, budget caps, log level, cache behavior, etc.

### Non-Goals

- LMentry is **not** a prompt engineering framework — it does not provide chains, agents, or tool-use orchestration (use LangChain, LlamaIndex, etc. for that).
- LMentry is **not** a hosted service — it runs entirely on the developer's machine.
- LMentry does **not** fine-tune or train models.
- LMentry does **not** manage prompt versioning or template libraries (this may be considered for a future release).

---

## Inputs

| Input | Required | Source | Example |
|-------|----------|--------|---------|
| API key | Yes (per provider) | Interactive setup, `.env`, or env var | `OPENAI_API_KEY=sk-...` |
| Model identifier | Yes (for chat/compare) | CLI argument or config default | `gpt-4o`, `claude-3.5-sonnet` |
| Prompt / message | Yes (for chat/compare) | Interactive input or `--prompt` flag | `"Explain monads in one sentence"` |
| Prompt suite file | Optional (for compare) | File path | `prompts.yaml` |
| Config file | Optional | `lmentry.toml` in project root or `~/.config/lmentry/config.toml` | See Configuration section |

---

## Outputs

| Output | Format | Destination |
|--------|--------|-------------|
| Chat responses | Streamed text | stdout |
| Comparison report | Formatted table or JSON | stdout or file (`--output`) |
| Model list | Formatted table or JSON | stdout |
| Cost summary | Formatted table | stdout |
| Call logs | Structured log lines (JSON or human-readable) | Log file or stderr |
| `.env` file | `KEY=value` pairs | Project root or specified path |

---

## Functional Requirements

### FR-1: Provider Setup Wizard

The `lmentry setup` command launches an interactive wizard.

- **FR-1.1**: Display a numbered list of supported providers.
- **FR-1.2**: For the selected provider, display step-by-step instructions including the URL to obtain an API key.
- **FR-1.3**: Offer to open the URL in the default browser.
- **FR-1.4**: Accept the pasted API key (masked input).
- **FR-1.5**: Validate the key by making a lightweight API call (e.g., list models).
- **FR-1.6**: On success, report which models the key grants access to.
- **FR-1.7**: Save the key to `.env` with `600` permissions.
- **FR-1.8**: Add `.env` to `.gitignore` if not already present.
- **FR-1.9**: Detect existing keys in environment variables or common config locations and offer to import them.
- **FR-1.10**: Support non-interactive mode (`lmentry setup --provider openai --key sk-...`).

### FR-2: Interactive Chat

The `lmentry chat <model>` command starts a REPL session.

- **FR-2.1**: Accept user input, send to the specified model, and stream the response.
- **FR-2.2**: Maintain conversation history within the session.
- **FR-2.3**: Display token usage and cost estimate after each response.
- **FR-2.4**: Support multi-model mode (`lmentry chat gpt-4o claude-3.5-sonnet`) showing responses side-by-side.
- **FR-2.5**: Support `/commands` within the chat (e.g., `/clear`, `/switch <model>`, `/cost`, `/exit`).
- **FR-2.6**: **Model name completion** — tab-completion and fuzzy matching for model names in the CLI and REPL. Typing a partial name (e.g., `claude-3.5` or `gpt-4o`) should suggest or resolve to the full model identifier. Works for CLI arguments (`lmentry chat <tab>`), `/switch` commands, and anywhere a model name is accepted.

### FR-3: Model Comparison (Arena)

The `lmentry compare` command runs prompts against multiple models.

- **FR-3.1**: Accept a single prompt via `--prompt` or a prompt suite via `--file`.
- **FR-3.2**: Run the prompt(s) against all specified models concurrently.
- **FR-3.3**: Produce a comparison report with: response text, latency, tokens, and cost.
- **FR-3.4**: Optionally score responses using a configurable judge model (`--judge gpt-4o`).
- **FR-3.5**: Output as formatted table (default) or JSON (`--json`).

### FR-4: Model Discovery and Recommendation

The `lmentry models` command lists available models. The `lmentry recommend` command provides opinionated guidance.

- **FR-4.1**: For each configured provider, query available models.
- **FR-4.2**: Display model name, context window, input/output pricing, and capabilities.
- **FR-4.3**: Support filtering by provider (`--provider openai`) or capability (`--capability vision`).
- **FR-4.4**: `lmentry recommend <use-case>` suggests models for a task category. Supported categories include (but are not limited to): `code-generation`, `summarization`, `classification`, `vision`, `cheap-and-fast`, `highest-quality`, `long-context`.
- **FR-4.5**: Recommendations are ranked by a composite score derived from public benchmarks (SWE-bench, HumanEval, MMLU, MT-Bench, etc.), cost, and latency, and filtered to only models the developer has keys for.
- **FR-4.6**: Benchmark and pricing data is maintained in a bundled catalog that ships with the package and can be refreshed independently (`lmentry models --update-catalog`). The update pulls from curated public benchmark sources.
- **FR-4.7**: If Ollama is detected locally, offer to use a small model for lightweight tasks (use-case classification, prompt pre-screening, sanity checks) to avoid burning paid tokens. Enabled via config (`local_model = true`) or CLI (`--local`). Gracefully skipped when Ollama is unavailable.

### FR-5: Cost Tracking

The `lmentry cost` command displays spend summaries.

- **FR-5.1**: Track cumulative token usage and estimated cost per provider, model, and session.
- **FR-5.2**: Support budget caps with configurable warning thresholds and hard stops.
- **FR-5.3**: Display a summary table on demand.

### FR-6: Adaptive Throttling

- **FR-6.1**: Integrate `gentlify` to automatically manage request rates per provider.
- **FR-6.2**: Detect rate-limit responses (HTTP 429) and back off adaptively.
- **FR-6.3**: Log throttling events at `INFO` level.

### FR-7: Fallback Chains

- **FR-7.1**: Accept an ordered list of models in config or CLI (`--fallback claude-3.5-sonnet,gpt-4o-mini`).
- **FR-7.2**: On primary model failure or timeout, automatically retry with the next model.
- **FR-7.3**: Log fallback events and include the final model used in the response metadata.

### FR-8: Response Caching

- **FR-8.1**: Cache prompt/response pairs locally (opt-in via config or `--cache`).
- **FR-8.2**: Use exact-match on (model, prompt, key parameters) as the cache key.
- **FR-8.3**: Support cache clearing (`lmentry cache clear`).

---

## Configuration

Configuration is resolved in the following precedence order (highest to lowest):

1. CLI flags (e.g., `--model gpt-4o`)
2. Environment variables (e.g., `LMENTRY_DEFAULT_MODEL=gpt-4o`)
3. Project config file (`./lmentry.toml`)
4. User config file (`~/.config/lmentry/config.toml`)
5. Built-in defaults

### Config File Format (TOML)

```toml
[defaults]
model = "gpt-4o"
log_level = "info"
cache = false

[budget]
monthly_cap_usd = 50.00
warning_threshold_pct = 80

[fallback]
models = ["gpt-4o", "claude-3.5-sonnet", "gpt-4o-mini"]
timeout_seconds = 30

[providers.openai]
# Key is read from .env or environment; never stored here.
default_model = "gpt-4o"

[providers.anthropic]
default_model = "claude-3.5-sonnet"
```

---

## Testing Requirements

- **Unit tests** for all core modules (key validation, cost calculation, config resolution, caching logic).
- **Integration tests** for provider setup flow (mocked API), chat session, and comparison pipeline.
- **Minimum 90% line coverage** for core library code, reported via [Codecov](https://codecov.io/).
- **CLI tests** verifying all subcommands, flags, and error paths.
- **Python version matrix** — tests must pass on Python 3.11, 3.12, 3.13, and 3.14.

---

## CI/CD & Release

- **CI workflow** — GitHub Actions running lint, type-check, and tests on every push and pull request, across the Python 3.11–3.14 version matrix.
- **Coverage reporting** — upload coverage to Codecov on every CI run; add a dynamic Codecov badge to the README.
- **Automated PyPI publishing** — publish to PyPI on tagged releases using trusted publishing (OIDC) to avoid storing API tokens as secrets.
- **README badges** — CI status, PyPI version, Python versions, license (Apache-2.0), coverage (Codecov), and typed (`py.typed`).

---

## Security and Compliance Notes

- API keys must never be logged, printed in full, or written to any file other than the designated `.env`.
- The `.env` file must be created with `600` permissions (owner read/write only).
- The tool must warn if `.env` is not in `.gitignore`.
- **Security audit** — `lmentry audit` scans for common key-safety issues and reports actionable warnings:
  - `.env` files without `600` permissions.
  - `.env` not listed in `.gitignore`.
  - API key patterns (e.g., `sk-`, `ANTHR-`, `AIza`) found in source files, config files, shell history, or other non-`.env` locations in the project tree.
  - Keys present in environment variables that are not sourced from a secure `.env` file.
  - The audit is non-destructive (read-only) and can be run at any time or integrated into CI as a pre-commit check.
- No telemetry or external data collection. LMentry does not phone home or route data through intermediary servers.
- All network traffic goes directly to the LLM provider APIs.
- **Cloud and server safe** — LMentry must operate correctly in headless, containerized, and cloud-server environments (e.g., CI runners, Docker, EC2, Lambda). Key-loading must support environment variables and mounted secrets (not just local `.env` files), and interactive prompts must be skippable or auto-detected as unavailable when no TTY is present.

---

## Performance Notes

- **Concurrency**: Model comparison requests should be dispatched concurrently (async) to minimize wall-clock time.
- **Streaming**: Chat responses must be streamed token-by-token to stdout for low perceived latency.
- **Caching**: Cache lookups must be O(1) (hash-based) and add negligible overhead.
- **Startup time**: The CLI should start in under 500ms for common commands.

---

## Acceptance Criteria

The project is considered complete when:

1. A developer can run `pip install lmentry` and `lmentry setup` to configure at least 3 providers (OpenAI, Anthropic, Google) in under 2 minutes each.
2. `lmentry chat <model>` provides a working, streaming REPL with token/cost display.
3. `lmentry compare` produces a structured side-by-side report for 2+ models.
4. `lmentry models` lists available models with pricing and capabilities.
5. `lmentry cost` shows accurate cumulative spend tracking.
6. Rate limiting is handled transparently via `gentlify` with no user intervention.
7. All API keys are stored securely and never exposed in logs or output.
8. Test coverage meets the 90% threshold for core library code.
9. The library API exposes all CLI functionality for programmatic use.
10. CI passes on Python 3.11, 3.12, 3.13, and 3.14 with lint, type-check, and tests.
11. The package is published to PyPI via automated trusted publishing on tagged releases.
12. README displays dynamic badges for CI status, PyPI version, Python versions, license, coverage, and typing.
