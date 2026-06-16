"""Streamlit form interface for software project estimation.

Session 4 changes (latest):
- **Chat UI removed** — no ``stream_estimation``, no direct ``llm_service`` imports.
- **Typed form** — ``st.form`` collects ``request_form.EstimationRequest`` fields
  and POSTs to ``POST /api/v1/estimate`` via httpx.
- **Sidebar** — CAG slider and legacy ``build_system_prompt`` previews replaced
  with read-only Jinja renders (``render_estimation_prompt`` via helpers).
- **Session state** — ``last_preview_request`` feeds the sidebar; ``last_estimation``
  persists the API response across reruns.

The UI stays decoupled from the LLM layer: only the API contract and prompt
templates need to change when estimation logic evolves.
"""

from enum import Enum

import httpx
import streamlit as st
from pydantic import ValidationError

from app.config import Settings, get_settings
# Reuse the same Pydantic models as the API so form fields and JSON payload
# stay in sync — no duplicate field definitions in the UI layer.
from app.schemas.request_form import (
    DetailLevel,
    EstimationRequest,
    EstimationResponse,
    OutputFormat,
    ProjectType,
)
from app.ui import streamlit_helpers

# FastAPI must be running separately (uvicorn app.main:app). Hardcoded for now;
# a future iteration can move this to Settings / .env.
API_ESTIMATE_URL = "http://localhost:8000/api/v1/estimate"


def _enum_label(member: Enum) -> str:
    return member.value.replace("_", " ").title()


def bootstrap() -> Settings:
    """Configure page, load settings, and initialise session state.
    Calls st.stop() on configuration errors — nothing after this can fail."""
    st.set_page_config(page_title="Software Estimator", layout="wide")
    st.title("Software Estimator")
    st.caption(
        "Describe your project below to generate a software estimation "
        "using versioned Jinja2 prompts."
    )

    try:
        settings: Settings = get_settings()
    except ValueError as exc:
        st.error(
            f"**LLM configuration error:** {exc}\n\n"
            "Copy `.env.example` to `.env` in the `estimator/` folder and set the "
            "API key matching your `LLM_PROVIDER`. Restart Streamlit after editing `.env`."
        )
        st.stop()

    for key, value in streamlit_helpers.initial_session_state().items():
        if key not in st.session_state:
            st.session_state[key] = value

    # API response persisted outside the form so reruns (e.g. sidebar expand) do
    # not clear the rendered estimation.
    if "last_estimation" not in st.session_state:
        st.session_state.last_estimation = None

    return settings


def render_sidebar(settings: Settings) -> None:
    """Render the sidebar configuration panel and Jinja prompt previews."""
    with st.sidebar:
        st.header("Configuration")
        st.text_input("Provider", value=settings.LLM_PROVIDER, disabled=True)
        st.text_input("Model", value=settings.LLM_MODEL, disabled=True)

        # Preview uses the last submitted request, or a placeholder until first submit.
        # Form widget values are not readable outside st.form on partial reruns.
        preview_request = streamlit_helpers.preview_request(
            st.session_state.last_preview_request,
        )
        system_prompt, user_prompt = streamlit_helpers.sidebar_prompt_preview(preview_request)

        with st.expander("System prompt", expanded=False):
            st.text_area(
                "System prompt",
                value=system_prompt,
                height=300,
                disabled=True,
                label_visibility="collapsed",
            )

        with st.expander("User prompt", expanded=False):
            st.text_area(
                "User prompt",
                value=user_prompt,
                height=200,
                disabled=True,
                label_visibility="collapsed",
            )


def render_form() -> None:
    """Render the estimation form and POST to the API on submit."""
    # st.form batches widget changes: values are only sent on submit, avoiding
    # partial reruns while the user is still filling in the fields.
    # clear_on_submit=False keeps the description visible after submission.
    with st.form("estimation_form", clear_on_submit=False):
        description = st.text_area(
            "Project description",
            placeholder="Describe the project (minimum 20 characters)...",
            height=200,
        )
        # Selectbox options are driven by the schema enums so new values only
        # need to be added in request_form.py.
        project_type = st.selectbox(
            "Project type",
            options=list(ProjectType),
            format_func=_enum_label,
        )
        detail_level = st.selectbox(
            "Detail level",
            options=list(DetailLevel),
            format_func=_enum_label,
        )
        output_format = st.selectbox(
            "Output format",
            options=list(OutputFormat),
            format_func=_enum_label,
        )
        submitted = st.form_submit_button("Estimate")

    if submitted:
        # Client-side validation mirrors the API — fail fast before httpx.post.
        try:
            request = EstimationRequest(
                description=description,
                project_type=project_type,
                detail_level=detail_level,
                output_format=output_format,
            )
        except ValidationError as exc:
            for err in exc.errors():
                loc = " → ".join(str(part) for part in err["loc"])
                st.error(f"**{loc}:** {err['msg']}")
            return

        # Update sidebar previews even if the API call fails later.
        st.session_state.last_preview_request = request

        with st.spinner("Generating estimation..."):
            try:
                # mode="json" serialises enums to their string values (e.g.
                # "web_saas") so the payload matches the API JSON contract.
                response = httpx.post(
                    API_ESTIMATE_URL,
                    json=request.model_dump(mode="json"),
                    timeout=120.0,
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text.strip() or exc.response.reason_phrase
                st.error(f"**Estimation failed ({exc.response.status_code}):** {detail}")
                return
            except httpx.RequestError as exc:
                st.error(f"**Could not reach API:** {exc}")
                return

        try:
            result = EstimationResponse.model_validate(response.json())
        except ValidationError as exc:
            st.error(f"**Invalid API response:** {exc}")
            return

        st.session_state.last_estimation = result

    # Render outside the submit branch so the result survives sidebar reruns.
    if st.session_state.last_estimation is not None:
        result: EstimationResponse = st.session_state.last_estimation
        st.caption(f"Prompt version: {result.prompt_version}")
        st.markdown(result.text)


def main() -> None:
    settings = bootstrap()
    render_sidebar(settings)
    render_form()


if __name__ == "__main__":
    main()
