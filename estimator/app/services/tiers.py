"""Dynamic tier resolution from session context size.

Maps enriched transcript length and in-window message count to a tier label,
human-readable rule, and max_tokens bonus (+0 / +1024 / +2048). The higher
tier from either dimension wins.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings

TIER_BONUSES = {"low": 0, "medium": 1024, "high": 2048}
_TIER_RANK = {"low": 0, "medium": 1, "high": 2}


@dataclass(frozen=True)
class ResolvedTier:
    """Tier label, triggering rule, and max_tokens bonus for one LLM call."""

    label: str
    rule: str
    max_tokens_bonus: int


def resolve_tier(enriched_transcript_chars: int, messages_in_window: int) -> ResolvedTier:
    """Resolve the effective tier from transcript size and message-window load."""
    settings = get_settings()
    char_tier = _tier_from_chars(enriched_transcript_chars, settings)
    message_tier = _tier_from_messages(messages_in_window, settings)
    return _pick_higher_tier(char_tier, message_tier)


def adjust_max_tokens(base_max_tokens: int, tier: ResolvedTier) -> int:
    """Return base max_tokens plus the tier bonus."""
    return base_max_tokens + tier.max_tokens_bonus


def _tier_from_chars(enriched_transcript_chars: int, settings) -> ResolvedTier:
    if enriched_transcript_chars >= settings.TIER_HIGH_CHARS:
        return ResolvedTier(
            label="high",
            rule=f"enriched_transcript_chars>={settings.TIER_HIGH_CHARS}",
            max_tokens_bonus=TIER_BONUSES["high"],
        )
    if enriched_transcript_chars >= settings.TIER_MEDIUM_CHARS:
        return ResolvedTier(
            label="medium",
            rule=f"enriched_transcript_chars>={settings.TIER_MEDIUM_CHARS}",
            max_tokens_bonus=TIER_BONUSES["medium"],
        )
    return ResolvedTier(
        label="low",
        rule=f"enriched_transcript_chars<{settings.TIER_MEDIUM_CHARS}",
        max_tokens_bonus=TIER_BONUSES["low"],
    )


def _tier_from_messages(messages_in_window: int, settings) -> ResolvedTier:
    full_window = settings.MAX_CONVERSATION_TURNS * 2
    if messages_in_window >= full_window:
        return ResolvedTier(
            label="high",
            rule=f"messages_in_window>={full_window}",
            max_tokens_bonus=TIER_BONUSES["high"],
        )
    if messages_in_window >= settings.MAX_CONVERSATION_TURNS:
        return ResolvedTier(
            label="medium",
            rule=f"messages_in_window>={settings.MAX_CONVERSATION_TURNS}",
            max_tokens_bonus=TIER_BONUSES["medium"],
        )
    return ResolvedTier(
        label="low",
        rule=f"messages_in_window<{settings.MAX_CONVERSATION_TURNS}",
        max_tokens_bonus=TIER_BONUSES["low"],
    )


def _pick_higher_tier(left: ResolvedTier, right: ResolvedTier) -> ResolvedTier:
    if _TIER_RANK[left.label] > _TIER_RANK[right.label]:
        return left
    if _TIER_RANK[right.label] > _TIER_RANK[left.label]:
        return right
    return ResolvedTier(
        label=left.label,
        rule=f"{left.rule};{right.rule}",
        max_tokens_bonus=left.max_tokens_bonus,
    )
