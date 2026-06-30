from app.services.summarizer import MAX_SUMMARY_CHARS, update_summary


def test_update_summary_starts_from_empty() -> None:
    summary = update_summary("", "Need a CRM.", "Here is the estimate.")
    assert summary == "User: Need a CRM.\nAssistant: Here is the estimate."


def test_update_summary_appends_prior_content() -> None:
    prior = "User: Turn one.\nAssistant: Reply one."
    summary = update_summary(prior, "Turn two.", "Reply two.")
    assert summary.startswith(prior)
    assert summary.endswith("User: Turn two.\nAssistant: Reply two.")


def test_update_summary_truncates_to_max_chars() -> None:
    prior = "x" * (MAX_SUMMARY_CHARS - 10)
    summary = update_summary(prior, "y" * 500, "z" * 500)
    assert len(summary) == MAX_SUMMARY_CHARS
    assert summary.endswith("...")


def test_update_summary_truncates_long_turn_snippets() -> None:
    summary = update_summary("", "u" * 500, "a" * 500)
    assert "u" * 400 + "..." in summary
    assert "a" * 400 + "..." in summary


def test_update_summary_preserves_content_under_limit() -> None:
    summary = update_summary("", "short user", "short assistant")
    assert len(summary) < MAX_SUMMARY_CHARS
    assert "short user" in summary
    assert "short assistant" in summary
