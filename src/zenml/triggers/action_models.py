from typing import List
from uuid import UUID

from pydantic import BaseModel


class Action(BaseModel):
    """BaseModel for all Actions"""


# Just to help design the abstraction, a concrete Action
class PipelineRunAction(Action):
    """Model for all PipelineRunActions."""
    # Needed to run
    pipeline_build_id: UUID

    # For the frontend
    pipeline_name: str
    pipeline_id: UUID

    # Future considerations
    # stack_id: UUID
    # run_configuration