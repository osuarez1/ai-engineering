"""Template contract tests for estimation v2 Jinja prompts.

Same contract as ``test_estimation_v1`` but anchored on v2-specific tone, headings,
and few-shot examples. Renders via ``render_estimation_prompt`` only — no LLM or HTTP.
"""

import pytest

from app.prompts.loader import render_estimation_prompt
from app.schemas.request_form import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)

_UNIQUE_DESCRIPTION = (
    "Fleet maintenance dashboard for logistics managers with work orders and alerts."
)

PHASES_TABLE_MARKER = "| Task | Hours | Cost (EUR) |"
LINE_ITEMS_MARKER = "numbered line-item list"
NARRATIVE_MARKER = "plain, direct prose"

DETAIL_MARKERS: dict[DetailLevel, str] = {
    DetailLevel.SUMMARY: "task-level rows unless needed to defend the number",
    DetailLevel.MEDIUM: "roughly 5–8 phases or work streams",
    DetailLevel.DETAILED: "assumptions, technical risks, vendor dependencies, and contingency",
}

EXAMPLE_TITLES: list[tuple[OutputFormat, DetailLevel, str]] = [
    (OutputFormat.PHASES_TABLE, DetailLevel.SUMMARY, "Startup MVP Landing Page"),
    (OutputFormat.PHASES_TABLE, DetailLevel.MEDIUM, "Courier Dispatch Mobile App"),
    (OutputFormat.PHASES_TABLE, DetailLevel.DETAILED, "Procurement Workflow Portal"),
    (OutputFormat.LINE_ITEMS, DetailLevel.SUMMARY, "Webhook Health Monitor"),
    (OutputFormat.LINE_ITEMS, DetailLevel.MEDIUM, "Restaurant Reservation API"),
    (OutputFormat.LINE_ITEMS, DetailLevel.DETAILED, "Multi-tenant Audit Log Service"),
    (OutputFormat.NARRATIVE, DetailLevel.SUMMARY, "Personal Finance Tracker PWA"),
    (OutputFormat.NARRATIVE, DetailLevel.MEDIUM, "B2B Referral Program Platform"),
    (OutputFormat.NARRATIVE, DetailLevel.DETAILED, "Clinical Trial Site Portal"),
]

PROMPT_VERSION = "v2"


def _request(
    *,
    description: str = _UNIQUE_DESCRIPTION,
    project_type: ProjectType = ProjectType.WEB_SAAS,
    output_format: OutputFormat = OutputFormat.PHASES_TABLE,
    detail_level: DetailLevel = DetailLevel.MEDIUM,
) -> EstimationRequest:
    """Build a valid EstimationRequest, overriding only the fields a test cares about."""
    return EstimationRequest(
        description=description,
        project_type=project_type,
        detail_level=detail_level,
        output_format=output_format,
    )


# ---------------------------------------------------------------------------
# User prompt (user.j2) — client brief placement
# ---------------------------------------------------------------------------


def test_user_prompt_includes_description_in_client_brief_block() -> None:
    """The model must receive the user's scope text in the user role, under the heading."""
    request = _request()
    _, user = render_estimation_prompt(request, version=PROMPT_VERSION)

    heading = "## Client brief"
    assert heading in user
    assert _UNIQUE_DESCRIPTION in user
    assert user.index(heading) < user.index(_UNIQUE_DESCRIPTION)


# ---------------------------------------------------------------------------
# System prompt (system.j2) — output_format branches
# ---------------------------------------------------------------------------


def test_system_prompt_phases_table_includes_format_instructions() -> None:
    """phases_table activates the table spec; narrative must not leak table syntax."""
    phases_request = _request(output_format=OutputFormat.PHASES_TABLE)
    narrative_request = _request(output_format=OutputFormat.NARRATIVE)

    phases_system, _ = render_estimation_prompt(phases_request, version=PROMPT_VERSION)
    narrative_system, _ = render_estimation_prompt(narrative_request, version=PROMPT_VERSION)

    assert "phased delivery" in phases_system
    assert PHASES_TABLE_MARKER in phases_system
    assert NARRATIVE_MARKER not in phases_system

    assert NARRATIVE_MARKER in narrative_system
    assert PHASES_TABLE_MARKER not in narrative_system


def test_system_prompt_line_items_includes_format_instructions() -> None:
    """line_items is the third output_format branch — easy to break when editing system.j2."""
    system, _ = render_estimation_prompt(
        _request(output_format=OutputFormat.LINE_ITEMS),
        version=PROMPT_VERSION,
    )

    assert LINE_ITEMS_MARKER in system
    assert "One-line rationale" in system
    assert PHASES_TABLE_MARKER not in system
    assert NARRATIVE_MARKER not in system


# ---------------------------------------------------------------------------
# System prompt (system.j2) — detail_level branches
# ---------------------------------------------------------------------------


def test_system_prompt_detailed_includes_extra_assumption_instructions() -> None:
    """detailed asks for risks/assumptions; summary must stay high-level only."""
    detailed_request = _request(detail_level=DetailLevel.DETAILED)
    summary_request = _request(detail_level=DetailLevel.SUMMARY)

    detailed_system, _ = render_estimation_prompt(detailed_request, version=PROMPT_VERSION)
    summary_system, _ = render_estimation_prompt(summary_request, version=PROMPT_VERSION)

    detailed_marker = DETAIL_MARKERS[DetailLevel.DETAILED]
    summary_marker = DETAIL_MARKERS[DetailLevel.SUMMARY]

    assert "Go deep:" in detailed_system
    assert detailed_marker in detailed_system

    assert "Stay high level:" in summary_system
    assert summary_marker in summary_system
    assert detailed_marker not in summary_system
    assert "Go deep:" not in summary_system


@pytest.mark.parametrize("detail_level", list(DetailLevel))
def test_system_prompt_includes_exactly_one_detail_level_branch(
    detail_level: DetailLevel,
) -> None:
    """A typo in {% elif %} chains can leave multiple branches active — catch that here."""
    system, _ = render_estimation_prompt(
        _request(detail_level=detail_level),
        version=PROMPT_VERSION,
    )

    assert DETAIL_MARKERS[detail_level] in system
    for other_level, other_marker in DETAIL_MARKERS.items():
        if other_level is not detail_level:
            assert other_marker not in system


# ---------------------------------------------------------------------------
# Few-shot selection (examples.j2) — output_format × detail_level matrix
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
        version=PROMPT_VERSION,
    )

    assert example_title in system
    assert "Reference deliveries" in system


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
        version=PROMPT_VERSION,
    )

    assert f"**Type:** {user_type_label}" in user
    assert f"project type ({system_type_label})" in system


# ---------------------------------------------------------------------------
# Role separation — system vs user must not leak into each other
# ---------------------------------------------------------------------------


def test_description_only_in_user_prompt_not_system() -> None:
    """Scope belongs in the user message; duplicating it in system wastes tokens."""
    description = "Unique scope marker XYZ-12345 for separation test."
    system, user = render_estimation_prompt(
        _request(description=description),
        version=PROMPT_VERSION,
    )

    assert description in user
    assert description not in system


def test_examples_only_in_system_prompt_not_user() -> None:
    """Few-shot examples are CAG context for the model — they belong in system only."""
    system, user = render_estimation_prompt(_request(), version=PROMPT_VERSION)

    assert "Reference deliveries" in system
    # Default request is phases_table + medium → this v2 example must be selected.
    assert "Courier Dispatch Mobile App" in system
    assert "Reference deliveries" not in user
    assert "Courier Dispatch Mobile App" not in user


# ---------------------------------------------------------------------------
# Static invariants — content that must survive template refactors
# ---------------------------------------------------------------------------


def test_system_prompt_includes_static_invariants() -> None:
    """Regression guard for role, pricing assumptions, guardrails, and examples preamble."""
    system, _ = render_estimation_prompt(_request(), version=PROMPT_VERSION)

    assert "pragmatic technical delivery lead" in system
    assert "62.50 EUR/hour" in system
    assert "50 EUR/hour" in system
    assert "flag gaps instead of guessing features" in system
    assert "Reference deliveries" in system


def test_system_prompt_does_not_use_v1_tone() -> None:
    """v2 must not accidentally include v1 consultant wording or example preamble."""
    system, _ = render_estimation_prompt(_request(), version=PROMPT_VERSION)

    assert "senior software consultant" not in system
    assert "Reference examples" not in system
    assert "Field Service Mobile App" not in system


# ---------------------------------------------------------------------------
# Jinja safety — user-provided description is interpolated verbatim
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "description",
    [
        "x" * 20,
        'Description with "double quotes" and \'single quotes\' inside.',
        "Line one of scope.\nLine two with {{ braces }} and backticks `code`.",
        "Unicode scope: café, naïve façade, 日本語, emoji 🚀.",
    ],
    ids=["min_length", "quotes", "newlines_and_braces", "unicode"],
)
def test_user_prompt_renders_description_literals_unchanged(description: str) -> None:
    """Description is {{ description }}, not a Jinja expression — special chars must pass through."""
    _, user = render_estimation_prompt(
        _request(description=description),
        version=PROMPT_VERSION,
    )

    assert description in user
