import pytest

from app.prompts import examples_catalog
from app.prompts.examples_catalog import (
    V1_ALL_PROJECTS,
    V2_ALL_PROJECTS,
    few_shot_project_names,
    resolve_reference_projects,
)
from app.schemas.request_form import (
    DetailLevel,
    OutputFormat,
    ProjectType,
    ReferenceProject,
)


def test_few_shot_project_names_returns_names_for_matching_branch() -> None:
    names = few_shot_project_names(
        version="v1",
        output_format=OutputFormat.PHASES_TABLE,
        detail_level=DetailLevel.MEDIUM,
    )
    assert names == {
        "Example 1 — Field Service Mobile App",
        "Example 2 — Retail Sales Analytics Pipeline",
    }


def test_few_shot_project_names_returns_empty_for_unknown_combo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(examples_catalog._CATALOG_BY_VERSION, "v1", [])
    assert (
        few_shot_project_names(
            version="v1",
            output_format=OutputFormat.NARRATIVE,
            detail_level=DetailLevel.SUMMARY,
        )
        == set()
    )


def test_resolve_reference_projects_filters_by_type_and_excludes_few_shot() -> None:
    resolved = resolve_reference_projects(
        version="v1",
        project_type=ProjectType.MOBILE_APP,
        output_format=OutputFormat.PHASES_TABLE,
        detail_level=DetailLevel.MEDIUM,
    )
    assert resolved
    assert all(project.project_type == ProjectType.MOBILE_APP for project in resolved)
    assert "Example 1 — Field Service Mobile App" not in {p.name for p in resolved}
    assert "Example 1 — Warehouse Barcode Scanner App" in {p.name for p in resolved}


def test_resolve_reference_projects_matches_project_type_only() -> None:
    resolved = resolve_reference_projects(
        version="v1",
        project_type=ProjectType.DATA_PIPELINE,
        output_format=OutputFormat.PHASES_TABLE,
        detail_level=DetailLevel.SUMMARY,
    )
    assert resolved
    assert all(project.project_type == ProjectType.DATA_PIPELINE for project in resolved)
    assert "Example 2 — Retail Sales Analytics Pipeline" in {p.name for p in resolved}


def test_resolve_reference_projects_uses_v2_catalog_for_non_v1_version() -> None:
    resolved = resolve_reference_projects(
        version="v2",
        project_type=ProjectType.MOBILE_APP,
        output_format=OutputFormat.PHASES_TABLE,
        detail_level=DetailLevel.SUMMARY,
    )
    assert resolved == [
        p for p in V2_ALL_PROJECTS if p.project_type == ProjectType.MOBILE_APP
    ][:3]
    assert resolved[0].name == "Example 1 — Courier Dispatch Mobile App"


def test_resolve_reference_projects_returns_empty_when_no_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(examples_catalog, "V1_ALL_PROJECTS", [])
    assert (
        resolve_reference_projects(
            version="v1",
            project_type=ProjectType.WEB_SAAS,
            output_format=OutputFormat.PHASES_TABLE,
            detail_level=DetailLevel.MEDIUM,
        )
        == []
    )


def test_resolve_reference_projects_caps_results_at_three() -> None:
    extras = [
        ReferenceProject(
            name=f"Example 99 — Extra Web SaaS {index}",
            scope_summary="Extra scope",
            body="Extra body",
            project_type=ProjectType.WEB_SAAS,
        )
        for index in range(5)
    ]
    V1_ALL_PROJECTS.extend(extras)
    try:
        resolved = resolve_reference_projects(
            version="v1",
            project_type=ProjectType.WEB_SAAS,
            output_format=OutputFormat.PHASES_TABLE,
            detail_level=DetailLevel.SUMMARY,
        )
        assert len(resolved) == 3
    finally:
        for extra in extras:
            V1_ALL_PROJECTS.remove(extra)
