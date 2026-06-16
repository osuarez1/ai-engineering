"""Streamlit form interface for software project estimation.

Replaces the previous chat UI: the client now collects structured input via
st.form, validates it with the shared Pydantic schema (request_form.py), and
calls the FastAPI service over HTTP instead of importing llm_service directly.
This decouples the UI from the LLM layer so the API contract can evolve
independently (e.g. structured responses in a later session).
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
        "using Cache Augmented Generation (CAG)."
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

    if "opts" not in st.session_state:
        st.session_state.opts = streamlit_helpers.default_generation_options()

    # Persist the last API response across reruns (e.g. when the sidebar slider
    # triggers a rerun) so the estimation text does not disappear from the page.
    if "last_estimation" not in st.session_state:
        st.session_state.last_estimation = None

    return settings


def render_sidebar(settings: Settings) -> None:
    """Render the sidebar configuration panel and update session opts in place."""
    with st.sidebar:
        st.header("Configuration")
        st.text_input("Provider", value=settings.LLM_PROVIDER, disabled=True)
        st.text_input("Model", value=settings.LLM_MODEL, disabled=True)
        st.session_state.opts.num_examples = st.slider(
            "CAG examples",
            min_value=0,
            max_value=5,
            value=st.session_state.opts.num_examples,
        )

        with st.expander("System prompt", expanded=False):
            st.text_area(
                "System prompt",
                value=streamlit_helpers.sidebar_system_prompt(st.session_state.opts),
                height=300,
                disabled=True,
                label_visibility="collapsed",
            )

        with st.expander("CAG examples", expanded=False):
            st.text_area(
                "CAG examples",
                value=streamlit_helpers.sidebar_cag_context(st.session_state.opts),
                height=300,
                disabled=True,
                label_visibility="collapsed",
            )

        _render_last_call_metrics()


def _render_last_call_metrics() -> None:
    st.subheader("Last call")
    if not st.session_state.last_call:
        st.caption("No estimation calls yet.")
        return

    last_call = st.session_state.last_call
    st.text_input("Call model", value=str(last_call.get("model", "")), disabled=True)
    col_in, col_out = st.columns(2)
    col_in.metric("Input tokens", last_call.get("input_tokens", 0))
    col_out.metric("Output tokens", last_call.get("output_tokens", 0))
    st.metric("Latency (ms)", last_call.get("latency_ms", 0))


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
        # Pydantic validates min/max length and required fields before any HTTP
        # call — same rules the API will enforce once it adopts this schema.
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

        # Response is free-form text for now; EstimationResponse will gain
        # structured fields in a later session once the API contract matures.
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
