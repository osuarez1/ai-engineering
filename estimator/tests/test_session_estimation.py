import pytest

from app.schemas.request_form import DetailLevel, OutputFormat, ProjectType
from app.services.session_estimation import build_session_estimation_request, run_session_estimation
from app.sessions import Session


def test_build_session_estimation_request_uses_defaults() -> None:
    transcript = "x" * 50
    request = build_session_estimation_request(transcript)
    assert request.description == transcript
    assert request.project_type == ProjectType.WEB_SAAS
    assert request.detail_level == DetailLevel.MEDIUM
    assert request.output_format == OutputFormat.PHASES_TABLE
    assert request.reference_projects is None


def test_run_session_estimation_appends_history_and_updates_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = Session()

    def fake_generate(*args, **kwargs) -> dict:
        return {"text": "estimate body", "prompt_version": "v2"}

    monkeypatch.setattr(
        "app.services.session_estimation.generate_session_estimation",
        fake_generate,
    )

    transcript = "The project is called BookFlow and we will use Rails and React."
    result = run_session_estimation(session, transcript, version="v2")

    assert result["text"] == "estimate body"
    assert len(session.history.messages) == 2
    assert session.history.messages[0].content == transcript
    assert session.project_metadata.project_name == "BookFlow"
    assert "Rails" in session.project_metadata.mentioned_technologies
