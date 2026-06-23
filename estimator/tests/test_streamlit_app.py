from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from streamlit.testing.v1 import AppTest

import streamlit_app as estimator_ui
from app.schemas.request_form import (
    DetailLevel,
    EstimationResponse,
    OutputFormat,
    ProjectType,
    ReferenceProject,
)

STREAMLIT_APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"
VALID_DESCRIPTION = (
    "We need a small CRM with auth, contacts and roles. MVP in six weeks."
)


def _load_app() -> AppTest:
    return AppTest.from_file(str(STREAMLIT_APP))


@pytest.fixture
def loaded_app(openai_settings: None) -> AppTest:
    app = _load_app()
    app.run()
    return app


def test_streamlit_app_module_is_importable_without_side_effects() -> None:
    assert callable(estimator_ui.main)
    assert callable(estimator_ui.bootstrap)
    assert callable(estimator_ui.render_sidebar)
    assert callable(estimator_ui.render_form)
    assert callable(estimator_ui.build_estimation_request)
    assert estimator_ui._enum_label(estimator_ui.ProjectType.WEB_SAAS) == "Web Saas"


def test_build_estimation_request_without_reference_projects() -> None:
    request = estimator_ui.build_estimation_request(
        description=VALID_DESCRIPTION,
        project_type=ProjectType.WEB_SAAS,
        detail_level=DetailLevel.MEDIUM,
        output_format=OutputFormat.PHASES_TABLE,
        include_reference_projects=False,
        prompt_version="v1",
    )
    assert request.reference_projects is None


def test_build_estimation_request_with_reference_projects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = [
        ReferenceProject(
            name="Example 1 — Multi-tenant Subscription Billing SaaS",
            scope_summary="Billing SaaS scope",
            body="Billing SaaS body",
            project_type=ProjectType.WEB_SAAS,
        )
    ]
    monkeypatch.setattr(estimator_ui, "resolve_reference_projects", lambda **kwargs: sample)
    request = estimator_ui.build_estimation_request(
        description=VALID_DESCRIPTION,
        project_type=ProjectType.WEB_SAAS,
        detail_level=DetailLevel.MEDIUM,
        output_format=OutputFormat.PHASES_TABLE,
        include_reference_projects=True,
        prompt_version="v1",
    )
    assert request.reference_projects == sample


def test_form_posts_reference_projects_when_checkbox_enabled(
    loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    posted: list[dict] = []
    sample = [
        ReferenceProject(
            name="Example 1 — Multi-tenant Subscription Billing SaaS",
            scope_summary="Billing SaaS scope",
            body="Billing SaaS body",
            project_type=ProjectType.WEB_SAAS,
        )
    ]

    def fake_post(url: str, **kwargs) -> httpx.Response:
        posted.append(kwargs)
        return httpx.Response(
            200,
            json={"text": "## Estimate\n\nTotal: 120 hours", "prompt_version": "v1"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(
        "app.prompts.examples_catalog.resolve_reference_projects",
        lambda **kwargs: sample,
    )
    monkeypatch.setattr(estimator_ui.httpx, "post", fake_post)

    loaded_app.text_area[0].set_value(VALID_DESCRIPTION)
    loaded_app.checkbox[0].check()
    loaded_app.button[0].click().run()

    assert not loaded_app.exception
    assert posted[0]["json"]["reference_projects"] == [
        project.model_dump(mode="json") for project in sample
    ]


def test_form_omits_reference_projects_when_checkbox_disabled(
    loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    posted: list[dict] = []

    def fake_post(url: str, **kwargs) -> httpx.Response:
        posted.append(kwargs)
        return httpx.Response(
            200,
            json={"text": "## Estimate\n\nTotal: 120 hours", "prompt_version": "v1"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(estimator_ui.httpx, "post", fake_post)

    loaded_app.text_area[0].set_value(VALID_DESCRIPTION)
    loaded_app.button[0].click().run()

    assert not loaded_app.exception
    assert posted[0]["json"]["reference_projects"] is None


def test_streamlit_app_loads(loaded_app: AppTest) -> None:
    assert not loaded_app.exception
    assert loaded_app.title[0].value == "Software Estimator"
    assert loaded_app.sidebar.header[0].value == "Configuration"
    assert loaded_app.text_area
    assert loaded_app.session_state.prompt_version == "v1"


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


def test_form_validation_error_on_short_description(loaded_app: AppTest) -> None:
    loaded_app.text_area[0].set_value("too short")
    loaded_app.button[0].click().run()

    assert not loaded_app.exception
    assert loaded_app.error
    assert "description" in loaded_app.error[0].value.lower()


def test_form_success_renders_estimation(
    loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = httpx.Response(
        200,
        json={"text": "## Estimate\n\nTotal: 120 hours", "prompt_version": "v1"},
        request=httpx.Request("POST", estimator_ui.API_ESTIMATE_URL),
    )
    monkeypatch.setattr(estimator_ui.httpx, "post", lambda *args, **kwargs: response)

    loaded_app.text_area[0].set_value(VALID_DESCRIPTION)
    loaded_app.button[0].click().run()

    assert not loaded_app.exception
    assert loaded_app.session_state.last_estimation is not None
    assert loaded_app.markdown
    assert "Total: 120 hours" in loaded_app.markdown[-1].value


def test_form_posts_selected_prompt_version(
    loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    posted: list[dict] = []

    def fake_post(url: str, **kwargs) -> httpx.Response:
        posted.append({"url": url, **kwargs})
        return httpx.Response(
            200,
            json={"text": "## Estimate\n\nTotal: 120 hours", "prompt_version": "v2"},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(estimator_ui.httpx, "post", fake_post)

    loaded_app.session_state.prompt_version = "v2"
    loaded_app.text_area[0].set_value(VALID_DESCRIPTION)
    loaded_app.button[0].click().run()

    assert not loaded_app.exception
    assert posted[0]["params"] == {"prompt_version": "v2"}
    assert loaded_app.session_state.last_estimation.prompt_version == "v2"


def test_form_http_status_error(
    loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = httpx.Request("POST", estimator_ui.API_ESTIMATE_URL)
    response = httpx.Response(500, text="internal error", request=request)
    monkeypatch.setattr(
        estimator_ui.httpx,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            httpx.HTTPStatusError("error", request=request, response=response)
        ),
    )

    loaded_app.text_area[0].set_value(VALID_DESCRIPTION)
    loaded_app.button[0].click().run()

    assert loaded_app.error
    assert "Estimation failed (500)" in loaded_app.error[0].value


def test_form_request_error(loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        estimator_ui.httpx,
        "post",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            httpx.ConnectError("connection refused", request=MagicMock())
        ),
    )

    loaded_app.text_area[0].set_value(VALID_DESCRIPTION)
    loaded_app.button[0].click().run()

    assert loaded_app.error
    assert "Could not reach API" in loaded_app.error[0].value


def test_form_invalid_api_response(
    loaded_app: AppTest, monkeypatch: pytest.MonkeyPatch
) -> None:
    response = httpx.Response(
        200,
        json={"unexpected": "shape"},
        request=httpx.Request("POST", estimator_ui.API_ESTIMATE_URL),
    )
    monkeypatch.setattr(estimator_ui.httpx, "post", lambda *args, **kwargs: response)

    loaded_app.text_area[0].set_value(VALID_DESCRIPTION)
    loaded_app.button[0].click().run()

    assert loaded_app.error
    assert "Invalid API response" in loaded_app.error[0].value


def test_render_form_displays_persisted_estimation(openai_settings: None) -> None:
    persisted = EstimationResponse(text="## Saved estimate", prompt_version="v1")
    at = _load_app()
    at.session_state["last_estimation"] = persisted
    at.run()

    assert any("Saved estimate" in block.value for block in at.markdown)
