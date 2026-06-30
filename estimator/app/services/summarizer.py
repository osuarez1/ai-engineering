"""Deterministic rolling summary for multi-turn session memory."""

from __future__ import annotations

MAX_SUMMARY_CHARS = 2000
_MAX_TURN_SNIPPET_CHARS = 400


def update_summary(
    prior_summary: str,
    user_turn: str,
    assistant_turn: str,
    *,
    max_chars: int = MAX_SUMMARY_CHARS,
) -> str:
    """Append a turn snippet to the prior summary and cap total length."""
    snippet = _turn_snippet(user_turn, assistant_turn)
    if prior_summary:
        combined = f"{prior_summary}\n{snippet}"
    else:
        combined = snippet
    if len(combined) <= max_chars:
        return combined
    return combined[-max_chars:]


def _turn_snippet(user_turn: str, assistant_turn: str) -> str:
    user_part = user_turn.strip()
    if len(user_part) > _MAX_TURN_SNIPPET_CHARS:
        user_part = user_part[:_MAX_TURN_SNIPPET_CHARS] + "..."

    assistant_part = assistant_turn.strip()
    if len(assistant_part) > _MAX_TURN_SNIPPET_CHARS:
        assistant_part = assistant_part[:_MAX_TURN_SNIPPET_CHARS] + "..."

    return f"User: {user_part}\nAssistant: {assistant_part}"
