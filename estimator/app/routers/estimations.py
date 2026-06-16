"""Estimation API router — form-based ``POST /estimate``.

Session 4 replaced the transcription payload (``schemas/estimation.py``) with a
typed project description (``schemas/request_form.py``). The endpoint no longer
runs preprocessing, CAG injection, or structural validation; prompts and
few-shot examples are rendered by ``app/prompts/loader.py``.
"""

import structlog
from fastapi import APIRouter, HTTPException

from app.schemas.request_form import EstimationRequest, EstimationResponse
from app.services.llm_service import LLMServiceError, generate_estimation_from_request

log = structlog.get_logger()

router = APIRouter(prefix="/api/v1", tags=["estimations"])

# Single switch point for prompt template version; passed through to the loader.
PROMPT_VERSION = "v1"


@router.post("/estimate", response_model=EstimationResponse)
async def create_estimation(request: EstimationRequest) -> EstimationResponse:
    """Receive a project description and return a software project estimation."""
    try:
        result = generate_estimation_from_request(request, version=PROMPT_VERSION)
    except LLMServiceError as exc:
        log.error("estimation_endpoint_error", error=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    # Response exposes only text + prompt_version; extra LLM metadata stays internal.
    return EstimationResponse(
        text=result["text"],
        prompt_version=result["prompt_version"],
    )
