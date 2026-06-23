"""Jinja2 prompt loader for versioned estimation templates.

Templates live under ``estimation/<version>/`` (e.g. ``v1/system.j2``). The
``version`` parameter is the only switch needed to adopt a new prompt set
without changing call sites in the LLM service or API router.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.schemas.request_form import EstimationRequest
from app.sessions import ProjectMetadata

# Parent of version folders — adding v2 means a new estimation/v2/ directory only.
_ESTIMATION_ROOT = Path(__file__).parent / "estimation"


def _get_environment(version: str) -> Environment:
    # Each version folder is the loader root so system.j2 can {% include "examples.j2" %}
    # with a relative path, without hard-coding the version inside templates.
    template_dir = _ESTIMATION_ROOT / version
    if not template_dir.is_dir():
        raise ValueError(f"Unknown prompt version: {version}")
    return Environment(
        loader=FileSystemLoader(template_dir),
        # Fail fast on typos or missing context keys instead of rendering empty strings.
        undefined=StrictUndefined,
        # Strip whitespace introduced by Jinja block tags ({% if %}, {% include %}, etc.).
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _build_template_context(
    request: EstimationRequest,
    project_metadata: ProjectMetadata | None = None,
) -> dict:
    context = request.model_dump(mode="json")
    if project_metadata is None:
        context["project_metadata"] = None
    else:
        context["project_metadata"] = project_metadata.model_dump(mode="json")
    return context


def render_estimation_prompt(
    request: EstimationRequest,
    version: str = "v1",
) -> tuple[str, str]:
    """Render the system and user prompts for an estimation request.

    Returns ``(system, user)`` ready to pass as the two message roles to the LLM.
    """
    env = _get_environment(version)
    context = _build_template_context(request)
    system = env.get_template("system.j2").render(**context)
    user = env.get_template("user.j2").render(**context)
    return system, user


def render_session_system_prompt(
    request: EstimationRequest,
    project_metadata: ProjectMetadata,
    *,
    version: str = "v2",
) -> str:
    """Render the system prompt for a conversational session turn.

    Injects the current ``project_metadata`` block when facts are known.
    """
    env = _get_environment(version)
    context = _build_template_context(request, project_metadata)
    return env.get_template("system.j2").render(**context)


def render_session_user_prompt(
    request: EstimationRequest,
    *,
    version: str = "v2",
) -> str:
    """Render the user prompt for a conversational session turn."""
    env = _get_environment(version)
    context = _build_template_context(request)
    return env.get_template("user.j2").render(**context)
