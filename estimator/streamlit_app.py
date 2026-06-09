"""Streamlit conversational interface for software project estimation."""

import time

import streamlit as st

from app.config import Settings, get_settings
from app.services.llm_service import LLMServiceError, stream_estimation
from app.ui import streamlit_helpers


def bootstrap() -> Settings:
    """Configure page, load settings, and initialise session state.
    Calls st.stop() on configuration errors — nothing after this can fail."""
    st.set_page_config(page_title="Software Estimator", layout="wide")
    st.title("Software Estimator")
    st.caption(
        "Paste a meeting transcript in the chat to generate a software project "
        "estimation using Cache Augmented Generation (CAG)."
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


def render_chat() -> None:
    """Render chat history, handle new input, and stream the assistant response."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if not (prompt := st.chat_input("Paste a meeting transcript or ask a follow-up...")):
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    api_messages = streamlit_helpers.to_api_messages(st.session_state.messages)
    meta: dict = {}
    t0 = time.perf_counter()

    with st.chat_message("assistant"):
        try:
            full_text = st.write_stream(
                stream_estimation(api_messages, st.session_state.opts, meta=meta)
            )
        except LLMServiceError as exc:
            st.error(f"**Estimation failed:** {exc}")
            return

    latency_ms = int((time.perf_counter() - t0) * 1000)
    st.session_state.last_call = streamlit_helpers.build_last_call(meta, latency_ms=latency_ms)
    st.session_state.messages.append({"role": "assistant", "content": full_text})


def main() -> None:
    settings = bootstrap()
    render_sidebar(settings)
    render_chat()


if __name__ == "__main__":
    main()
