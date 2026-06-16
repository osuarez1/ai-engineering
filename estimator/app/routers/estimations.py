"""Estimation API router — form-based ``POST /estimate``.

Session 4 replaced the transcription payload (``schemas/estimation.py``) with a
typed project description (``schemas/request_form.py``). The endpoint no longer
runs preprocessing, CAG injection, or structural validation; prompts and
few-shot examples are rendered by ``app/prompts/loader.py``.

Prompt versioning (``?prompt_version=v1|v2``) selects which ``estimation/<version>/``
template folder the loader renders. Default is v1 so existing clients keep working;
v2 is an alternate tone and few-shot set for live A/B comparison in demos.
"""

from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException, Query

from app.schemas.request_form import EstimationRequest, EstimationResponse
from app.services.llm_service import LLMServiceError, generate_estimation_from_request

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["estimations"])

# Default template set — keep aligned with streamlit_helpers.DEFAULT_PROMPT_VERSION.
DEFAULT_PROMPT_VERSION = "v1"
# Literal gives OpenAPI enum docs and automatic 422 for unsupported values (e.g. v99).
PromptVersion = Literal["v1", "v2"]


@router.post("/estimate", response_model=EstimationResponse)
async def create_estimation(
    request: EstimationRequest,
    prompt_version: PromptVersion = Query(
        DEFAULT_PROMPT_VERSION,
        description="Jinja prompt template set under app/prompts/estimation/",
    ),
) -> EstimationResponse:
    """Receive a project description and return a software project estimation."""
    try:
        # Version is forwarded to the loader; no prompt logic lives in the router.
        result = generate_estimation_from_request(request, version=prompt_version)
    except LLMServiceError as exc:
        log.error("estimation_endpoint_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    # Response exposes only text + prompt_version so callers can confirm which
    # template set produced the estimate; LLM usage/latency stay internal for now.
    return EstimationResponse(
        text=result["text"],
        prompt_version=result["prompt_version"],
    )
