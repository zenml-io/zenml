from typing import Annotated
from uuid import UUID

from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


def find_artifact_id(
    pipeline_name: str,
    artifact_name: str,
) -> Annotated[UUID, "artifact_id"]:
    pipeline = Client().get_pipeline(pipeline_name)
    latest_run = pipeline.runs[0]
    artifacts = [a for a in latest_run.artifacts if a.name == artifact_name]
    if artifacts:
        return artifacts[0].id
    else:
        raise ValueError(
            f"`{artifact_name}` not found in last run of `{pipeline_name}`"
        )
