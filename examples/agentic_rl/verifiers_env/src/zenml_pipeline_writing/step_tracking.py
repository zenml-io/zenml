#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Per-rollout step run tracking.

Every rollout becomes a step run of the pipeline run that launched the
trainer: created as RUNNING when the rollout's sandbox opens, finished
when it is torn down, with reward and sandbox id attached as step
metadata. Tracking is opt-in via ``ZENML_PIPELINE_RUN_ID`` (the run to
attach the step runs to). ``ZENML_ROLLOUT_UPSTREAM_STEP`` optionally
names the trainer step invocation so the rollout nodes hang off it in
the run DAG. Every function degrades to a no-op on failure — tracking
must never break a rollout.
"""

import logging
import os
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

if TYPE_CHECKING:
    from zenml.models import PipelineRunResponse

RUN_ID_ENV = "ZENML_PIPELINE_RUN_ID"
UPSTREAM_STEP_ENV = "ZENML_ROLLOUT_UPSTREAM_STEP"
ROLLOUT_STEP_PREFIX = "rollout_"

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_run(run_id: str) -> "PipelineRunResponse":
    """Fetch (once) the pipeline run to attach rollout steps to.

    Args:
        run_id: The pipeline run id.

    Returns:
        The pipeline run.
    """
    from zenml.client import Client

    return Client().get_pipeline_run(UUID(run_id))


def start_rollout_step(name: str) -> Optional[UUID]:
    """Create a running step run for a rollout.

    Args:
        name: The rollout name (verifiers passes the trace id).

    Returns:
        The step run id, or None when tracking is disabled or failed.
    """
    run_id = os.environ.get(RUN_ID_ENV)
    if not run_id:
        return None

    try:
        from zenml.client import Client
        from zenml.config.source import Source, SourceType
        from zenml.config.step_configurations import (
            Step,
            StepConfiguration,
            StepSpec,
        )
        from zenml.enums import ExecutionStatus
        from zenml.models import StepRunRequest
        from zenml.utils.time_utils import utc_now

        run = _get_run(run_id)
        upstream_step = os.environ.get(UPSTREAM_STEP_ENV)
        step_name = f"{ROLLOUT_STEP_PREFIX}{name}"
        config = StepConfiguration(name=step_name, enable_cache=False)
        step_run = Client().zen_store.create_run_step(
            StepRunRequest(
                name=step_name,
                project=run.project_id,
                pipeline_run_id=run.id,
                status=ExecutionStatus.RUNNING,
                start_time=utc_now(),
                dynamic_config=Step(
                    spec=StepSpec(
                        source=Source(
                            module="zenml_pipeline_writing.taskset",
                            attribute="PipelineWritingTask",
                            type=SourceType.USER,
                        ),
                        upstream_steps=[upstream_step]
                        if upstream_step
                        else [],
                        invocation_id=step_name,
                    ),
                    config=config,
                    step_config_overrides=config,
                ),
            )
        )
        return step_run.id
    except Exception as e:
        logger.warning("Failed to create rollout step run `%s`: %s", name, e)
        return None


def finish_rollout_step(step_run_id: UUID, success: bool) -> None:
    """Finish a tracked rollout step run.

    Args:
        step_run_id: The step run to finish.
        success: Whether the rollout was torn down normally.
    """
    try:
        from zenml.orchestrators import publish_utils

        if success:
            publish_utils.publish_successful_step_run(
                step_run_id=step_run_id, output_artifact_ids={}
            )
        else:
            publish_utils.publish_failed_step_run(step_run_id=step_run_id)
    except Exception as e:
        logger.warning(
            "Failed to finish rollout step run `%s`: %s", step_run_id, e
        )


def log_rollout_metadata(step_run_id: UUID, metadata: Dict[str, Any]) -> None:
    """Attach metadata to a tracked rollout step run.

    Args:
        step_run_id: The step run to attach the metadata to.
        metadata: The metadata.
    """
    try:
        from zenml.client import Client
        from zenml.enums import MetadataResourceTypes
        from zenml.models import RunMetadataResource

        Client().create_run_metadata(
            metadata=metadata,
            resources=[
                RunMetadataResource(
                    id=step_run_id, type=MetadataResourceTypes.STEP_RUN
                )
            ],
        )
    except Exception as e:
        logger.warning(
            "Failed to log metadata on rollout step run `%s`: %s",
            step_run_id,
            e,
        )
