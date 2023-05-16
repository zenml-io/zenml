#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Utils for the ZenML service module."""

from typing import Optional

from zenml.enums import ArtifactType
from zenml.post_execution import get_pipeline
from zenml.services.service import BaseService


def load_last_service_from_step(
    pipeline_name: str,
    step_name: str,
    running: bool = False,
) -> Optional[BaseService]:
    """Get the last service created by the pipeline and step with the given names.

    This function searches backwards through the execution history for a
    named pipeline step and returns the first service instance that it finds
    logged as a step output.

    Args:
        pipeline_name: the name of the pipeline
        step_name: pipeline step name
        running: when this flag is set, the search only returns a running
            service

    Returns:
        A BaseService instance that represents the service or None if no service
        was created during the last execution of the pipeline step.

    Raises:
        KeyError: if the pipeline or step name is not found in the execution.
        RuntimeError: if the artifact is not a service.
    """
    pipeline = get_pipeline(pipeline_name)
    if pipeline is None:
        raise KeyError(f"No pipeline with name `{pipeline_name}` was found")

    for run in reversed(pipeline.runs):
        step = run.get_step(step=step_name)
        for artifact_view in step.outputs.values():
            # filter out anything but service artifacts
            if artifact_view.type == ArtifactType.SERVICE:
                service = artifact_view.read()
                if not isinstance(service, BaseService):
                    raise RuntimeError(
                        f"Artifact `{artifact_view.name}` of type "
                        f"`{artifact_view.type}` is not a service"
                    )
                if not running or service.is_running:
                    return service
    return None
