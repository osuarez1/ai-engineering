"""Heuristic extraction of pinned facts (anchors) from conversational turns.

Anchors survive history truncation and are checked by stress-test memory-drift
metrics. Budget statements, locked decisions, and project names are captured
as literal phrases where possible.
"""

from __future__ import annotations

import re

from app.sessions import ProjectMetadata

_BUDGET_PATTERN = re.compile(r"(budget\s+\d[\d,.\s]*\s*EUR)", re.IGNORECASE)

_PROJECT_NAME_PATTERN = re.compile(
    r"project\s+is\s+called\s+['\"]?([A-Za-z0-9][A-Za-z0-9\-]*)['\"]?",
    re.IGNORECASE,
)

_LOCKED_DECISION_PATTERN = re.compile(
    r"(?:locked(?:\s+decision)?|firm decision):\s*(.{5,120}?)(?:[,.]|$)",
    re.IGNORECASE,
)

_SWITCHING_PATTERN = re.compile(
    r"(switching to\s+[A-Za-z0-9][A-Za-z0-9 .]*)",
    re.IGNORECASE,
)


def extract_anchors_from_turn(
    user_turn: str,
    assistant_turn: str,
    metadata: ProjectMetadata,
) -> list[str]:
    """Return new anchor strings found in the latest user/assistant exchange."""
    combined = f"{user_turn}\n{assistant_turn}"
    anchors: list[str] = []

    for match in _BUDGET_PATTERN.finditer(combined):
        anchors.append(_normalize_whitespace(match.group(1)))

    project_match = _PROJECT_NAME_PATTERN.search(combined)
    if project_match:
        name = project_match.group(1)
        anchors.append(f"project is called {name}")
    elif metadata.project_name:
        anchors.append(f"project is called {metadata.project_name}")

    locked_match = _LOCKED_DECISION_PATTERN.search(combined)
    if locked_match:
        anchors.append(f"locked decision: {locked_match.group(1).strip()}")

    switching_match = _SWITCHING_PATTERN.search(combined)
    if switching_match:
        anchors.append(_normalize_whitespace(switching_match.group(1)))

    return anchors


def update_anchors(
    existing: list[str],
    user_turn: str,
    assistant_turn: str,
    metadata: ProjectMetadata,
) -> list[str]:
    """Merge newly extracted anchors into the session list (case-insensitive dedupe)."""
    new_anchors = extract_anchors_from_turn(user_turn, assistant_turn, metadata)
    seen = {anchor.casefold() for anchor in existing}
    merged = list(existing)
    for anchor in new_anchors:
        key = anchor.casefold()
        if key not in seen:
            merged.append(anchor)
            seen.add(key)
    return merged


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .,:;-")
