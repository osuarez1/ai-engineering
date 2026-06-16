"""Jinja2 prompt loader for versioned estimation templates.

Templates live under ``estimation/<version>/`` (e.g. ``v1/system.j2``). The
``version`` parameter is the only switch needed to adopt a new prompt set
without changing call sites in the LLM service or API router.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.schemas.request_form import EstimationRequest

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


def render_estimation_prompt(
    request: EstimationRequest,
    version: str = "v1",
) -> tuple[str, str]:
    """Render the system and user prompts for an estimation request.

    Returns ``(system, user)`` ready to pass as the two message roles to the LLM.
    """
    env = _get_environment(version)
    # mode="json" serialises enums to their string values (e.g. "phases_table")
    # so Jinja {% if output_format == "..." %} comparisons work in the templates.
    context = request.model_dump(mode="json")
    system = env.get_template("system.j2").render(**context)
    user = env.get_template("user.j2").render(**context)
    return system, user
