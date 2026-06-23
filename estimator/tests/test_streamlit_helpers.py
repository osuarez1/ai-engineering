from unittest.mock import MagicMock

import httpx
import pytest

from app.sessions import ProjectMetadata
from app.ui import streamlit_helpers


def test_initial_session_state() -> None:
    state = streamlit_helpers.initial_session_state()
    assert state["session_id"] is None
    assert state["project_metadata"] == streamlit_helpers.empty_project_metadata()
    assert state["prompt_version"] == "v2"
    assert state["last_estimation"] is None


def test_validate_transcript_rejects_short_text() -> None:
    assert streamlit_helpers.validate_transcript("too short") is not None


def test_validate_transcript_accepts_long_enough_text() -> None:
    assert streamlit_helpers.validate_transcript("x" * 20) is None


def test_create_session_returns_session_id() -> None:
    def fake_post(url: str, **kwargs) -> httpx.Response:
        return httpx.Response(
            200,
            json={"session_id": "abc-123"},
            request=httpx.Request("POST", url),
        )

    session_id = streamlit_helpers.create_session(post=fake_post)
    assert session_id == "abc-123"


def test_submit_session_estimate_multipart() -> None:
    posted: list[dict] = []

    def fake_post(url: str, **kwargs) -> httpx.Response:
        posted.append({"url": url, **kwargs})
        return httpx.Response(
            200,
            json={
                "text": "## Estimate",
                "prompt_version": "v2",
                "project_metadata": ProjectMetadata(project_name="BookFlow").model_dump(),
            },
            request=httpx.Request("POST", url),
        )

    result = streamlit_helpers.submit_session_estimate(
        "abc-123",
        "We need a CRM with auth, contacts and roles.",
        [("spec.docx", b"doc-bytes", "application/vnd.openxmlformats")],
        post=fake_post,
    )

    assert result.text == "## Estimate"
    assert result.project_metadata.project_name == "BookFlow"
    assert posted[0]["url"].endswith("/sessions/abc-123/estimate")
    assert posted[0]["data"] == {
        "transcript": "We need a CRM with auth, contacts and roles.",
    }
    assert posted[0]["files"][0][0] == "attachments"


def test_submit_session_estimate_without_attachments() -> None:
    posted: list[dict] = []

    def fake_post(url: str, **kwargs) -> httpx.Response:
        posted.append(kwargs)
        return httpx.Response(
            200,
            json={
                "text": "## Estimate",
                "prompt_version": "v2",
                "project_metadata": {},
            },
            request=httpx.Request("POST", url),
        )

    streamlit_helpers.submit_session_estimate(
        "abc-123",
        "We need a CRM with auth, contacts and roles.",
        [],
        post=fake_post,
    )
    assert "files" not in posted[0]


def test_prepare_attachment_payloads_skips_unnamed_files() -> None:
    upload = MagicMock()
    upload.name = ""
    upload.getvalue.return_value = b"ignored"
    upload.type = "application/pdf"
    assert streamlit_helpers.prepare_attachment_payloads([upload]) == []


def test_prepare_attachment_payloads_normalises_uploads() -> None:
    upload = MagicMock()
    upload.name = "spec.pdf"
    upload.getvalue.return_value = b"%PDF"
    upload.type = None
    assert streamlit_helpers.prepare_attachment_payloads([upload]) == [
        ("spec.pdf", b"%PDF", "application/octet-stream")
    ]


def test_ensure_session_id_creates_once() -> None:
    state: dict = {}
    session_id = streamlit_helpers.ensure_session_id(
        state,
        create_session_fn=lambda _api_base: "session-1",
    )
    assert session_id == "session-1"
    assert state["session_id"] == "session-1"
    assert streamlit_helpers.ensure_session_id(
        state,
        create_session_fn=lambda _api_base: "session-2",
    ) == "session-1"


def test_reset_conversation_state_clears_local_memory() -> None:
    state = {
        "session_id": "old",
        "project_metadata": {"project_name": "BookFlow"},
        "last_estimation": "saved",
    }
    new_id = streamlit_helpers.reset_conversation_state(
        state,
        create_session_fn=lambda _api_base: "new-session",
    )
    assert new_id == "new-session"
    assert state["project_metadata"]["project_name"] is None
    assert state["last_estimation"] is None
