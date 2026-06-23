"""Structured catalog of few-shot examples for reference-project resolution.

Content is migrated from ``estimation/<version>/examples.j2``. Few-shot rendering
still uses the Jinja templates directly; this module powers the optional
``reference_projects`` field resolved by ``project_type``.

Project-type tags (applied during migration from examples.j2):

- **MOBILE_APP** — field service, courier dispatch, barcode scanner apps
- **WEB_SAAS** — landing pages, marketplaces, SaaS billing, APIs, PWAs
- **INTERNAL_TOOL** — onboarding, portals, notifier/routers, hospital boards
- **DATA_PIPELINE** — analytics pipelines, IoT/monitoring dashboards
"""

from dataclasses import dataclass

from app.prompts.catalog_data_v1 import V1_CATALOG_RAW
from app.prompts.catalog_data_v2 import V2_CATALOG_RAW
from app.schemas.request_form import (
    DetailLevel,
    OutputFormat,
    ProjectType,
    ReferenceProject,
)


@dataclass(frozen=True)
class CatalogEntry:
    # Mirrors one ``{% elif %}`` branch in examples.j2 (output_format × detail_level).
    output_format: OutputFormat
    detail_level: DetailLevel
    projects: list[ReferenceProject]


def _build_catalog(
    raw: list[tuple[OutputFormat, DetailLevel, list[ReferenceProject]]],
) -> list[CatalogEntry]:
    return [
        CatalogEntry(output_format=fmt, detail_level=level, projects=projects)
        for fmt, level, projects in raw
    ]


V1_CATALOG: list[CatalogEntry] = _build_catalog(V1_CATALOG_RAW)
V2_CATALOG: list[CatalogEntry] = _build_catalog(V2_CATALOG_RAW)

V1_ALL_PROJECTS: list[ReferenceProject] = [
    project for entry in V1_CATALOG for project in entry.projects
]
V2_ALL_PROJECTS: list[ReferenceProject] = [
    project for entry in V2_CATALOG for project in entry.projects
]

_CATALOG_BY_VERSION: dict[str, list[CatalogEntry]] = {
    "v1": V1_CATALOG,
    "v2": V2_CATALOG,
}


def few_shot_project_names(
    *,
    version: str,
    output_format: OutputFormat,
    detail_level: DetailLevel,
) -> set[str]:
    """Return example names that ``examples.j2`` would render for this combo."""
    catalog = _CATALOG_BY_VERSION.get(version, V2_CATALOG)
    for entry in catalog:
        if entry.output_format == output_format and entry.detail_level == detail_level:
            return {project.name for project in entry.projects}
    return set()


def resolve_reference_projects(
    *,
    version: str,
    project_type: ProjectType,
    output_format: OutputFormat,
    detail_level: DetailLevel,
    limit: int = 3,
) -> list[ReferenceProject]:
    """Return similar completed projects matching ``project_type``, excluding few-shot."""
    all_projects = V1_ALL_PROJECTS if version == "v1" else V2_ALL_PROJECTS
    # Exclude the examples.j2 branch already selected by output_format × detail_level
    # so few-shot and reference-project sections never repeat the same titles.
    excluded = few_shot_project_names(
        version=version,
        output_format=output_format,
        detail_level=detail_level,
    )
    matches = [
        project
        for project in all_projects
        if project.project_type == project_type and project.name not in excluded
    ]
    return matches[:limit]
