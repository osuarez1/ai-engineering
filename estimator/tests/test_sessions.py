import pytest

from app.config import get_settings
from app.sessions import (
    ConversationHistory,
    ProjectMetadata,
    Session,
    SessionNotFoundError,
    SessionStore,
    session_store,
)


def test_project_metadata_defaults() -> None:
    metadata = ProjectMetadata()
    assert metadata.project_name is None
    assert metadata.assumed_team_size is None
    assert metadata.mentioned_technologies == []
    assert metadata.agreed_scope is None
    assert metadata.budget_eur is None


def test_conversation_history_to_messages_list_prepends_system() -> None:
    history = ConversationHistory()
    history.add_turn("estimate this", "here is the estimate")

    messages = history.to_messages_list("system context")

    assert messages[0] == {"role": "system", "content": "system context"}
    assert messages[1:] == [
        {"role": "user", "content": "estimate this"},
        {"role": "assistant", "content": "here is the estimate"},
    ]


def test_conversation_history_sliding_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_CONVERSATION_TURNS", "2")
    get_settings.cache_clear()

    history = ConversationHistory()
    history.add_turn("turn 1", "reply 1")
    history.add_turn("turn 2", "reply 2")
    history.add_turn("turn 3", "reply 3")

    assert [message.content for message in history.messages] == [
        "turn 2",
        "reply 2",
        "turn 3",
        "reply 3",
    ]

    get_settings.cache_clear()


def test_conversation_history_keeps_all_pairs_at_exact_window_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_CONVERSATION_TURNS", "2")
    get_settings.cache_clear()

    history = ConversationHistory()
    history.add_turn("turn 1", "reply 1")
    history.add_turn("turn 2", "reply 2")

    assert [message.content for message in history.messages] == [
        "turn 1",
        "reply 1",
        "turn 2",
        "reply 2",
    ]

    get_settings.cache_clear()


def test_conversation_history_to_messages_list_without_prior_turns() -> None:
    history = ConversationHistory()
    messages = history.to_messages_list("system context")
    assert messages == [{"role": "system", "content": "system context"}]


def test_session_store_create_and_get() -> None:
    store = SessionStore()
    session = store.create()

    assert store.get(session.session_id) is session
    assert store.get("missing-id") is None


def test_session_store_get_or_raise() -> None:
    store = SessionStore()
    session = store.create()

    assert store.get_or_raise(session.session_id) is session

    with pytest.raises(SessionNotFoundError):
        store.get_or_raise("does-not-exist")


def test_session_touch_updates_timestamp() -> None:
    session = Session()
    before = session.updated_at
    session.touch()
    assert session.updated_at >= before


def test_session_memory_fields_default_empty() -> None:
    session = Session()
    assert session.anchors == []
    assert session.summary == ""
    assert session.turn_index == 0
    assert session.last_resolved_tier == ""
    assert session.last_tier_rule == ""
    assert session.last_turn_observed is None


def test_session_memory_fields_are_mutable() -> None:
    session = Session()
    session.anchors.append("budget 30000 EUR")
    session.summary = "CRM with auth and roles."
    session.turn_index = 3
    session.last_resolved_tier = "medium"
    session.last_tier_rule = "enriched_transcript_chars>=8000"
    session.last_turn_observed = {"turn_index": 3, "cost_usd": 0.01}

    assert session.anchors == ["budget 30000 EUR"]
    assert session.summary == "CRM with auth and roles."
    assert session.turn_index == 3
    assert session.last_resolved_tier == "medium"
    assert session.last_tier_rule == "enriched_transcript_chars>=8000"
    assert session.last_turn_observed == {"turn_index": 3, "cost_usd": 0.01}


def test_module_level_session_store_is_singleton() -> None:
    assert isinstance(session_store, SessionStore)
