from uuid import UUID

from zenml.models.v2.core.action import ActionBase


class PipelineRunAction(ActionBase):
    """Model for all PipelineRunActions."""
    # Needed to run
    pipeline_build_id: UUID

    # For the frontend
    pipeline_name: str
    pipeline_id: UUID

    # TODO: Make sure the mutability of the fields above leads to no issues
    def __hash__(self):
        return hash(
            (self.pipeline_build_id, self.pipeline_name, self.pipeline_id)
        )
