import pytest

from app.prompts.loader import render_estimation_prompt
from app.schemas.request_form import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)

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
