from app.schemas.request_form import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)
from app.ui import streamlit_helpers


def test_initial_session_state() -> None:
    state = streamlit_helpers.initial_session_state()
    assert state == {
        "last_preview_request": None,
        "prompt_version": "v1",
    }


def test_preview_request_uses_default_when_no_submission() -> None:
    request = streamlit_helpers.preview_request(None)
    assert request == streamlit_helpers.DEFAULT_PREVIEW_REQUEST


def test_preview_request_uses_last_submission() -> None:
    submitted = EstimationRequest(
        description="A fleet maintenance dashboard for logistics managers.",
        project_type=ProjectType.WEB_SAAS,
        detail_level=DetailLevel.DETAILED,
        output_format=OutputFormat.NARRATIVE,
    )
    assert streamlit_helpers.preview_request(submitted) is submitted


def test_sidebar_prompt_preview_renders_system_and_user() -> None:
    request = EstimationRequest(
        description="An internal tool for tracking employee onboarding tasks.",
        project_type=ProjectType.INTERNAL_TOOL,
        detail_level=DetailLevel.MEDIUM,
        output_format=OutputFormat.PHASES_TABLE,
    )
    system, user = streamlit_helpers.sidebar_prompt_preview(request)
    assert "senior software consultant" in system
    assert "Field Service Mobile App" in system
    assert "employee onboarding" in user.lower()
    assert "Internal Tool" in user


def test_sidebar_prompt_preview_renders_v2_tone() -> None:
    request = EstimationRequest(
        description="An internal tool for tracking employee onboarding tasks.",
        project_type=ProjectType.INTERNAL_TOOL,
        detail_level=DetailLevel.MEDIUM,
        output_format=OutputFormat.PHASES_TABLE,
    )
    system, user = streamlit_helpers.sidebar_prompt_preview(request, version="v2")
    assert "pragmatic technical delivery lead" in system
    assert "Courier Dispatch Mobile App" in system
    assert "## Client brief" in user
