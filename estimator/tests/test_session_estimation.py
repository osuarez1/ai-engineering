import pytest

from app.config import get_settings
from app.schemas.request_form import DetailLevel, OutputFormat, ProjectType
from app.services.session_estimation import (
    build_session_estimation_request,
    build_session_messages,
    cap_outgoing_messages,
    run_session_estimation,
)
from app.sessions import ProjectMetadata, Session


def test_build_session_estimation_request_uses_defaults() -> None:
    transcript = "x" * 50
    request = build_session_estimation_request(transcript)
    assert request.description == transcript
    assert request.project_type == ProjectType.WEB_SAAS
    assert request.detail_level == DetailLevel.MEDIUM
    assert request.output_format == OutputFormat.PHASES_TABLE
    assert request.reference_projects is None


def test_build_session_messages_includes_prior_history() -> None:
    session = Session()
    session.history.add_turn("first turn text here", "first reply")
    session.project_metadata = ProjectMetadata(project_name="BookFlow")

    messages = build_session_messages(
        session,
        "second turn with enough length for validation",
        version="v2",
    )

    assert messages[0]["role"] == "system"
    assert "Project name: BookFlow" in messages[0]["content"]
    assert messages[1] == {"role": "user", "content": "first turn text here"}
    assert messages[2] == {"role": "assistant", "content": "first reply"}
    assert messages[-1]["role"] == "user"
    assert "second turn" in messages[-1]["content"]


def test_cap_outgoing_messages_trims_oldest_pairs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_CONVERSATION_TURNS", "2")
    get_settings.cache_clear()

    messages = [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "u3"},
    ]
    capped = cap_outgoing_messages(messages)
    assert capped[1:] == [
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "u3"},
    ]
    get_settings.cache_clear()


def test_cap_outgoing_messages_drops_leading_orphan_when_not_a_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAX_CONVERSATION_TURNS", "1")
    get_settings.cache_clear()

    messages = [
        {"role": "system", "content": "system"},
        {"role": "assistant", "content": "orphan"},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
    ]
    capped = cap_outgoing_messages(messages)
    assert capped == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "u2"},
    ]
    get_settings.cache_clear()


def test_cap_outgoing_messages_returns_unchanged_without_system() -> None:
    messages = [{"role": "user", "content": "only user"}]
    assert cap_outgoing_messages(messages) == messages


def test_run_session_estimation_appends_history_and_updates_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Session()
    captured: list[list[dict[str, str]]] = []

    def fake_generate(messages, *, version: str = "v2", opts=None) -> dict:
        captured.append(messages)
        return {"text": "estimate body", "prompt_version": "v2"}

    monkeypatch.setattr(
        "app.services.session_estimation.generate_estimation_from_messages",
        fake_generate,
    )

    transcript = "The project is called BookFlow and we will use Rails and React."
    result = run_session_estimation(session, transcript, version="v2")

    assert result["text"] == "estimate body"
    assert len(session.history.messages) == 2
    assert "BookFlow" in session.history.messages[0].content
    assert session.project_metadata.project_name == "BookFlow"
    assert len(captured) == 1
    assert captured[0][0]["role"] == "system"
    assert "BookFlow" in captured[0][-1]["content"]
