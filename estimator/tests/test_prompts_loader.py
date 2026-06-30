import pytest

from app.prompts.loader import (
    render_estimation_prompt,
    render_session_system_prompt,
    render_session_user_prompt,
)
from app.schemas.request_form import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)
from app.sessions import ProjectMetadata

REQUEST = EstimationRequest(
    description="We need a small CRM with auth, contacts and roles. MVP in six weeks.",
    project_type=ProjectType.WEB_SAAS,
    detail_level=DetailLevel.MEDIUM,
    output_format=OutputFormat.PHASES_TABLE,
)


def test_render_estimation_prompt_v1() -> None:
    system, user = render_estimation_prompt(REQUEST, version="v1")
    assert "senior software consultant" in system
    assert REQUEST.description in user


def test_render_estimation_prompt_v2() -> None:
    system, user = render_estimation_prompt(REQUEST, version="v2")
    assert "pragmatic technical delivery lead" in system
    assert "## Client brief" in user
    assert REQUEST.description in user


def test_unknown_prompt_version_raises() -> None:
    with pytest.raises(ValueError, match="Unknown prompt version: missing"):
        render_estimation_prompt(REQUEST, version="missing")


def test_render_session_system_prompt_includes_project_metadata() -> None:
    metadata = ProjectMetadata(
        project_name="BookFlow",
        assumed_team_size=3,
        mentioned_technologies=["Rails", "React"],
        agreed_scope="MVP with auth and contacts",
    )
    system = render_session_system_prompt(REQUEST, metadata, version="v2")
    assert "<project_metadata>" in system
    assert "Project name: BookFlow" in system
    assert "Assumed team size: 3 full-time engineers" in system
    assert "Technologies mentioned: Rails, React" in system
    assert "Agreed scope: MVP with auth and contacts" in system
    assert "established facts" in system


def test_render_session_system_prompt_omits_empty_metadata_block() -> None:
    system = render_session_system_prompt(REQUEST, ProjectMetadata(), version="v2")
    assert "<project_metadata>" not in system
    assert "<session_anchors>" not in system
    assert "<session_summary>" not in system


def test_render_session_system_prompt_includes_anchors_and_summary() -> None:
    system = render_session_system_prompt(
        REQUEST,
        ProjectMetadata(project_name="Nimbus"),
        version="v2",
        anchors=["budget 30000 EUR", "project is called Nimbus"],
        summary="User: Need auth.\nAssistant: Added auth scope.",
    )
    assert "<session_anchors>" in system
    assert "- budget 30000 EUR" in system
    assert "- project is called Nimbus" in system
    assert "pinned decisions" in system
    assert "<session_summary>" in system
    assert "User: Need auth." in system
    assert "compressed context" in system


def test_render_session_user_prompt_v2() -> None:
    user = render_session_user_prompt(REQUEST, version="v2")
    assert REQUEST.description in user
    assert "## Client brief" in user
