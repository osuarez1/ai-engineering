from app.services.anchor_extractor import extract_anchors_from_turn, update_anchors
from app.sessions import ProjectMetadata


def test_extract_anchors_budget_statement() -> None:
    anchors = extract_anchors_from_turn(
        "The budget 30000 EUR is approved for phase one.",
        "I will estimate within that budget.",
        ProjectMetadata(),
    )
    assert "budget 30000 EUR" in anchors


def test_extract_anchors_project_name_from_transcript() -> None:
    anchors = extract_anchors_from_turn(
        "The project is called Nimbus and needs auth.",
        "Estimating Nimbus as a SaaS MVP.",
        ProjectMetadata(),
    )
    assert "project is called Nimbus" in anchors


def test_extract_anchors_project_name_from_metadata() -> None:
    anchors = extract_anchors_from_turn(
        "Add multi-tenant support next.",
        "Noted for the estimate.",
        ProjectMetadata(project_name="Nimbus"),
    )
    assert "project is called Nimbus" in anchors


def test_extract_anchors_locked_decision() -> None:
    anchors = extract_anchors_from_turn(
        "Locked decision: use PostgreSQL for all persistence.",
        "Understood.",
        ProjectMetadata(),
    )
    assert "locked decision: use PostgreSQL for all persistence" in anchors


def test_extract_anchors_switching_phrase() -> None:
    anchors = extract_anchors_from_turn(
        "We are switching to Flutter for the mobile client.",
        "Stack updated.",
        ProjectMetadata(),
    )
    assert "switching to Flutter for the mobile client" in anchors


def test_update_anchors_deduplicates_case_insensitively() -> None:
    existing = ["budget 30000 EUR"]
    merged = update_anchors(
        existing,
        "Confirm budget 30000 EUR still applies.",
        "Yes.",
        ProjectMetadata(),
    )
    assert merged == ["budget 30000 EUR"]


def test_update_anchors_appends_new_entries() -> None:
    merged = update_anchors(
        ["budget 30000 EUR"],
        "Later the budget 80000 EUR was approved.",
        "Updated.",
        ProjectMetadata(),
    )
    assert merged == ["budget 30000 EUR", "budget 80000 EUR"]
