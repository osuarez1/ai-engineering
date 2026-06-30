from app.services.metadata_extractor import update_metadata_heuristic
from app.sessions import ProjectMetadata


def test_update_metadata_extracts_project_name() -> None:
    metadata = update_metadata_heuristic(
        ProjectMetadata(),
        "The project is called BookFlow and needs a web app.",
        "I will estimate BookFlow as a SaaS MVP.",
    )
    assert metadata.project_name == "BookFlow"


def test_update_metadata_extracts_team_size() -> None:
    metadata = update_metadata_heuristic(
        ProjectMetadata(),
        "We have 3 full-time engineers available for this build.",
        "With a team of three developers the timeline is realistic.",
    )
    assert metadata.assumed_team_size == 3


def test_update_metadata_merges_technologies() -> None:
    metadata = update_metadata_heuristic(
        ProjectMetadata(mentioned_technologies=["Rails"]),
        "We will add React on the frontend and use PostgreSQL.",
        "Stack assumptions include Rails, React, and PostgreSQL.",
    )
    assert metadata.mentioned_technologies == ["PostgreSQL", "Rails", "React"]


def test_update_metadata_extracts_agreed_scope() -> None:
    metadata = update_metadata_heuristic(
        ProjectMetadata(),
        "Agreed scope: MVP with auth, contacts, roles, and a simple dashboard for admins.",
        "The estimate covers the agreed MVP scope only.",
    )
    assert metadata.agreed_scope is not None
    assert "MVP with auth" in metadata.agreed_scope


def test_update_metadata_preserves_existing_project_name() -> None:
    metadata = update_metadata_heuristic(
        ProjectMetadata(project_name="BookFlow"),
        "The project is called OtherName now maybe?",
        "Still estimating BookFlow.",
    )
    assert metadata.project_name == "BookFlow"


def test_update_metadata_no_changes_returns_same_object() -> None:
    original = ProjectMetadata()
    updated = update_metadata_heuristic(original, "short", "reply")
    assert updated is original


def test_update_metadata_cleans_captured_project_name() -> None:
    metadata = update_metadata_heuristic(
        ProjectMetadata(),
        "The project is called  BookFlow  and needs a web app.",
        "Estimate for BookFlow.",
    )
    assert metadata.project_name == "BookFlow"


def test_update_metadata_extracts_flutter_technology() -> None:
    metadata = update_metadata_heuristic(
        ProjectMetadata(),
        "We are switching to Flutter for the mobile client.",
        "Stack includes Flutter.",
    )
    assert metadata.mentioned_technologies == ["Flutter"]


def test_update_metadata_extracts_budget_eur() -> None:
    metadata = update_metadata_heuristic(
        ProjectMetadata(),
        "The approved budget 30000 EUR covers MVP delivery.",
        "Estimate aligned to budget.",
    )
    assert metadata.budget_eur == 30000


def test_update_metadata_overwrites_budget_eur_on_contradiction() -> None:
    metadata = update_metadata_heuristic(
        ProjectMetadata(budget_eur=30000),
        "Revised budget 80000 EUR after scope expansion.",
        "Updated estimate.",
    )
    assert metadata.budget_eur == 80000
