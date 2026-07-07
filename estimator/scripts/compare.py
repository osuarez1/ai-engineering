#!/usr/bin/env python3
"""Compare cosine similarity between two texts using OpenAI embeddings."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.embedding_pipeline.compare_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
