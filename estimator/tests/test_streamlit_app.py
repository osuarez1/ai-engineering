from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from streamlit.testing.v1 import AppTest

import streamlit_app as estimator_ui
from app.schemas.session import SessionEstimationResponse
from app.sessions import ProjectMetadata
from app.ui import streamlit_helpers

STREAMLIT_APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"
VALID_TRANSCRIPT = (
    "We need a small CRM with auth, contacts and roles. MVP in six weeks."
)


def _load_app() -> AppTest:
    return AppTest.from_file(str(STREAMLIT_APP))


@pytest.fixture
def loaded_app(openai_settings: None, monkeypatch: pytest.MonkeyPatch) -> AppTest:
    monkeypatch.setattr(
        streamlit_helpers,
        "create_session",
        lambda api_base: "test-session-id",
    )
    app = _load_app()
    app.run()
    return app


def test_streamlit_app_module_is_importable_without_side_effects() -> None:
    assert callable(estimator_ui.main)
    assert callable(estimator_ui.bootstrap)
    assert callable(estimator_ui.render_sidebar)
    assert callable(estimator_ui.render_conversation)


def test_streamlit_app_loads(loaded_app: AppTest) -> None:
    assert not loaded_app.exception
    assert loaded_app.title[0].value == "Software Estimator"
    assert loaded_app.sidebar.header[0].value == "Configuration"
    assert loaded_app.session_state.session_id == "test-session-id"
    assert loaded_app.session_state.prompt_version == "v2"


def test_bootstrap_shows_configuration_error(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_st = MagicMock()

    def boom() -> None:
        raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER is 'openai'")

    mock_st.stop.side_effect = StopIteration
    monkeypatch.setattr(estimator_ui, "st", mock_st)
    monkeypatch.setattr(estimator_ui, "get_settings", boom)

    with pytest.raises(StopIteration):
        estimator_ui.bootstrap()

    mock_st.error.assert_called_once()
    assert "LLM configuration error" in mock_st.error.call_args.args[0]


def test_bootstrap_stops_when_session_creation_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_st = MagicMock()
    mock_st.stop.side_effect = StopIteration
    mock_st.session_state = {}

    monkeypatch.setattr(estimator_ui, "st", mock_st)
    monkeypatch.setattr(
        streamlit_helpers,
        "ensure_session_id",
        MagicMock(side_effect=httpx.ConnectError("refused", request=MagicMock())),
    )

    with pytest.raises(StopIteration):
        estimator_ui.bootstrap()

    assert "Could not create session" in mock_st.error.call_args.args[0]


def test_conversation_validation_error_on_short_transcript(loaded_app: AppTest) -> None:
    loaded_app.text_area[0].set_value("too short")
    loaded_app.button[0].click().run()

    assert not loaded_app.exception
    assert loaded_app.error
    assert "20 characters" in loaded_app.error[0].value


def test_conversation_success_renders_estimation(
    loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        streamlit_helpers,
        "submit_session_estimate",
        lambda *args, **kwargs: SessionEstimationResponse(
            text="## Estimate\n\nTotal: 120 hours",
            prompt_version="v2",
            project_metadata=ProjectMetadata(),
        ),
    )

    loaded_app.text_area[0].set_value(VALID_TRANSCRIPT)
    loaded_app.button[0].click().run()

    assert not loaded_app.exception
    assert loaded_app.session_state.last_estimation is not None
    assert "Total: 120 hours" in loaded_app.markdown[-1].value


def test_conversation_updates_project_metadata(
    loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        streamlit_helpers,
        "submit_session_estimate",
        lambda *args, **kwargs: SessionEstimationResponse(
            text="## Estimate",
            prompt_version="v2",
            project_metadata=ProjectMetadata(project_name="BookFlow"),
        ),
    )

    loaded_app.text_area[0].set_value(VALID_TRANSCRIPT)
    loaded_app.button[0].click().run()

    assert loaded_app.session_state.project_metadata["project_name"] == "BookFlow"


def test_conversation_http_status_error(
    loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = httpx.Request("POST", "http://localhost:8000/sessions/x/estimate")
    response = httpx.Response(500, text="internal error", request=request)

    def boom(*args, **kwargs):
        raise httpx.HTTPStatusError("error", request=request, response=response)

    monkeypatch.setattr(streamlit_helpers, "submit_session_estimate", boom)

    loaded_app.text_area[0].set_value(VALID_TRANSCRIPT)
    loaded_app.button[0].click().run()

    assert loaded_app.error
    assert "Estimation failed (500)" in loaded_app.error[0].value


def test_conversation_request_error(
    loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        streamlit_helpers,
        "submit_session_estimate",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            httpx.ConnectError("connection refused", request=MagicMock())
        ),
    )

    loaded_app.text_area[0].set_value(VALID_TRANSCRIPT)
    loaded_app.button[0].click().run()

    assert loaded_app.error
    assert "Could not reach API" in loaded_app.error[0].value


def test_new_conversation_resets_session_state(
    loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    loaded_app.session_state.project_metadata = {"project_name": "BookFlow"}
    loaded_app.session_state.last_estimation = SessionEstimationResponse(
        text="saved",
        prompt_version="v2",
        project_metadata=ProjectMetadata(project_name="BookFlow"),
    )

    monkeypatch.setattr(
        streamlit_helpers,
        "create_session",
        lambda api_base: "fresh-session-id",
    )

    loaded_app.sidebar.button[0].click().run()

    assert not loaded_app.exception
    assert loaded_app.session_state.session_id == "fresh-session-id"
    assert loaded_app.session_state.project_metadata["project_name"] is None
    assert loaded_app.session_state.last_estimation is None


def test_new_conversation_shows_error_when_api_fails(
    loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(state, **kwargs):
        raise httpx.ConnectError("refused", request=MagicMock())

    monkeypatch.setattr(streamlit_helpers, "reset_conversation_state", boom)

    loaded_app.sidebar.button[0].click().run()

    assert loaded_app.error
    assert "Could not start a new session" in loaded_app.error[0].value


def test_render_conversation_displays_persisted_estimation(openai_settings: None) -> None:
    persisted = SessionEstimationResponse(
        text="## Saved estimate",
        prompt_version="v2",
        project_metadata=ProjectMetadata(),
    )
    at = _load_app()
    at.session_state["session_id"] = "existing-session"
    at.session_state["project_metadata"] = persisted.project_metadata.model_dump()
    at.session_state["last_estimation"] = persisted
    at.run()

    assert any("Saved estimate" in block.value for block in at.markdown)
