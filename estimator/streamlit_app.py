"""Streamlit conversational interface for software project estimation."""

import streamlit as st

from app.config import Settings, get_settings

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
