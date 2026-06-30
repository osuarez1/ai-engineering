from types import SimpleNamespace

import pytest

from app.services import tiers
from app.services.tiers import ResolvedTier, adjust_max_tokens, resolve_tier


@pytest.fixture
def tier_settings(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    settings = SimpleNamespace(
        TIER_MEDIUM_CHARS=8_000,
        TIER_HIGH_CHARS=20_000,
        MAX_CONVERSATION_TURNS=6,
    )
    monkeypatch.setattr(tiers, "get_settings", lambda: settings)
    return settings


def test_resolve_tier_low_for_small_context(tier_settings: SimpleNamespace) -> None:
    tier = resolve_tier(100, 1)
    assert tier == ResolvedTier(
        label="low",
        rule="enriched_transcript_chars<8000;messages_in_window<6",
        max_tokens_bonus=0,
    )


def test_resolve_tier_medium_from_transcript_chars(tier_settings: SimpleNamespace) -> None:
    tier = resolve_tier(10_000, 1)
    assert tier.label == "medium"
    assert tier.max_tokens_bonus == 1024
    assert tier.rule == "enriched_transcript_chars>=8000"


def test_resolve_tier_high_from_transcript_chars(tier_settings: SimpleNamespace) -> None:
    tier = resolve_tier(25_000, 1)
    assert tier == ResolvedTier(
        label="high",
        rule="enriched_transcript_chars>=20000",
        max_tokens_bonus=2048,
    )


def test_resolve_tier_medium_from_message_window(tier_settings: SimpleNamespace) -> None:
    tier = resolve_tier(100, 6)
    assert tier == ResolvedTier(
        label="medium",
        rule="messages_in_window>=6",
        max_tokens_bonus=1024,
    )


def test_resolve_tier_combines_rules_when_both_dimensions_are_medium(
    tier_settings: SimpleNamespace,
) -> None:
    tier = resolve_tier(10_000, 6)
    assert tier.label == "medium"
    assert tier.max_tokens_bonus == 1024
    assert tier.rule == "enriched_transcript_chars>=8000;messages_in_window>=6"


def test_resolve_tier_high_from_full_message_window(tier_settings: SimpleNamespace) -> None:
    tier = resolve_tier(100, 12)
    assert tier == ResolvedTier(
        label="high",
        rule="messages_in_window>=12",
        max_tokens_bonus=2048,
    )


def test_resolve_tier_picks_higher_dimension(tier_settings: SimpleNamespace) -> None:
    tier = resolve_tier(25_000, 1)
    assert tier.label == "high"
    tier = resolve_tier(100, 12)
    assert tier.label == "high"


def test_adjust_max_tokens_applies_bonus() -> None:
    tier = ResolvedTier(label="medium", rule="test", max_tokens_bonus=1024)
    assert adjust_max_tokens(4000, tier) == 5024
