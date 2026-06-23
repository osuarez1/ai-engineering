from enum import Enum
from pydantic import BaseModel, Field

class ProjectType(str, Enum):
    MOBILE_APP = "mobile_app"
    WEB_SAAS = "web_saas"
    INTERNAL_TOOL = "internal_tool"
    DATA_PIPELINE = "data_pipeline"

class DetailLevel(str, Enum):
    SUMMARY = "summary"
    MEDIUM = "medium"
    DETAILED = "detailed"

class OutputFormat(str, Enum):
    PHASES_TABLE = "phases_table"
    LINE_ITEMS = "line_items"
    NARRATIVE = "narrative"


# One historical delivery pulled from examples.j2 and serialised for the optional
# ``reference_projects`` Jinja {% for %} block. ``body`` holds the estimation
# markdown (phases, totals, or narrative prose) after the scope line.
class ReferenceProject(BaseModel):
    name: str
    scope_summary: str
    body: str
    project_type: ProjectType


class EstimationRequest(BaseModel):
    description: str = Field(min_length=20, max_length=2000)
    project_type: ProjectType
    detail_level: DetailLevel
    output_format: OutputFormat
    # None → system prompt keeps static few-shot examples.j2. A non-empty list
    # replaces that block with dynamically rendered similar projects.
    reference_projects: list[ReferenceProject] | None = None

class EstimationResponse(BaseModel):
    text: str
    prompt_version: str