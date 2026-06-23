"""Streamlit conversational interface for multi-turn software estimation.

Session 5 replaces the Session 4 typed form with a session-aware client:
- ``POST /sessions`` on first load (``session_id`` in ``st.session_state``)
- ``POST /sessions/{session_id}/estimate`` with transcript + optional attachments
- Sidebar panel showing distilled ``project_metadata`` (memory vs history)
- **New conversation** resets the server session and local state
"""

import httpx
import streamlit as st

from app.config import Settings, get_settings
from app.schemas.session import SessionEstimationResponse
from app.ui import streamlit_helpers

API_BASE = streamlit_helpers.API_BASE_DEFAULT


def bootstrap() -> Settings:
    """Configure page, load settings, and ensure a server session exists."""
    st.set_page_config(page_title="Software Estimator", layout="wide")
    st.title("Software Estimator")
    st.caption(
        "Iterative project estimation with conversational memory. "
        "Each turn refines the estimate; project facts accumulate in the sidebar."
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

    try:
        streamlit_helpers.ensure_session_id(st.session_state, api_base=API_BASE)
    except httpx.HTTPError as exc:
        st.error(f"**Could not create session:** {exc}")
        st.stop()

    return settings


def render_sidebar(settings: Settings) -> None:
    """Render configuration, project metadata, and new-conversation control."""
    with st.sidebar:
        st.header("Configuration")
        st.text_input("Provider", value=settings.LLM_PROVIDER, disabled=True)
        st.text_input("Model", value=settings.LLM_MODEL, disabled=True)
        st.text_input("Session ID", value=st.session_state.session_id, disabled=True)
        st.radio(
            "Prompt version",
            options=list(streamlit_helpers.SUPPORTED_PROMPT_VERSIONS),
            key="prompt_version",
            horizontal=True,
            help="Selects the Jinja template set sent to the session estimate API.",
        )

        with st.expander("Project metadata", expanded=True):
            st.json(st.session_state.project_metadata)

        if st.button("New conversation", type="secondary"):
            try:
                streamlit_helpers.reset_conversation_state(
                    st.session_state,
                    api_base=API_BASE,
                )
            except httpx.HTTPError as exc:
                st.error(f"**Could not start a new session:** {exc}")
            else:
                st.rerun()


def render_conversation() -> None:
    """Render transcript input, attachments, and the latest estimation."""
    transcript = st.text_area(
        "Transcript",
        placeholder="Describe the project or add detail for this turn (minimum 20 characters)...",
        height=200,
    )
    uploads = st.file_uploader(
        "Attachments (optional)",
        type=["pdf", "docx"],
        accept_multiple_files=True,
        help="PDF or Word documents with supplementary specifications.",
    )

    if st.button("Estimate", type="primary"):
        validation_error = streamlit_helpers.validate_transcript(transcript)
        if validation_error:
            st.error(f"**{validation_error}**")
            return

        attachments = streamlit_helpers.prepare_attachment_payloads(uploads)

        with st.spinner("Generating estimation..."):
            try:
                result = streamlit_helpers.submit_session_estimate(
                    st.session_state.session_id,
                    transcript,
                    attachments,
                    api_base=API_BASE,
                    prompt_version=st.session_state.prompt_version,
                )
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text.strip() or exc.response.reason_phrase
                st.error(f"**Estimation failed ({exc.response.status_code}):** {detail}")
                return
            except httpx.RequestError as exc:
                st.error(f"**Could not reach API:** {exc}")
                return

        st.session_state.last_estimation = result
        st.session_state.project_metadata = result.project_metadata.model_dump()

    if st.session_state.last_estimation is not None:
        result: SessionEstimationResponse = st.session_state.last_estimation
        st.caption(f"Prompt version: {result.prompt_version}")
        st.markdown(result.text)


def main() -> None:
    settings = bootstrap()
    render_sidebar(settings)
    render_conversation()


if __name__ == "__main__":
    main()
