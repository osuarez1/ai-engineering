# Estimator architecture

Architecture notes for the FastAPI estimator service. For setup, env vars, and curl examples see [README.md](../README.md).

## Request paths

| Path | Entry | LLM / embed entrypoint | Prompt / corpus source |
|------|-------|------------------------|------------------------|
| Form API | `POST /api/v1/estimate` | `generate_estimation_from_request` | `render_estimation_prompt` (v1/v2) |
| Session API | `POST /sessions/{id}/estimate` | `run_session_estimation` → `generate_estimation_from_messages` | `render_session_system_prompt` + `render_session_user_prompt` (v2 default) |
| Session snapshot | `GET /sessions/{id}` | — (read-only) | — |
| Embedding ingest | `POST /embeddings/ingest` | `ingest_document` → `OpenAIEmbedder.embed_many` | Structural chunk text (no Jinja); persisted to Postgres |
| Semantic search | `POST /search` | `search_chunks` → `OpenAIEmbedder.embed_one` | Query string embedded; nearest chunks by cosine distance |

Both estimation paths converge on `_dispatch_llm` in `app/services/llm_service.py`, which routes a message array (system first, then user/assistant turns) to OpenAI, Anthropic, or Gemini. Ingest and search use the OpenAI embeddings API directly (`text-embedding-3-small`) and do not share the chat LLM provider abstraction. Chat sessions remain process-local (`SessionStore`); only the embedding corpus uses Postgres.

## Multi-turn session LLM message flow

Each `POST /sessions/{session_id}/estimate` call runs the pipeline below. Attachments are extracted locally (Path B) and concatenated into the transcript before orchestration begins.

```mermaid
flowchart TD
  Router["routers/sessions.py<br/>estimate_session"]
  Attach["attachments.py<br/>enrich_transcript"]
  Run["session_estimation.py<br/>run_session_estimation"]
  Build["build_session_messages"]
  Cap["cap_outgoing_messages"]
  LLM["llm_service.py<br/>generate_estimation_from_messages"]
  Dispatch["_dispatch_llm"]
  Provider["OpenAI / Anthropic / Gemini"]
  Meta["metadata_extractor.py<br/>update_metadata_heuristic"]
  History["ConversationHistory.add_turn"]

  Router --> Attach --> Run
  Run --> Build --> Cap --> LLM --> Dispatch --> Provider
  Provider --> Run
  Run --> Meta
  Run --> History
```

### Step-by-step

1. **`build_session_estimation_request`** — Maps the enriched transcript to a fixed `EstimationRequest` (web SaaS, medium detail, phases table). Uses `model_construct` so large attachment text is not capped at 2000 characters.

2. **`build_session_messages`** — Assembles the outgoing payload:
   - Regenerates the **system prompt** from current `project_metadata` via `render_session_system_prompt` and `_project_metadata.j2`.
   - Prepends prior turns from `ConversationHistory.to_messages_list(system_prompt)`.
   - Appends the **current user message** from `render_session_user_prompt` (not stored in history until after the LLM responds).

3. **`cap_outgoing_messages`** — Trims the oldest user/assistant pairs so non-system content sent to the LLM respects `MAX_CONVERSATION_TURNS` (default `6`). The current user message counts toward the cap. Orphan leading assistant messages (not a full pair) are dropped one at a time.

4. **`generate_estimation_from_messages`** — Public LLM entrypoint for any multi-turn array. Logs `message_count` and `history_turns`, then calls `_dispatch_llm`.

5. **`_dispatch_llm`** — Splits system from turns (`_split_system_and_turns`) and dispatches:
   - **OpenAI** — full message array (system + turns).
   - **Anthropic** — `system` parameter plus `messages` turn list.
   - **Gemini** — `system_instruction` plus mapped turn contents.

6. **Post-turn memory** — `update_metadata_heuristic` refreshes `project_metadata`; `history.add_turn` stores the **rendered user prompt** (including attachment blocks) and the assistant estimation. `ConversationHistory._trim` enforces the same window limit in stored history.

### Sliding window: two layers

| Layer | Where | What it limits |
|-------|-------|----------------|
| Stored history | `ConversationHistory._trim` | User/assistant pairs kept in the in-memory session |
| Outgoing LLM payload | `cap_outgoing_messages` | Non-system messages sent on each API call |

Both use `MAX_CONVERSATION_TURNS * 2` message slots. Facts that must survive truncation live in `project_metadata`, which is re-injected into the system prompt every turn.

### Single-turn convenience

`generate_session_estimation` builds a two-message array (system + user) and delegates to `generate_estimation_from_messages`. Session orchestration uses the message-array API directly so prior turns are included.

## Provider abstraction

All provider wrappers return the same dict shape (`estimation`, `model`, `provider`, `finish_reason`, `usage`). `generate_estimation_from_messages` maps `estimation` → `text` for the session and form API contracts.

`thinking_budget` is honored only for Anthropic; OpenAI and Gemini log a warning and ignore it.

## Session state

Sessions live in a process-local `SessionStore` (no database). Each `Session` holds:

- `ConversationHistory` — user/assistant turns only; system prompt is never stored.
- `ProjectMetadata` — distilled facts updated heuristically after each turn.
- `session_id`, `created_at`, `updated_at`.

Restarting the process clears all sessions.

## Session snapshot and observation

`GET /sessions/{session_id}` returns a `SessionSnapshotResponse` for stress-test observation and debugging. Fields:

| Field | Description |
|-------|-------------|
| `session_id` | Session identifier |
| `message_count` | Stored user/assistant turns in history |
| `anchors_count` / `anchors` | Promoted facts retained across window truncation |
| `summary_chars` / `summary` | Rolling cumulative summary (capped at 2000 chars) |
| `last_resolved_tier` / `last_tier_rule` | Dynamic prompt tier from enriched transcript size |
| `project_metadata` | Heuristic facts (name, stack, team, scope) |
| `last_turn_observed` | Per-turn bundle from the most recent estimate (see below) |

At the end of each `run_session_estimation` call, the service populates `session.last_turn_observed` with tokens, cost, latency, cache hit kind, window size, and attachment stats, then logs a `turn_observed` structlog event with the same payload. The stress runner (`evals/stress/run.py`) reads the snapshot after every estimate turn so metrics use genuine server state rather than inferring from the response body alone.

## CAG memory stack (session path)

Beyond the sliding-window history and heuristic `project_metadata`, the session path maintains additional context injected into the system prompt each turn:

| Component | Module | Role |
|-----------|--------|------|
| Anchors | `anchor_extractor.py` | Promotes durable facts from turns so they survive history truncation |
| Summary | `summarizer.py` | Rolling cumulative summary, capped at 2000 characters |
| Tiers | `tiers.py` | Selects prompt detail level (`low` / `medium` / `high`) from enriched transcript size vs `TIER_MEDIUM_CHARS` / `TIER_HIGH_CHARS` |
| Metadata | `metadata_extractor.py` | Heuristic `project_metadata` update after each turn (see README) |

Facts that must survive window truncation live in anchors, summary, and `project_metadata`, all re-injected via Jinja partials (`_anchors.j2`, `_summary.j2`, `_project_metadata.j2`) on every LLM call.

## LLM instrumentation

**Cost tracking** — `llm_wrapper.compute_cost_usd` uses the `MODEL_COSTS` table keyed by model id (prefix-matched for versioned ids). Each provider wrapper records `tokens_in`, `tokens_out`, `latency_ms`, and `cost_usd` in the returned usage dict.

**Response cache** — `llm_cache.py` provides exact and semantic cache lookup before dispatching to the provider. Controlled by `LLM_CACHE_ENABLED` (default `true`) and `SEMANTIC_CACHE_THRESHOLD` (default `0.85`). Cache hit kind (`none` / `exact` / `semantic`) is included in `last_turn_observed`.

## Stress evaluation pipeline

Exercise 6.1 adds `evals/stress/` — a CLI harness that drives the session API through synthetic multi-turn scenarios with optional PDF attachments.

```mermaid
flowchart LR
  Run["evals/stress/run.py"]
  API["Session API"]
  Snap["GET /sessions/id"]
  CSV["results.csv"]
  Agg["evals/stress/aggregate.py"]
  Report["REPORT.md"]

  Run -->|"POST estimate per turn"| API
  Run --> Snap
  Snap --> Run
  Run --> CSV
  CSV --> Agg --> Report
```

- **Transport** — in-process (`TestClient`, default) or `--http` against a running API.
- **Scenarios** — `evals/stress/scenarios.py` defines `growing`, `pivot`, and `contradiction` profiles with fact-trackers for memory-drift measurement.
- **Metrics** — `evals/stress/metrics.py` consumes snapshot data and scenario trackers (`MemoryDriftMetric`, latency/cost budgets, attachment recall).
- **Aggregation** — `evals/stress/aggregate.py` reads `results.csv`, writes `localized/REPORT.en.md` and `localized/REPORT.es.md`, and copies the Spanish report to `REPORT.md` for the temporary course publish path.

Mocked runs patch `generate_estimation_from_messages` for fast CI; `--real-llm --cache-on` exercises the full stack including cache hit rates.

## Clients

### Streamlit (`streamlit_app.py`)

The Session 5 UI is an **HTTP client only** — it does not import `llm_service` or call providers directly. FastAPI must be running separately (default `http://localhost:8000`).

```mermaid
flowchart LR
  UI["streamlit_app.py"]
  Helpers["streamlit_helpers.py"]
  API["FastAPI session routes"]
  Orch["session_estimation.py"]

  UI --> Helpers
  Helpers -->|"POST /sessions"| API
  Helpers -->|"POST /sessions/{id}/estimate"| API
  API --> Orch
```

| UI action | HTTP call | Local state updated |
|-----------|-----------|---------------------|
| Page load / bootstrap | `POST /sessions` via `ensure_session_id` | `session_id` |
| **Estimate** | `POST /sessions/{id}/estimate` (multipart: transcript + optional PDF/DOCX) | `last_estimation`, `project_metadata` |
| **New conversation** | `POST /sessions` via `reset_conversation_state` | New `session_id`; clears `project_metadata` and `last_estimation` |

Pure HTTP and validation logic lives in `app/ui/streamlit_helpers.py` (no Streamlit imports) so behaviour is unit-testable without AppTest. The sidebar displays `project_metadata` returned by the API — memory the server maintains across turns, distinct from the transcript the user types each time.

The legacy Session 4 form client (`POST /api/v1/estimate`) is no longer exposed in Streamlit; the form API path remains available for curl, tests, and other HTTP clients.

## Persistence layer (Postgres + pgvector)

Session 08 adds a dedicated DB stack for the embedding corpus. Migrations are Alembic-managed (`estimator/alembic/`); runtime access is async SQLAlchemy 2.0 via `asyncpg`.

| Piece | Location | Role |
|-------|----------|------|
| Settings | `config.py` → `DATABASE_URL` | Default `postgresql+asyncpg://…@localhost:5432/estimator`; Compose overrides host to `postgres` |
| Engine / sessions | `app/db/session.py` | `create_async_engine`, `AsyncSessionLocal`, `get_session` dependency helper |
| ORM | `app/db/models.py` | `Document`, `Chunk` (`metadata_` → column `metadata`); `EMBEDDING_DIMENSION = 1536` |
| Migration | `alembic/versions/0001_initial_schema.py` | `CREATE EXTENSION vector`; tables + non-vector indexes; **no** HNSW/IVFFlat |

### Schema

```mermaid
erDiagram
  documents ||--o{ chunks : "CASCADE"
  documents {
    bigint id PK
    text source_path
    varchar document_type
    timestamptz ingested_at
    jsonb metadata
  }
  chunks {
    bigint id PK
    bigint document_id FK
    varchar chunk_type
    text content
    vector_1536 embedding
    jsonb metadata
    timestamptz created_at
  }
```

- **`documents`** — One row per ingested estimate (`source_path` uniqueness checked in the ingest service; indexed for lookup). Document-level JSONB holds budget_id, sector, year, technology, total hours.
- **`chunks`** — One row per budget component (`chunk_type = budget_component`). Embedding is `vector(1536)` (nullable until filled). Chunk JSONB carries filterable fields from the Session 07 chunker. Indexes: `document_id`, `chunk_type`, GIN on `metadata`. Distance search uses sequential scan today (live-session baseline).

Compose: `postgres` service (`pgvector/pgvector:pg16`) with healthcheck; `estimator` waits until healthy and receives `DATABASE_URL` pointing at that service.

## Embedding pipeline

Session 07 introduced structural chunking + OpenAI embeddings. Session 08 persists each ingest in a single transaction and exposes cosine-distance search over stored chunks.

```mermaid
flowchart LR
  subgraph ingestFlow [POST /embeddings/ingest]
    IReq["source_path + document_type + content"]
    ISvc["ingest_service.ingest_document"]
    Chunker["JSONStructuralChunker"]
    EmbedMany["OpenAIEmbedder.embed_many"]
    IReq --> ISvc --> Chunker --> EmbedMany
    EmbedMany --> ISvc
  end
  subgraph searchFlow [POST /search]
    SReq["query + k"]
    SSvc["search_service.search_chunks"]
    EmbedOne["OpenAIEmbedder.embed_one"]
    SReq --> SSvc --> EmbedOne
    EmbedOne --> SSvc
  end
  PG[("Postgres 16 + pgvector")]
  ISvc --> PG
  SSvc --> PG
```

### Ingest flow (`POST /embeddings/ingest`)

Router: `embedding_pipeline/router.py` → `ingest_document` in `ingest_service.py`.

1. **`IngestRequest`** — `{source_path, document_type, content}` where `content` is one `Budget` (sample corpus: `data/budgets_sample.json`).
2. **Duplicate check** — If `source_path` already exists, raise `DocumentAlreadyIngestedError` → HTTP **409** `{detail, document_id}`.
3. **Insert `Document`** — JSONB metadata derived from the budget; still uncommitted.
4. **`JSONStructuralChunker.chunk`** — One `BudgetComponent` → one in-memory chunk. Parent proposal context is prepended to component text; metadata stays filterable and separate from embedded text.
5. **`OpenAIEmbedder.embed_many`** — Sync client invoked via `run_in_executor` so the event loop is not blocked. Batches up to 100; rate-limit retries with backoff.
6. **`session.add_all` chunk rows** — `chunk_type="budget_component"`, vectors written to `embedding`, then **commit**. Any failure before commit rolls back (no orphan document).
7. **`IngestResponse`** — `{document_id, chunks_created, embedding_dimension, ingestion_time_ms}`.

Other embedding API failures map to HTTP 500 with a generic message.

### Search flow (`POST /search`)

Router: `embedding_pipeline/search_router.py` → `search_chunks` in `search_service.py`.

1. **`SearchRequest`** — `{query, k}` (`k` default 5, bounded in the schema).
2. **`OpenAIEmbedder.embed_one`** — Same model as ingest (`run_in_executor`).
3. **SQL** — `ORDER BY Chunk.embedding.cosine_distance(query_vector) LIMIT k` (pgvector `<=>`). No vector ANN index; sequential scan is expected at current corpus size.
4. **`SearchResponse`** — `{query, k, search_time_ms, results[]}` with `chunk_id`, `document_id`, `chunk_type`, `content`, `distance`, `metadata`.

### Corpus helpers

| Script | Role |
|--------|------|
| `scripts/ingest_examples.py` | POSTs all 15 sample budgets with `source_path` like `data/budgets_sample.json#BUD-…` (409 treated as already loaded) |
| `query_examples.py` | Five query archetypes against `POST /search`; sample capture in `output_examples.txt` |

### Module map

| Module | Role |
|--------|------|
| `app/db/models.py` | ORM `Document` / `Chunk`; vector dimension constant |
| `app/db/session.py` | Async engine and session factory |
| `schemas.py` | `Budget`, chunk DTOs, `IngestRequest`/`IngestResponse`, `SearchRequest`/`SearchResponse` |
| `chunker.py` | Structural JSON chunking; `tiktoken` token counts |
| `embedder.py` | OpenAI `text-embedding-3-small`; batching and cost constant |
| `ingest_service.py` | Transactional persist (duplicate 409, batch embed, commit/rollback) |
| `router.py` | FastAPI `POST /embeddings/ingest` |
| `search_service.py` | Embed query + cosine-distance select |
| `search_router.py` | FastAPI `POST /search` |
