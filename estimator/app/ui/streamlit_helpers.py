"""Pure helpers for the Streamlit form UI — no Streamlit imports.

Session 4 replaced the chat-era helpers (``to_api_messages``, ``build_last_call``,
``sidebar_system_prompt`` / ``sidebar_cag_context`` backed by ``build_system_prompt``)
with a thin preview layer over ``render_estimation_prompt``. The form POSTs to the
API via HTTP; these helpers only drive sidebar prompt previews and session defaults.

Prompt version selection (v1 vs v2) lives in ``streamlit_app`` session state. These
helpers expose the supported values and render previews for the active version so the
sidebar matches what the next API call will send as ``?prompt_version=``.
"""

from app.prompts.loader import render_estimation_prompt
from app.schemas.request_form import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)

# Default template set — keep aligned with estimations.DEFAULT_PROMPT_VERSION.
DEFAULT_PROMPT_VERSION = "v1"
# Must match estimations.PromptVersion; adding v3 requires a new estimation/v3/ folder
# and updating the API Literal before exposing it here.
SUPPORTED_PROMPT_VERSIONS = ("v1", "v2")

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


def initial_session_state() -> dict[str, EstimationRequest | str | None]:
    """Return the initial Streamlit session_state keys for the form UI."""
    return {
        # Updated on valid form submit so sidebar previews match the last request.
        "last_preview_request": None,
        # Drives sidebar previews and the ?prompt_version= query param on submit.
        "prompt_version": DEFAULT_PROMPT_VERSION,
    }


def preview_request(
    last_request: EstimationRequest | None,
) -> EstimationRequest:
    """Pick the request used for sidebar prompt previews."""
    return last_request or DEFAULT_PREVIEW_REQUEST


def sidebar_prompt_preview(
    request: EstimationRequest,
    version: str = DEFAULT_PROMPT_VERSION,
) -> tuple[str, str]:
    """Render the system and user prompts shown in the sidebar.

    Uses the same loader path as the API so instructors can compare v1 vs v2
    tone and few-shot examples before submitting the form.
    """
    return render_estimation_prompt(request, version=version)
