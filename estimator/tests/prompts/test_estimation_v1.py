"""Template contract tests for estimation v1 Jinja prompts.

These tests render prompts via ``render_estimation_prompt`` — the same path the API
and Streamlit UI use — but never call an LLM or HTTP endpoint. They run in
milliseconds and guard the *template contract*: which Jinja branches fire for each
form field, what text lands in system vs user roles, and which few-shot examples
are inlined from ``examples.j2``.

If a template edit breaks conditional logic or accidentally leaks content across
roles, these tests should fail before a bad prompt ever reaches a model.
"""

import pytest

from app.prompts.examples_catalog import resolve_reference_projects
from app.prompts.loader import render_estimation_prompt
from app.schemas.request_form import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)

# Distinct enough to grep in rendered output without colliding with example text.
_UNIQUE_DESCRIPTION = (
    "Fleet maintenance dashboard for logistics managers with work orders and alerts."
)

# Anchor strings unique to each ``{% if output_format %}`` branch in system.j2.
# We assert presence/absence rather than full prompt snapshots to keep tests stable.
PHASES_TABLE_MARKER = "| Task | Hours | Cost (EUR) |"
LINE_ITEMS_MARKER = "numbered list of line items"
NARRATIVE_MARKER = "connected prose"

# One distinctive phrase per ``{% if detail_level %}`` branch — used to verify
# mutual exclusivity (exactly one branch active per render).
DETAIL_MARKERS: dict[DetailLevel, str] = {
    DetailLevel.SUMMARY: "Do not break down individual tasks unless",
    DetailLevel.MEDIUM: "roughly 5–8 work items or phases",
    DetailLevel.DETAILED: "assumptions, technical risks, external dependencies",
}

# examples.j2 branches on output_format × detail_level (3×3 = 9 combos). Each row
# maps to a unique "Example 1" title so we can detect the wrong few-shot block
# without comparing entire rendered prompts.
EXAMPLE_TITLES: list[tuple[OutputFormat, DetailLevel, str]] = [
    (OutputFormat.PHASES_TABLE, DetailLevel.SUMMARY, "Marketing Landing Page Refresh"),
    (OutputFormat.PHASES_TABLE, DetailLevel.MEDIUM, "Field Service Mobile App"),
    (OutputFormat.PHASES_TABLE, DetailLevel.DETAILED, "Employee Onboarding Internal Tool"),
    (OutputFormat.LINE_ITEMS, DetailLevel.SUMMARY, "Podcast RSS Feed Validator"),
    (OutputFormat.LINE_ITEMS, DetailLevel.MEDIUM, "Warehouse Barcode Scanner App"),
    (OutputFormat.LINE_ITEMS, DetailLevel.DETAILED, "IoT Cold-Chain Monitoring Dashboard"),
    (OutputFormat.NARRATIVE, DetailLevel.SUMMARY, "Fitness Class Booking Widget"),
    (OutputFormat.NARRATIVE, DetailLevel.MEDIUM, "Community Marketplace Web App"),
    (OutputFormat.NARRATIVE, DetailLevel.DETAILED, "Insurance Claims Triage Platform"),
]


def _request(
    *,
    description: str = _UNIQUE_DESCRIPTION,
    project_type: ProjectType = ProjectType.WEB_SAAS,
    output_format: OutputFormat = OutputFormat.PHASES_TABLE,
    detail_level: DetailLevel = DetailLevel.MEDIUM,
    reference_projects: list | None = None,
) -> EstimationRequest:
    """Build a valid EstimationRequest, overriding only the fields a test cares about."""
    return EstimationRequest(
        description=description,
        project_type=project_type,
        detail_level=detail_level,
        output_format=output_format,
        reference_projects=reference_projects,
    )


def _request_with_resolved_reference_projects(
    *,
    description: str = _UNIQUE_DESCRIPTION,
    project_type: ProjectType = ProjectType.MOBILE_APP,
    output_format: OutputFormat = OutputFormat.PHASES_TABLE,
    detail_level: DetailLevel = DetailLevel.MEDIUM,
) -> EstimationRequest:
    return _request(
        description=description,
        project_type=project_type,
        output_format=output_format,
        detail_level=detail_level,
        reference_projects=resolve_reference_projects(
            version="v1",
            project_type=project_type,
            output_format=output_format,
            detail_level=detail_level,
        ),
    )


# ---------------------------------------------------------------------------
# User prompt (user.j2) — project description placement
# ---------------------------------------------------------------------------


def test_user_prompt_includes_description_in_project_block() -> None:
    """The model must receive the user's scope text in the user role, under the heading."""
    request = _request()
    _, user = render_estimation_prompt(request, version="v1")

    heading = "## Project to estimate"
    assert heading in user
    assert _UNIQUE_DESCRIPTION in user
    # Ordering matters: heading introduces the block, description follows it.
    assert user.index(heading) < user.index(_UNIQUE_DESCRIPTION)


# ---------------------------------------------------------------------------
# System prompt (system.j2) — output_format branches
# ---------------------------------------------------------------------------


def test_system_prompt_phases_table_includes_format_instructions() -> None:
    """phases_table activates the table spec; narrative must not leak table syntax."""
    phases_request = _request(output_format=OutputFormat.PHASES_TABLE)
    narrative_request = _request(output_format=OutputFormat.NARRATIVE)

    phases_system, _ = render_estimation_prompt(phases_request, version="v1")
    narrative_system, _ = render_estimation_prompt(narrative_request, version="v1")

    assert "delivery phases" in phases_system
    assert PHASES_TABLE_MARKER in phases_system
    assert NARRATIVE_MARKER not in phases_system

    assert NARRATIVE_MARKER in narrative_system
    assert PHASES_TABLE_MARKER not in narrative_system


def test_system_prompt_line_items_includes_format_instructions() -> None:
    """line_items is the third output_format branch — easy to break when editing system.j2."""
    system, _ = render_estimation_prompt(
        _request(output_format=OutputFormat.LINE_ITEMS),
        version="v1",
    )

    assert LINE_ITEMS_MARKER in system
    assert "One-sentence justification" in system
    assert PHASES_TABLE_MARKER not in system
    assert NARRATIVE_MARKER not in system


# ---------------------------------------------------------------------------
# System prompt (system.j2) — detail_level branches
# ---------------------------------------------------------------------------


def test_system_prompt_detailed_includes_extra_assumption_instructions() -> None:
    """detailed asks for risks/assumptions; summary must stay high-level only."""
    detailed_request = _request(detail_level=DetailLevel.DETAILED)
    summary_request = _request(detail_level=DetailLevel.SUMMARY)

    detailed_system, _ = render_estimation_prompt(detailed_request, version="v1")
    summary_system, _ = render_estimation_prompt(summary_request, version="v1")

    detailed_marker = DETAIL_MARKERS[DetailLevel.DETAILED]
    summary_marker = DETAIL_MARKERS[DetailLevel.SUMMARY]

    assert "comprehensive breakdown" in detailed_system
    assert detailed_marker in detailed_system

    assert "Keep the estimation concise" in summary_system
    assert summary_marker in summary_system
    assert detailed_marker not in summary_system
    assert "comprehensive breakdown" not in summary_system


@pytest.mark.parametrize("detail_level", list(DetailLevel))
def test_system_prompt_includes_exactly_one_detail_level_branch(
    detail_level: DetailLevel,
) -> None:
    """A typo in {% elif %} chains can leave multiple branches active — catch that here."""
    system, _ = render_estimation_prompt(
        _request(detail_level=detail_level),
        version="v1",
    )

    assert DETAIL_MARKERS[detail_level] in system
    for other_level, other_marker in DETAIL_MARKERS.items():
        if other_level is not detail_level:
            assert other_marker not in system


# ---------------------------------------------------------------------------
# CAG few-shot selection (examples.j2) — output_format × detail_level matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("output_format", "detail_level", "example_title"),
    EXAMPLE_TITLES,
    ids=[f"{fmt.value}-{lvl.value}" for fmt, lvl, _ in EXAMPLE_TITLES],
)
def test_examples_match_format_and_detail_level(
    output_format: OutputFormat,
    detail_level: DetailLevel,
    example_title: str,
) -> None:
    """Wrong few-shot examples teach the model the wrong output shape — verify all 9 paths."""
    system, _ = render_estimation_prompt(
        _request(output_format=output_format, detail_level=detail_level),
        version="v1",
    )

    assert example_title in system
    assert "Reference examples" in system


# ---------------------------------------------------------------------------
# Jinja filters — project_type rendered differently in user vs system
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("project_type", "user_type_label", "system_type_label"),
    [
        (ProjectType.MOBILE_APP, "Mobile App", "mobile app"),
        (ProjectType.DATA_PIPELINE, "Data Pipeline", "data pipeline"),
        (ProjectType.INTERNAL_TOOL, "Internal Tool", "internal tool"),
    ],
)
def test_project_type_rendered_in_user_and_system_prompts(
    project_type: ProjectType,
    user_type_label: str,
    system_type_label: str,
) -> None:
    """user.j2 uses |title; system.j2 does not — both must still read naturally."""
    system, user = render_estimation_prompt(
        _request(project_type=project_type),
        version="v1",
    )

    assert f"**Type:** {user_type_label}" in user
    assert f"project type ({system_type_label})" in system


# ---------------------------------------------------------------------------
# Role separation — system vs user must not leak into each other
# ---------------------------------------------------------------------------


def test_description_only_in_user_prompt_not_system() -> None:
    """Scope belongs in the user message; duplicating it in system wastes tokens and confuses role boundaries."""
    description = "Unique scope marker XYZ-12345 for separation test."
    system, user = render_estimation_prompt(
        _request(description=description),
        version="v1",
    )

    assert description in user
    assert description not in system


def test_examples_only_in_system_prompt_not_user() -> None:
    """Few-shot examples are CAG context for the model — they belong in system only."""
    system, user = render_estimation_prompt(_request(), version="v1")

    assert "Reference examples" in system
    # Default request is phases_table + medium → this example must be selected.
    assert "Field Service Mobile App" in system
    assert "Reference examples" not in user
    assert "Field Service Mobile App" not in user


# ---------------------------------------------------------------------------
# Static invariants — content that must survive template refactors
# ---------------------------------------------------------------------------


def test_system_prompt_includes_static_invariants() -> None:
    """Regression guard for role, pricing assumptions, guardrails, and examples preamble."""
    system, _ = render_estimation_prompt(_request(), version="v1")

    assert "senior software consultant" in system
    assert "62.50 EUR/hour" in system
    assert "50 EUR/hour" in system
    assert "Do not invent major features" in system
    assert "Reference examples" in system


# ---------------------------------------------------------------------------
# Jinja safety — user-provided description is interpolated verbatim
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "description",
    [
        "x" * 20,  # Pydantic min_length boundary
        'Description with "double quotes" and \'single quotes\' inside.',
        "Line one of scope.\nLine two with {{ braces }} and backticks `code`.",
        "Unicode scope: café, naïve façade, 日本語, emoji 🚀.",
    ],
    ids=["min_length", "quotes", "newlines_and_braces", "unicode"],
)
def test_user_prompt_renders_description_literals_unchanged(description: str) -> None:
    """Description is {{ description }}, not a Jinja expression — special chars must pass through."""
    _, user = render_estimation_prompt(_request(description=description), version="v1")

    assert description in user


# ---------------------------------------------------------------------------
# Reference projects (reference_projects.j2) — dynamic similar-project context
# ---------------------------------------------------------------------------


def test_v1_reference_projects_renders_similar_completed_projects_section() -> None:
    request = _request_with_resolved_reference_projects()
    system, _ = render_estimation_prompt(request, version="v1")

    assert "Similar completed projects" in system
    assert "Warehouse Barcode Scanner App" in system
    assert "Reference examples" not in system


def test_v1_reference_projects_excludes_active_few_shot_titles() -> None:
    request = _request_with_resolved_reference_projects()
    system, _ = render_estimation_prompt(request, version="v1")

    assert "Field Service Mobile App" not in system
    assert "Retail Sales Analytics Pipeline" not in system


def test_v1_reference_projects_includes_scope_and_body() -> None:
    request = _request_with_resolved_reference_projects()
    system, _ = render_estimation_prompt(request, version="v1")

    assert "warehouse staff" in system
    assert "Barcode scanning module" in system


def test_v1_reference_projects_none_uses_static_examples() -> None:
    system, _ = render_estimation_prompt(_request(reference_projects=None), version="v1")

    assert "Reference examples" in system
    assert "Field Service Mobile App" in system
    assert "Similar completed projects" not in system


def test_v1_empty_reference_projects_falls_back_to_static_examples() -> None:
    system, _ = render_estimation_prompt(_request(reference_projects=[]), version="v1")

    assert "Reference examples" in system
    assert "Field Service Mobile App" in system
    assert "Similar completed projects" not in system
