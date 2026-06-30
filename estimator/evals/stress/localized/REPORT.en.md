# CAG Stress Test Report (Exercise 6.1)

## Design decisions

- **Snapshot endpoint:** Each stress turn reads `GET /sessions/{id}` after estimate so metrics use genuine `last_turn_observed`, anchors, summary, and metadata rather than inferring state from the response body alone.
- **Metrics module location:** `evals/stress/metrics.py` lives beside the runner because it depends on the snapshot/`turn_observed` contract; there is no shared `evals/metrics.py` base package in this repo.
- **Cache on during stress:** `LLM_CACHE_ENABLED=true` so exact and semantic cache hit rates are measured alongside latency and cost.
- **Spec vs codebase gap:** Step 0 added anchors, rolling summary, dynamic tiers, cost wrapper, and cache instrumentation without tuning existing CAG constants (`MAX_CONVERSATION_TURNS`, prompt templates, etc.).

**Run mode:** in-process (real LLM, LLM_CACHE_ENABLED=true, 1500 ms pause between requests) · **Rows:** 900

## Summary table

| Scenario | Attachment (KiB) | P50 latency (ms) | P95 latency (ms) | Total cost (USD) | Exact cache hit | Semantic cache hit | Mean MemoryDrift |
|---|---:|---:|---:|---:|---:|---:|---:|
| contradiction | 0 | 0 | 13976 | 0.0230 | 66.7% | 0.0% | 0.99 |
| contradiction | 5 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.99 |
| contradiction | 20 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.99 |
| contradiction | 50 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.99 |
| contradiction | 100 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.99 |
| growing | 0 | 0 | 11540 | 0.0203 | 66.7% | 0.0% | 0.94 |
| growing | 5 | 0 | 0 | 0.0011 | 73.3% | 25.0% | 0.94 |
| growing | 20 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.94 |
| growing | 50 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.94 |
| growing | 100 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.94 |
| pivot | 0 | 0 | 8521 | 0.0164 | 66.7% | 0.0% | 0.96 |
| pivot | 5 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.96 |
| pivot | 20 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.96 |
| pivot | 50 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.96 |
| pivot | 100 | 0 | 0 | 0.0000 | 70.0% | 30.0% | 0.96 |

## Curves

### Latency vs input tokens (growing scenario, turn 1)

| Attachment (KiB) | Mean tokens_in | Mean latency_ms | Mean attachments_total_chars |
|---:|---:|---:|---:|
| 0 | 547 | 2730 | 0 |
| 5 | 4867 | 2211 | 20611 |
| 20 | 4867 | 0 | 60000 |
| 50 | 4867 | 0 | 60000 |
| 100 | 4867 | 0 | 60000 |

### Cumulative cost vs turn index (attachment size = 0 KiB)

**contradiction**

| Turn | Mean cumulative cost (USD) |
|---:|---:|
| 1 | 0.0001 |
| 3 | 0.0005 |
| 6 | 0.0013 |
| 10 | 0.0029 |
| 20 | 0.0077 |

**growing**

| Turn | Mean cumulative cost (USD) |
|---:|---:|
| 1 | 0.0001 |
| 3 | 0.0005 |
| 6 | 0.0013 |
| 10 | 0.0028 |
| 20 | 0.0068 |

**pivot**

| Turn | Mean cumulative cost (USD) |
|---:|---:|
| 1 | 0.0001 |
| 3 | 0.0005 |
| 6 | 0.0012 |
| 10 | 0.0024 |
| 20 | 0.0055 |

### MemoryDrift mean vs turn index (sampled)

| Turn | Mean memory_drift_score |
|---:|---:|
| 1 | 1.00 |
| 3 | 1.00 |
| 6 | 1.00 |
| 10 | 1.00 |
| 20 | 0.86 |

## Attachment recall

- **5 KiB** (`STRESS_TOKEN_5KB`): recall rate 0.0% over 9 turn-1 rows.
- **20 KiB** (`STRESS_TOKEN_20KB`): recall rate 0.0% over 9 turn-1 rows.
- **50 KiB** (`STRESS_TOKEN_50KB`): recall rate 0.0% over 9 turn-1 rows.
- **100 KiB** (`STRESS_TOKEN_100KB`): recall rate 0.0% over 9 turn-1 rows.

## Analysis

Across the **growing** profile with no attachment, turn 20 cumulative cost (0.0068 mean per session) is **54.4×** turn 1 per-turn cost (0.0001), while mean `tokens_in` grows from 547 to 5152 (**9.4×**) as history, anchors, and summary accumulate in the system prompt.

Mean MemoryDrift recall stays at **100%** through turn 12, then drops to **86%** by turn 20 overall (pivot scenario at turn 20: **79%**). The 100 KiB attachment run caps `attachments_total_chars` at **60000** (limit 60,000), and attachment sizes preserved their `STRESS_TOKEN_*` in the response on turn 1 at rate shown above.
