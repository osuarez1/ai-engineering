"""Streamlit conversational interface for software project estimation."""

import streamlit as st

st.set_page_config(page_title="Software Estimator", layout="wide")

st.title("Software Estimator")
st.caption(
    "Paste a meeting transcript in the chat to generate a software project estimation "
    "using Cache Augmented Generation (CAG)."
)
