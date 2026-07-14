# Estimator CAG — AI-Powered Software Estimation Service

AI-powered software project estimation service using a **Cache Augmented Generation (CAG)** architecture.

## What is CAG and why we use it

CAG (Cache Augmented Generation) is an architecture pattern where relevant context is injected directly into the LLM prompt as static text. **Estimation** still works this way: reference projects are few-shot examples inside Jinja system prompts — the chat path does not retrieve from the vector store.

The implementation uses **Jinja2** templates under `app/prompts/estimation/`: each version (`v1`, `v2`) has `system.j2`, `user.j2`, and `examples.j2`, rendered by `app/prompts/loader.py`. Two prompt sets exist for live A/B comparisons in demos.

Separately, Sessions 07–08 add a **budget embedding corpus** in PostgreSQL + pgvector with `POST /embeddings/ingest` and `POST /search`. Estimation prompts do not consume those hits yet; wiring retrieval into the system prompt is the next step toward full **RAG**.

CAG remains a good estimation baseline because:
- It is simple to implement and debug for a small example set
- Chat sessions stay process-local (no session DB)
- It works well when the inlined example volume is manageable

## Prerequisites

- **Docker** and **Docker Compose** (API + Postgres with pgvector)
- An **API key** for OpenAI, Anthropic, or Google Gemini (chat LLM)
- **`OPENAI_API_KEY`** for embedding ingest/search (`text-embedding-3-small`), even if chat uses another provider
- **uv** and Python 3.11+ (for local runs or Streamlit)
- Python is **not** required locally if you only use Docker for the API

## Configuration

Copy the environment file and set your variables:

```bash
cp .env.example .env
# Edit .env and set your real API key
```

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | Active provider: `openai`, `anthropic`, or `gemini` |
| `LLM_MODEL` | Provider model (e.g. `gpt-4o-mini`, `claude-haiku-4-5`, `gemini-2.0-flash`) |
| `OPENAI_API_KEY` | OpenAI key (required when `LLM_PROVIDER=openai`; also required for embeddings) |
| `ANTHROPIC_API_KEY` | Anthropic key (required when `LLM_PROVIDER=anthropic`) |
| `GEMINI_API_KEY` | Google Gemini key (required when `LLM_PROVIDER=gemini`) |
| `DATABASE_URL` | Async Postgres URL (default `postgresql+asyncpg://estimator:estimator@localhost:5432/estimator`; Compose overrides host to `postgres`) |
| `APP_ENV` | Environment: `development`, `staging`, or `production` |
| `LOG_LEVEL` | Log level: `DEBUG`, `INFO`, `WARNING`, or `ERROR` |
| `MAX_CONVERSATION_TURNS` | User/assistant pairs kept in memory per session (default: `6`) |
| `MAX_ATTACHMENT_CHARS` | Cap on extracted attachment text (default: `60000`) |
| `LLM_CACHE_ENABLED` | Enable exact/semantic LLM response cache (default: `true`) |
| `SEMANTIC_CACHE_THRESHOLD` | Similarity threshold for semantic cache (default: `0.85`) |
| `TIER_MEDIUM_CHARS` | Enriched transcript size for `medium` tier (default: `8000`) |
| `TIER_HIGH_CHARS` | Enriched transcript size for `high` tier (default: `20000`) |

`.env.example` defaults to `openai`; without a `.env` file, `app/config.py` falls back to `anthropic` / `claude-haiku-4-5`.

**Important:** `get_settings()` is cached with `@lru_cache`. After editing `.env`, **restart the process** (uvicorn or Streamlit). Uvicorn's `--reload` flag does not reload the cached settings singleton.

## Quick start with Docker (recommended)

1. Clone the repository and enter the directory:
   ```bash
   cd estimator
   ```

2. Configure `.env` (see section above). Include `OPENAI_API_KEY` if you will ingest or search embeddings.

3. Build and start **Postgres + API**:
   ```bash
   docker compose up --build
   ```

4. Apply migrations (once per fresh database):
   ```bash
   docker compose run --rm estimator alembic upgrade head
   ```

5. The API is at `http://localhost:8000`; Postgres is on `localhost:5432`.

> Compose runs `postgres` (`pgvector/pgvector:pg16`) and `estimator`. Streamlit is **not** in Compose — run it on the host (see below).

## Alternative: local run without Docker

Postgres must still be reachable (e.g. `docker compose up -d postgres`). Point `DATABASE_URL` at `localhost` (the `.env.example` default), then:

```bash
uv sync
# Configure .env with your API keys
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

## Web UI (Streamlit — Session 5)

Multi-turn conversational client that talks to the session API. **Requires FastAPI running in parallel.**

```bash
# Terminal 1 — API
uv run uvicorn app.main:app --reload

# Terminal 2 — Streamlit
uv sync
cp .env.example .env   # configure API key for your LLM_PROVIDER
uv run streamlit run streamlit_app.py
```

Open `http://localhost:8501`. On page load a session is created (`POST /sessions`) and `session_id` is stored. The main area accepts a **transcript** and PDF/DOCX attachments; **Estimate** sends `POST /sessions/{session_id}/estimate`. The sidebar shows updated `project_metadata` after each turn and a **New conversation** button that creates a fresh session and resets local state.

HTTP client details (no direct LLM calls): [docs/ARCHITECTURE.md#clients](docs/ARCHITECTURE.md#clients).

## Conversational sessions (Session 5)

The service supports multi-turn estimation with in-process memory and document attachments.

### Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `POST` | `/sessions` | Create an empty session; returns `{"session_id": "..."}` |
| `GET` | `/sessions/{session_id}` | Memory snapshot: anchors, summary, tier, `last_turn_observed` |
| `POST` | `/sessions/{session_id}/estimate` | Estimate via `multipart/form-data` (`transcript` + optional `attachments`) |

Sessions live in a process-local dictionary: they are lost on service restart and are not shared across workers.

Example with transcript and attachment:

```bash
SESSION_ID=$(curl -s -X POST http://localhost:8000/sessions | jq -r .session_id)

curl -X POST "http://localhost:8000/sessions/${SESSION_ID}/estimate?prompt_version=v2" \
  -F "transcript=We need a CRM with auth, contacts and roles. MVP in six weeks." \
  -F "attachments=@spec.docx"
```

**Response** (`SessionEstimationResponse`):

```json
{
  "text": "...",
  "prompt_version": "v2",
  "project_metadata": {
    "project_name": null,
    "assumed_team_size": null,
    "mentioned_technologies": [],
    "agreed_scope": null
  }
}
```

### Attachments: Path B (local extraction)

We implement **Path B** — text extraction in the AI service with `pypdf` (PDF) and `python-docx` (Word), concatenated to the transcript with the separator `=== attachment: filename ===`.

**Why Path B and not direct multimodal (Path A):**

- **Provider independence** — the LLM wrapper works with OpenAI, Anthropic, or Gemini without a Files API.
- **Control and testability** — extracted text is inspectable and mockable in tests.
- **RAG preparation** — the same extraction logic is the first step of the module 3 chunking pipeline.

Path A (uploading the PDF to a multimodal provider) is valid when development speed matters and provider coupling is acceptable; for this exercise we chose Path B.

### `project_metadata` extraction: heuristics

After each turn, the service updates `project_metadata` with heuristic rules (`app/services/metadata_extractor.py`): regex for project name and team size, a known-technology vocabulary, and simple patterns for agreed scope.

**Why heuristics and not an LLM extractor:**

- **Zero cost and latency** — no second model call per turn.
- **Predictable behavior** — easy to debug in tests and in the client metadata panel.
- **Bounded domain** — relevant facts (name, stack, team, scope) fit reasonable patterns at this stage.

An LLM extractor (second call with a structured prompt) is more robust to language variation and multilingual input; it is the natural evolution if heuristics start failing in production.

The `<project_metadata>` block is injected into the system prompt via `_project_metadata.j2` (v1 and v2) and is regenerated on every call together with the sliding history window.

Detailed multi-turn pipeline (`build_session_messages` → `cap_outgoing_messages` → `generate_estimation_from_messages` → provider): see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Stress evaluation (Exercise 6.1)

Harness under `evals/stress/` to measure latency, cost, cache, and memory drift across multi-turn scenarios with attachments of varying size.

```bash
# Mock in-process (fast, no API key)
uv run python -m evals.stress.run

# Real LLM in-process (reads .env)
uv run python -m evals.stress.run --real-llm --cache-on

# Against a running API
uv run python -m evals.stress.run --http http://localhost:8000

# Regenerate localized reports from results.csv (Spanish copied to REPORT.md)
uv run python -m evals.stress.aggregate --run-mode "in-process (real LLM)" --cache-on
```

The runner writes `evals/stress/results.csv` (tracked). Each turn reads `GET /sessions/{id}` after the estimate to obtain real `last_turn_observed` — see [docs/ARCHITECTURE.md#session-snapshot-and-observation](docs/ARCHITECTURE.md#session-snapshot-and-observation). Localized reports live under `evals/stress/localized/` (`REPORT.en.md`, `REPORT.es.md`); `REPORT.md` at the stress root is temporarily a Spanish publish copy. Backups and run logs are gitignored.

## Embedding corpus + semantic search (Sessions 07–08)

Structural chunking and OpenAI embeddings for historical budgets, persisted in PostgreSQL 16 + pgvector. Schema is Alembic-managed (`documents` + `chunks`). Estimation still uses CAG; this corpus is searchable via HTTP but not yet injected into estimate prompts.

**Requirements:** migrated database, `DATABASE_URL`, and `OPENAI_API_KEY` (embeddings use `text-embedding-3-small` regardless of `LLM_PROVIDER`).

```bash
docker compose up -d --build
docker compose run --rm estimator alembic upgrade head
uv run python scripts/ingest_examples.py   # 15 budgets → POST /embeddings/ingest
uv run python query_examples.py            # five query archetypes → POST /search
# Sample capture: output_examples.txt
```

Sample data: `data/budgets_sample.json` (15 normalized proposals, ~64 components). Pipeline details: [docs/ARCHITECTURE.md#embedding-pipeline](docs/ARCHITECTURE.md#embedding-pipeline).

### `POST /embeddings/ingest`

Persists one budget document and its embedded chunks in a **single transaction**. Duplicate `source_path` returns **409** `{detail, document_id}`.

```bash
jq -n --slurpfile budgets data/budgets_sample.json \
  '{source_path: "data/budgets_sample.json#\($budgets[0].budget_id)",
    document_type: "budget",
    content: $budgets[0]}' | \
  curl -s -X POST http://localhost:8000/embeddings/ingest \
    -H "Content-Type: application/json" \
    -d @- | jq .
```

**Response** (`IngestResponse`):

```json
{
  "document_id": 1,
  "chunks_created": 4,
  "embedding_dimension": 1536,
  "ingestion_time_ms": 842
}
```

### `POST /search`

Embed the query with the same model, then return the `k` nearest chunks by **cosine distance** (sequential scan; no ANN index yet).

```bash
curl -s -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query":"REST API development with JWT authentication for financial sector","k":5}' | jq .
```

**Response** (`SearchResponse`): `{query, k, search_time_ms, results[]}` where each result has `chunk_id`, `document_id`, `chunk_type`, `content`, `distance`, `metadata`.

### Corpus helpers

| Script | Role |
|--------|------|
| `scripts/ingest_examples.py` | POSTs all 15 sample budgets (`source_path` like `data/budgets_sample.json#BUD-…`; treats 409 as already loaded) |
| `query_examples.py` | Five query archetypes against `POST /search`; see `output_examples.txt` for a captured run |

### Design decisions

**Two tables (`documents` + `chunks`), not one flattened table.** A document is one ingested budget (`source_path`, type, document-level metadata). Chunks are the retrieval unit: one row per budget component with `content`, `embedding`, and chunk metadata. Splitting keeps cascade deletes clean (`ON DELETE CASCADE`), avoids repeating document fields on every component, and matches how RAG later retrieves passages while still joining back to provenance.

**JSONB for metadata, not dedicated columns.** Chunk/document filters (sector, year, technology, complexity, hours) evolve with the corpus. JSONB plus a GIN index on `chunks.metadata` avoids a migration per filter field; selective `metadata->>'…'` predicates stay available for the live session without baking them into the schema now.

**Cosine distance (`<=>` / `cosine_distance`), not L2 or inner product.** OpenAI `text-embedding-3-small` vectors are L2-normalized, so cosine distance and (scaled) inner product rank equivalently; cosine remains the less surprising metric when norms drift and is the convention aligned with a future `vector_cosine_ops` index. L2 would be misleading once vectors are unit length.

**No HNSW/IVFFlat index yet.** The sample corpus is tiny (~64 chunks); a sequential scan is correct and fast. Leaving ANN indexing out keeps a clean baseline for the live session (index impact, metadata filters, hybrid search, tuning). Non-vector indexes (`source_path`, `document_id`, `chunk_type`, GIN on metadata) are in place for ordinary lookups only.

## Try the service

Health check:

```bash
curl http://localhost:8000/health
```

Estimation (Session 4 contract):

```bash
curl -X POST "http://localhost:8000/api/v1/estimate?prompt_version=v1" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "We need a small CRM with auth, contacts and roles. MVP in six weeks.",
    "project_type": "web_saas",
    "detail_level": "medium",
    "output_format": "phases_table"
  }'
```

**Request fields** (`EstimationRequest`):

| Field | Allowed values |
|-------|----------------|
| `description` | Project text (20–2000 characters) |
| `project_type` | `mobile_app`, `web_saas`, `internal_tool`, `data_pipeline` |
| `detail_level` | `summary`, `medium`, `detailed` |
| `output_format` | `phases_table`, `line_items`, `narrative` |

**Query param:** `prompt_version` — `v1` (default) or `v2`. Selects the Jinja template set under `app/prompts/estimation/`.

**Response** (`EstimationResponse`):

```json
{
  "text": "...",
  "prompt_version": "v1"
}
```

## Request flow

```mermaid
flowchart LR
  Client[curl_or_Streamlit_client]
  API[POST_/api/v1/estimate]
  Loader[render_estimation_prompt]
  Templates["prompts/estimation/v1|v2"]
  LLM[llm_service]
  Client --> API
  API --> Loader
  Loader --> Templates
  Loader --> LLM
  LLM --> API
```

## Project structure

```
estimator/
├── app/
│   ├── main.py                    # FastAPI, CORS, GET /health
│   ├── config.py                  # Pydantic Settings (incl. DATABASE_URL)
│   ├── logging.py                 # structlog (JSON in production)
│   ├── db/
│   │   ├── models.py              # Document / Chunk ORM (pgvector)
│   │   └── session.py             # async engine + sessionmaker
│   ├── routers/estimations.py     # POST /api/v1/estimate
│   ├── routers/sessions.py        # POST/GET /sessions, POST /sessions/{id}/estimate
│   ├── schemas/request_form.py    # EstimationRequest / EstimationResponse
│   ├── schemas/session.py         # SessionCreateResponse / SessionEstimationResponse
│   ├── services/llm_service.py    # generate_estimation_from_messages, 3 providers
│   ├── services/llm_wrapper.py    # cost_usd, MODEL_COSTS
│   ├── services/llm_cache.py      # exact/semantic cache
│   ├── services/anchor_extractor.py  # facts promoted to anchors
│   ├── services/summarizer.py     # rolling summary (cap 2000 chars)
│   ├── services/tiers.py          # dynamic tier by transcript size
│   ├── services/attachments.py    # Local PDF/DOCX extraction (Path B)
│   ├── services/metadata_extractor.py  # Post-turn heuristic for project_metadata
│   ├── services/session_estimation.py
│   ├── sessions.py                # ConversationHistory, ProjectMetadata, SessionStore
│   ├── prompts/
│   │   ├── loader.py              # render_estimation_prompt()
│   │   └── estimation/v1|v2/      # system.j2, user.j2, examples.j2
│   ├── ui/streamlit_helpers.py    # Pure HTTP helpers for session client
│   ├── embedding_pipeline/        # Chunk, embed, persist, search
│   │   ├── chunker.py             # JSONStructuralChunker (one component = one chunk)
│   │   ├── embedder.py            # OpenAIEmbedder (text-embedding-3-small)
│   │   ├── schemas.py             # Budget + ingest/search contracts
│   │   ├── ingest_service.py      # Transactional document ingest
│   │   ├── router.py              # POST /embeddings/ingest
│   │   ├── search_service.py      # Cosine-distance chunk search
│   │   └── search_router.py       # POST /search
│   └── fixtures/                  # Sample transcriptions (fixtures only)
├── alembic/                       # Async migrations (0001 documents + chunks)
├── alembic.ini
├── data/
│   └── budgets_sample.json        # 15 normalized proposals for embedding ingest
├── scripts/
│   └── ingest_examples.py         # Load sample corpus via HTTP
├── query_examples.py              # Five-archetype search demo
├── output_examples.txt            # Captured query_examples output
├── evals/stress/                  # Runner, metrics, aggregator (6.1)
│   ├── localized/                 # REPORT.en.md, REPORT.es.md
│   └── REPORT.md                  # Published copy (Spanish, temporary)
├── docs/ARCHITECTURE.md           # Form, session, persistence, embedding flows
├── streamlit_app.py               # Conversational UI (HTTP session client)
├── tests/                         # pytest + AppTest
├── Dockerfile                     # Multi-stage build with uv
├── docker-compose.yml             # postgres + estimator
└── pyproject.toml                 # Dependencies and tooling
```

## Tests and lint

```bash
uv run pytest -v          # 334 tests, 100% coverage on app/ + streamlit_app.py + scripts/
uv run ruff check .
uv run ruff format .
```

Tests use mocked providers — no real API keys required (via `tests/conftest.py`).

## Interactive documentation

With the service running, access Swagger UI at:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

> This project is part of the **Master in AI Engineering**. Estimation uses CAG; a Postgres + pgvector corpus is already in place for budgets. The next evolution is **RAG**: retrieve relevant chunks into the estimation prompt.
