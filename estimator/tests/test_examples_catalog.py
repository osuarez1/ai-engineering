from app.prompts.examples_catalog import (
    CatalogEntry,
    V1_ALL_PROJECTS,
    V1_CATALOG,
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
    project = ReferenceProject(
        name="Example 1 — Field Service Mobile App",
        scope_summary="Cross-platform mobile app for HVAC technicians.",
        body="**Totals:** 176 hours",
        project_type=ProjectType.MOBILE_APP,
    )
    V1_CATALOG.append(
        CatalogEntry(
            output_format=OutputFormat.PHASES_TABLE,
            detail_level=DetailLevel.MEDIUM,
            projects=[project],
        )
    )
    try:
        names = few_shot_project_names(
            version="v1",
            output_format=OutputFormat.PHASES_TABLE,
            detail_level=DetailLevel.MEDIUM,
        )
        assert names == {project.name}
    finally:
        V1_CATALOG.clear()


def test_few_shot_project_names_returns_empty_for_unknown_combo() -> None:
    assert (
        few_shot_project_names(
            version="v1",
            output_format=OutputFormat.NARRATIVE,
            detail_level=DetailLevel.SUMMARY,
        )
        == set()
    )


def test_resolve_reference_projects_filters_by_type_and_excludes_few_shot() -> None:
    few_shot = ReferenceProject(
        name="Example 1 — Field Service Mobile App",
        scope_summary="Few-shot scope",
        body="Few-shot body",
        project_type=ProjectType.MOBILE_APP,
    )
    similar = ReferenceProject(
        name="Example 1 — Warehouse Barcode Scanner App",
        scope_summary="Warehouse scanning scope",
        body="Warehouse scanning body",
        project_type=ProjectType.MOBILE_APP,
    )
    other_type = ReferenceProject(
        name="Example 1 — Employee Onboarding Internal Tool",
        scope_summary="Onboarding scope",
        body="Onboarding body",
        project_type=ProjectType.INTERNAL_TOOL,
    )
    V1_CATALOG.append(
        CatalogEntry(
            output_format=OutputFormat.PHASES_TABLE,
            detail_level=DetailLevel.MEDIUM,
            projects=[few_shot],
        )
    )
    V1_ALL_PROJECTS.extend([few_shot, similar, other_type])
    try:
        resolved = resolve_reference_projects(
            version="v1",
            project_type=ProjectType.MOBILE_APP,
            output_format=OutputFormat.PHASES_TABLE,
            detail_level=DetailLevel.MEDIUM,
        )
        assert resolved == [similar]
    finally:
        V1_CATALOG.clear()
        V1_ALL_PROJECTS.clear()


def test_resolve_reference_projects_uses_v2_catalog_for_non_v1_version() -> None:
    from app.prompts import examples_catalog

    project = ReferenceProject(
        name="Example 1 — Courier Dispatch Mobile App",
        scope_summary="Courier app scope",
        body="Courier app body",
        project_type=ProjectType.MOBILE_APP,
    )
    examples_catalog.V2_ALL_PROJECTS.append(project)
    try:
        resolved = resolve_reference_projects(
            version="v2",
            project_type=ProjectType.MOBILE_APP,
            output_format=OutputFormat.PHASES_TABLE,
            detail_level=DetailLevel.MEDIUM,
        )
        assert resolved == [project]
    finally:
        examples_catalog.V2_ALL_PROJECTS.clear()
