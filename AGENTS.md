# AGENTS.md

Guidance for **coding assistants** (Cursor, Claude Code, etc.) and human contributors working in this repository. Covers the application stack, architecture, and conventions for commits and pull requests.

---

## Repository layout

This repo currently contains a single project under `estimator/` — all commands below assume `cd estimator` first. The repo is part of a Master in AI Engineering evolving module-by-module (CAG estimation today; pgvector corpus in place; retrieval into estimation prompts next).

## Common commands

Dependency / runtime management uses **uv** (Astral) and Python 3.11.

```bash
# Install deps (creates .venv)
uv sync

# Run the API locally with hot reload
uv run uvicorn app.main:app --reload

# Run the full test suite
uv run pytest

# Run a single test file or test
uv run pytest tests/test_health.py
uv run pytest tests/test_health.py::test_name -v

# Lint
uv run ruff check .
uv run ruff format .

# Streamlit chat UI (Session 5 — HTTP client; requires FastAPI running in parallel)
# Terminal 1: uv run uvicorn app.main:app --reload
# Terminal 2:
uv run streamlit run streamlit_app.py

# Docker (recommended — postgres + API; bind-mounts for live reload)
docker compose up --build
docker compose run --rm estimator alembic upgrade head

# Load sample budgets / run search archetypes (API must be up; needs OPENAI_API_KEY)
# uv run python scripts/ingest_examples.py
# uv run python query_examples.py

# Stress evaluation (Exercise 6.1)
uv run python -m evals.stress.run                              # mocked in-process (CI / fast local)
uv run python -m evals.stress.run --real-llm --cache-on        # real LLM in-process
uv run python -m evals.stress.run --http http://localhost:8000  # against running API

# Regenerate localized reports from results.csv (Spanish copied to REPORT.md)
uv run python -m evals.stress.aggregate --run-mode "in-process (real LLM)" --cache-on
```

Service listens on `http://localhost:8000`; Postgres on `localhost:5432`. `/docs` (Swagger) and `/redoc` are enabled. Health probe at `GET /health`. Form API: `POST /api/v1/estimate`. Session API: `POST /sessions`, `GET /sessions/{id}`, `POST /sessions/{id}/estimate`. Embedding corpus: `POST /embeddings/ingest`, `POST /search`. The Streamlit UI listens on `http://localhost:8501`.

## Architecture

The estimator implements **Cache Augmented Generation (CAG)** for estimation: reference projects are inlined as static Jinja2 text in the system prompt — the chat path has **no retrieval step**. Separately, Session 08 persists historical budget embeddings in **PostgreSQL + pgvector** and exposes `POST /embeddings/ingest` and `POST /search`; estimation prompts do **not** consume those hits yet (future RAG). Sessions remain process-local (`SessionStore`).

### Request paths

**Form API (Session 4):**

1. `app/routers/estimations.py` — `POST /api/v1/estimate?prompt_version=v1|v2` accepts an `EstimationRequest` (`description`, `project_type`, `detail_level`, `output_format`, optional `reference_projects`).
2. `app/services/llm_service.py::generate_estimation_from_request` — renders prompts via `render_estimation_prompt` from `app/prompts/estimation/v{1,2}/`, then calls `_dispatch_llm`.
3. Returns `EstimationResponse` with `text` and `prompt_version`.

**Session API (Session 5):**

1. `app/routers/sessions.py` — `POST /sessions` creates a session; `POST /sessions/{id}/estimate` accepts multipart transcript + optional PDF/DOCX attachments; `GET /sessions/{id}` returns a snapshot for observation.
2. `app/services/session_estimation.py::run_session_estimation` — enriches transcript (Path B attachment extraction), builds messages (`build_session_messages` → `cap_outgoing_messages`), calls `generate_estimation_from_messages`.
3. Post-turn: heuristic `project_metadata` update, anchor/summary/tier maintenance, `last_turn_observed` population, `turn_observed` structlog event.
4. Returns `SessionEstimationResponse` with `text`, `prompt_version`, `project_metadata`.

Both paths converge on `_dispatch_llm` in `llm_service.py`, which routes a message array to OpenAI, Anthropic, or Gemini.

**Streamlit UI** (`streamlit_app.py`, Session 5) is an **HTTP client only** — it does not import `llm_service` or call providers directly. FastAPI must be running separately. Entrypoint is `main()` → `bootstrap()` → `render_sidebar()` → `render_chat()`. Pure HTTP logic lives in `app/ui/streamlit_helpers.py`.

### CAG prompt source

Few-shot examples live in `app/prompts/estimation/v{1,2}/examples.j2`, rendered by `app/prompts/loader.py`. Canonical project data for dynamic reference rendering is in `app/prompts/examples_catalog.py`. When estimation graduates to RAG, the prompts/loader seam is the replacement point for injecting retrieved chunks. Persistence and search flows: `estimator/docs/ARCHITECTURE.md`.

### Observability

- `app/services/llm_wrapper.py` — `compute_cost_usd` and `MODEL_COSTS` pricing table.
- `app/services/llm_cache.py` — exact and semantic cache lookup/store, controlled by `LLM_CACHE_ENABLED` and `SEMANTIC_CACHE_THRESHOLD`.
- `turn_observed` structlog event emitted at end of `run_session_estimation` with per-turn tokens, cost, latency, cache hit kind, tier, and window size.

Key design points future changes should respect:

- **Provider abstraction lives in one file** (`llm_service.py`). All three providers return the same dict shape (`estimation`, `model`, `provider`, `finish_reason`, `usage`) so routers stay provider-agnostic.
- **Settings are a cached singleton** via `app/config.py::get_settings` (`@lru_cache`). Pydantic Settings runs a `model_validator` that requires the API key matching `LLM_PROVIDER` to be set. Because of the cache, **any change to `.env` requires restarting the process** (uvicorn `--reload` is not enough).
- **Pricing assumptions** (62.50 EUR/h dev, 50 EUR/h designer) live in the Jinja prompt templates. Per-token USD costs for observability are in `llm_wrapper.MODEL_COSTS`.
- **`thinking_budget` is Anthropic-only** — for OpenAI and Gemini it is logged as a warning and ignored. The Anthropic wrapper auto-pads `max_tokens` so it stays above the budget.
- **Streamlit helpers** (`app/ui/streamlit_helpers.py`) hold testable pure functions for session HTTP calls. Keep `streamlit_app.py` thin.
- **Logging** is `structlog`, configured in `app/logging.py::configure_logging` (called from `main.py` lifespan): JSON in `production`, console in dev. Use `structlog.get_logger()` rather than stdlib `logging`.
- **Session memory stack** — anchors (`anchor_extractor.py`), rolling summary (`summarizer.py`, capped at 2000 chars), dynamic tiers (`tiers.py`), and heuristic metadata (`metadata_extractor.py`) complement the sliding-window history. See `estimator/docs/ARCHITECTURE.md` for the full flow.

Removed in Sessions 4–6: `app/context/examples.py`, `evaluation.py`, `generate_estimation`, `stream_estimation`, `build_system_prompt`, preprocessing knobs, structural validation in the router response.

## How to compare in live demos

The form endpoint supports A/B prompt comparison via the `prompt_version` query param without code changes.

```bash
# v1 vs v2 prompt templates
for VERSION in v1 v2; do
  curl -s "localhost:8000/api/v1/estimate?prompt_version=$VERSION" \
    -H 'Content-Type: application/json' \
    -d '{
      "description": "We need a small CRM with auth, contacts and roles. MVP in six weeks.",
      "project_type": "web_saas",
      "detail_level": "medium",
      "output_format": "phases_table"
    }' | jq "{version:\"$VERSION\", text_length:(.text|length)}"
done
```

Architecture details and session multi-turn flow: `estimator/docs/ARCHITECTURE.md`.

## Configuration

`.env` (copied from `.env.example`) drives everything via `pydantic-settings`. Notable vars:

- `LLM_PROVIDER` — `openai`, `anthropic` (code default), or `gemini`. `.env.example` uses `openai`.
- `LLM_MODEL` — model id passed straight through to the SDK (e.g. `gpt-4o-mini`, `claude-haiku-4-5`, `gemini-2.0-flash`).
- `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` — the key matching `LLM_PROVIDER` is required for chat; **`OPENAI_API_KEY` is also required for embedding ingest/search** regardless of chat provider.
- `DATABASE_URL` — async Postgres URL for the embedding corpus (default `postgresql+asyncpg://estimator:estimator@localhost:5432/estimator`; Compose sets host to `postgres`).
- `APP_ENV` — `development` | `staging` | `production` (controls log renderer).
- `LOG_LEVEL` — `DEBUG` | `INFO` | `WARNING` | `ERROR`.
- `MAX_CONVERSATION_TURNS` — user/assistant pairs kept per session (default `6`).
- `MAX_ATTACHMENT_CHARS` — cap on extracted attachment text (default `60000`).
- `LLM_CACHE_ENABLED` — enable exact/semantic LLM response cache (default `true`).
- `SEMANTIC_CACHE_THRESHOLD` — cosine similarity threshold for semantic cache hits (default `0.85`).
- `TIER_MEDIUM_CHARS` / `TIER_HIGH_CHARS` — enriched-transcript size thresholds for dynamic prompt tiers (defaults `8000` / `20000`).

## Docker

Multi-stage Dockerfile: `builder` installs prod-only deps with `uv sync --no-install-project --no-dev`; `runtime` is `python:3.11-slim` carrying `/app/.venv`, `app/`, `alembic/`, `alembic.ini`, `data/`, `scripts/`, and `query_examples.py`, running as non-root `appuser`. HEALTHCHECK probes `/health`.

`docker-compose.yml` runs **`postgres`** (`pgvector/pgvector:pg16`, healthcheck + volume) and **`estimator`** (`depends_on` healthy Postgres, `DATABASE_URL` to that service). Dev bind-mounts cover `app/`, migrations, corpus, and scripts with uvicorn `--reload` — strip bind mounts and `--reload` for production. Apply schema with `docker compose run --rm estimator alembic upgrade head`.

---

## Commit and PR conventions

### Instructions for assistants

When the user asks for a commit message, `git commit` text, or PR copy:

1. **Match Conventional Commits** for the subject line (see below).
2. **Use imperative mood** in the description (e.g. "add", "fix", "remove" — not "added", "fixes", "adding").
3. **Keep the subject ≤ ~72 characters** when practical; no trailing period on the subject.
4. **Choose the narrowest accurate `type`**. If unsure between `feat` and `fix`, ask one clarifying question or default to what the code actually does (user-visible behavior → `feat`/`fix`; tooling-only → `chore`/`ci`).
5. For **PRs**, prefer a Conventional-Commit-style **title** and a **body** with Overview, Changes, Testing, and links to tickets (Trello/Jira) when the user supplied them.
6. This project hosts code on **GitHub**; issue keys in footers may be Jira-style (`PROJ-123`) or whatever the team uses — do not assume `#123` unless the user referenced it.
7. When a change affects **architecture** (layers, routers, services, context/CAG, LLM providers, config, or cross-package dependencies), update **`estimator/docs/ARCHITECTURE.md`** in the same change set (diagrams, tables, flows). Link from `estimator/README.md`; do not duplicate full architecture prose there.
8. Keep all **tracked documentation in English**.

### Commit messages (Conventional Commits)

#### Format

```text
<type>(<optional-scope>): <description>

<optional body — blank line before this block>

<optional footer(s)>
```

#### Allowed `<type>` values

Use one of these literals in lowercase:

| type | Use when |
|------|----------|
| `feat` | New user-facing capability or API behavior |
| `fix` | Bug fix or correcting broken behavior |
| `chore` | Maintenance that is not a product fix/feature (deps, config noise, ignore files) |
| `docs` | Documentation only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `style` | Formatting / whitespace only (no behavior change) |
| `test` | Tests only (add/fix coverage) |
| `ci` | CI/CD pipelines, automation around builds |
| `build` | Build system or compiled artifacts configuration |

#### Scope

- Optional parenthetical after the type: `feat(sales): ...`, `fix(api): ...`, `chore(docker): ...`.
- Use a short domain: area of the codebase, gem, or subsystem (e.g. `sales`, `api`, `webpack`, `deps`).

#### Subject (`<description>`)

- Imperative, present tense: completes *"If applied, this commit will …"*
- Lowercase first letter (types like `API` in scope are fine).
- **No** trailing period.

#### Body

- Explains **what** and **why**, not line-by-line **how** (the diff shows how).
- Use bullets for multiple distinct points.
- One blank line between subject and body.

#### Footer

- **Breaking change:** start a line with `BREAKING CHANGE:` followed by what breaks and what callers should do.
- **Tickets:** e.g. `Resolves #123`, `Closes PROJ-456`, or a Trello card URL if that is team standard.

#### Examples

**Good**

```text
feat(sales): add manual ad report cost entry form

Validate overlapping date ranges server-side before save.

Closes ABC-789
```

```text
chore(cursor): ignore local environment files in cursorignore
```

**Avoid**

```text
Fixed the bug.
```

```text
feat: updates
```

```text
feat(sales): Added manual reports.
```

(last: wrong tense / ends with period)

### Pull requests (GitHub)

PRs are opened on **GitHub** against the target branch the team uses (often **`main`** — confirm if unsure).

#### Title

- Same spirit as commits: optional Conventional Commits shape, e.g. `feat(sales): manual ad reports for non-integrated channels`.
- Should stand alone: a reviewer understands the theme without opening every file.

#### Description (suggested sections)

Use markdown. Suggested structure:

```markdown
## Overview
<Why this change exists; link to product/Trello/Jira context if available.>

## Changes
- <bullet — major behavior or file areas>
- <bullet>

## Testing
1. <step a reviewer can run>
2. <step>

## Related
- <Trello / Jira / doc links>
```

Optional checklist (toggle as appropriate):

```markdown
- [ ] Tests added or updated
- [ ] No unintended secrets or credentials
- [ ] estimator/docs/ARCHITECTURE.md updated if architecture changed
- [ ] AGENTS.md / migrations / locales updated if applicable
```

#### Hygiene

- Keep the branch reasonably up to date with the base branch (merge or rebase per team preference) before final review.
- Prefer **small, reviewable PRs**; if the diff is huge, call that out in Overview and justify.

### Why this matters

Structured commits improve **history search**, **changelogs**, and **review focus**. Structured PRs reduce round-trips and make **QA steps** explicit.
