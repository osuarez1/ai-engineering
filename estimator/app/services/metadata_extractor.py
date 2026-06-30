"""Heuristic extraction of project facts from conversational turns.

Updates ``ProjectMetadata`` after each user/assistant exchange without an extra LLM
call. Chosen for zero added latency/cost and predictable, debuggable behaviour in
this exercise phase.
"""

from __future__ import annotations

import re

from app.sessions import ProjectMetadata

KNOWN_TECHNOLOGIES: dict[str, str] = {
    "rails": "Rails",
    "ruby on rails": "Rails",
    "react": "React",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "redis": "Redis",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "node": "Node.js",
    "python": "Python",
    "django": "Django",
    "fastapi": "FastAPI",
    "vue": "Vue",
    "angular": "Angular",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "kubernetes": "Kubernetes",
    "docker": "Docker",
    "aws": "AWS",
    "gcp": "GCP",
    "azure": "Azure",
    "mongodb": "MongoDB",
    "mysql": "MySQL",
    "graphql": "GraphQL",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "flutter": "Flutter",
}

_PROJECT_NAME_PATTERNS = (
    re.compile(
        r"project\s+(?:is\s+)?(?:called|named)\s+['\"]?([A-Za-z0-9][A-Za-z0-9\-]*?)['\"]?"
        r"(?:\s+and\b|\s+with\b|[,.]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:we(?:'re| are)\s+(?:building|calling(?:\s+it)?))\s+['\"]?([A-Za-z0-9][A-Za-z0-9\-]*?)['\"]?"
        r"(?:\s+and\b|\s+with\b|[,.]|$)",
        re.IGNORECASE,
    ),
)

_TEAM_SIZE_PATTERN = re.compile(
    r"(\d+)\s+(?:full[- ]time\s+)?(?:engineers?|developers?|people|person(?:\s+team)?)",
    re.IGNORECASE,
)

_SCOPE_PATTERN = re.compile(
    r"(?:agreed scope|scope is|mvp includes)[: ]+(.{20,200}?)(?:\.|$)",
    re.IGNORECASE,
)

_BUDGET_EUR_PATTERN = re.compile(r"budget\s+(\d[\d,.\s]*)\s*EUR", re.IGNORECASE)


def update_metadata_heuristic(
    metadata: ProjectMetadata,
    user_turn: str,
    assistant_turn: str,
) -> ProjectMetadata:
    """Return updated metadata incorporating facts from the latest turn."""
    combined = f"{user_turn}\n{assistant_turn}"
    lowered = combined.lower()
    updates: dict[str, object] = {}

    if metadata.project_name is None:
        for pattern in _PROJECT_NAME_PATTERNS:
            match = pattern.search(combined)
            if match:
                updates["project_name"] = _clean_capture(match.group(1))
                break

    if metadata.assumed_team_size is None:
        team_match = _TEAM_SIZE_PATTERN.search(combined)
        if team_match:
            updates["assumed_team_size"] = int(team_match.group(1))

    found_technologies = _find_technologies(lowered)
    if found_technologies:
        merged = sorted(set(metadata.mentioned_technologies) | found_technologies)
        updates["mentioned_technologies"] = merged

    if metadata.agreed_scope is None:
        scope_match = _SCOPE_PATTERN.search(combined)
        if scope_match:
            updates["agreed_scope"] = scope_match.group(1).strip()

    budget_match = _BUDGET_EUR_PATTERN.search(combined)
    if budget_match:
        updates["budget_eur"] = _parse_budget_eur(budget_match.group(1))

    if not updates:
        return metadata
    return metadata.model_copy(update=updates)


def _clean_capture(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip(" .,:;-")


def _parse_budget_eur(raw: str) -> int:
    normalized = raw.replace(",", "").replace(" ", "").split(".", maxsplit=1)[0]
    return int(normalized)


def _find_technologies(lowered_text: str) -> set[str]:
    found: set[str] = set()
    for needle, canonical in sorted(KNOWN_TECHNOLOGIES.items(), key=lambda item: -len(item[0])):
        if needle in lowered_text:
            found.add(canonical)
    return found
