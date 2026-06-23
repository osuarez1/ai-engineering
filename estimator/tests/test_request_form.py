from app.schemas.request_form import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
    ReferenceProject,
)


def test_reference_project_round_trip() -> None:
    project = ReferenceProject(
        name="Example 1 — Field Service Mobile App",
        scope_summary="Cross-platform mobile app for HVAC technicians.",
        body="**Totals:** 176 hours · 10,700 EUR",
        project_type=ProjectType.MOBILE_APP,
    )
    request = EstimationRequest(
        description="We need a field service app for HVAC technicians with offline sync.",
        project_type=ProjectType.MOBILE_APP,
        detail_level=DetailLevel.MEDIUM,
        output_format=OutputFormat.PHASES_TABLE,
        reference_projects=[project],
    )
    payload = request.model_dump(mode="json")
    restored = EstimationRequest.model_validate(payload)
    assert restored.reference_projects == [project]


def test_estimation_request_omits_reference_projects_by_default() -> None:
    request = EstimationRequest(
        description="We need a small CRM with auth, contacts and roles. MVP in six weeks.",
        project_type=ProjectType.WEB_SAAS,
        detail_level=DetailLevel.MEDIUM,
        output_format=OutputFormat.PHASES_TABLE,
    )
    assert request.reference_projects is None
