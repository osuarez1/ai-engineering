"""Streamlit conversational interface for software project estimation."""

import time

import streamlit as st

from app.config import Settings, get_settings
from app.services.llm_service import LLMServiceError, stream_estimation
from app.ui import streamlit_helpers

st.set_page_config(page_title="Software Estimator", layout="wide")

st.title("Software Estimator")
st.caption(
    "Paste a meeting transcript in the chat to generate a software project estimation "
    "using Cache Augmented Generation (CAG)."
)

try:
    settings: Settings = get_settings()
except ValueError as exc:
    st.error(
        f"**LLM configuration error:** {exc}\n\n"
        "Copy `.env.example` to `.env` in the `estimator/` folder and set the API key "
        "matching your `LLM_PROVIDER`. Restart Streamlit after editing `.env`."
    )
    st.stop()

for key, value in streamlit_helpers.initial_session_state().items():
    if key not in st.session_state:
        st.session_state[key] = value

if "opts" not in st.session_state:
    st.session_state.opts = streamlit_helpers.default_generation_options()

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

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Paste a meeting transcript or ask a follow-up..."):
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
            full_text = ""

    if full_text:
        latency_ms = int((time.perf_counter() - t0) * 1000)
        st.session_state.last_call = streamlit_helpers.build_last_call(meta, latency_ms=latency_ms)
        st.session_state.messages.append({"role": "assistant", "content": full_text})
