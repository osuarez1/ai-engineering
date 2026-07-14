# Embedding Sanity Check

Archived Session 07 pairwise cosine similarity results for `text-embedding-3-small`. The compare CLI that produced them was removed in Session 08; live corpus validation is `query_examples.py` / `POST /search`.

## Pair A — Semantically close (expected roughly > 0.6)

| Text A | OAuth 2.0 authentication backend with JWT tokens for fintech mobile app |
| Text B | Authorization service using JSON Web Tokens for a banking application |
| **Cosine similarity** | **0.5957** |

## Pair B — Unrelated (expected roughly < 0.4)

| Text A | OAuth 2.0 authentication backend with JWT tokens for fintech mobile app |
| Text B | Database migration from MySQL to PostgreSQL with zero downtime |
| **Cosine similarity** | **0.1920** |

## Pair C — Generic and ambiguous (no fixed expectation)

| Text A | Backend services |
| Text B | API development |
| **Cosine similarity** | **0.5407** |

## Commentary

The pipeline discriminates well between close and distant texts: Pair A scores far above Pair B, confirming that embeddings capture semantic overlap even when wording differs (OAuth/JWT vs authorization/JSON Web Tokens). Pair A lands just under the 0.6 guideline (0.5957), which is close enough to validate the model for this domain but worth discussing as a threshold calibration topic. Pair B at 0.19 clearly separates unrelated infrastructure topics from authentication. Pair C is the surprise: two vague phrases still score 0.54, showing that generic backend vocabulary collapses into a broad cluster — useful retrieval would need richer chunks or metadata filters, not just raw similarity on short queries.
