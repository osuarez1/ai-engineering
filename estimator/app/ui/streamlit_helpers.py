"""Pure helpers for the Streamlit form UI — no Streamlit imports.

Session 4 replaced the chat-era helpers (``to_api_messages``, ``build_last_call``,
``sidebar_system_prompt`` / ``sidebar_cag_context`` backed by ``build_system_prompt``)
with a thin preview layer over ``render_estimation_prompt``. The form POSTs to the
API via HTTP; these helpers only drive sidebar prompt previews and session defaults.
"""

from app.prompts.loader import render_estimation_prompt
from app.schemas.request_form import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)

# Keep in sync with estimations.PROMPT_VERSION and the loader default.
PROMPT_VERSION = "v1"

# Placeholder shown in the sidebar before the user submits the form for the first time.
DEFAULT_PREVIEW_REQUEST = EstimationRequest(
    description=(
        "Submit the form with your project description to preview the exact "
        "system and user prompts sent to the model."
    ),
    project_type=ProjectType.WEB_SAAS,
    detail_level=DetailLevel.MEDIUM,
    output_format=OutputFormat.PHASES_TABLE,
)


def initial_session_state() -> dict[str, EstimationRequest | None]:
    """Return the initial Streamlit session_state keys for the form UI."""
    return {
        # Updated on valid form submit so sidebar previews match the last request.
        "last_preview_request": None,
    }


def preview_request(
    last_request: EstimationRequest | None,
) -> EstimationRequest:
    """Pick the request used for sidebar prompt previews."""
    return last_request or DEFAULT_PREVIEW_REQUEST


def sidebar_prompt_preview(
    request: EstimationRequest,
    version: str = PROMPT_VERSION,
) -> tuple[str, str]:
    """Render the system and user prompts shown in the sidebar."""
    return render_estimation_prompt(request, version=version)
