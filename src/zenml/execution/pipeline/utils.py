#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Pipeline execution utilities."""

import contextvars
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generator,
    Optional,
    Union,
)

from zenml.client import Client
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.exceptions import RunMonitoringError
from zenml.logger import get_logger
from zenml.models import (
    PipelineRunResponse,
    PipelineSnapshotResponse,
)
from zenml.orchestrators.publish_utils import publish_failed_pipeline_run
from zenml.stack import Stack

if TYPE_CHECKING:
    StepConfigurationUpdateOrDict = Union[
        Dict[str, Any], StepConfigurationUpdate
    ]

logger = get_logger(__name__)


_prevent_pipeline_execution = contextvars.ContextVar(
    "prevent_pipeline_execution", default=False
)


def should_prevent_pipeline_execution() -> bool:
    """Whether to prevent pipeline execution.

    Returns:
        Whether to prevent pipeline execution.
    """
    return _prevent_pipeline_execution.get()


@contextmanager
def prevent_pipeline_execution() -> Generator[None, None, None]:
    """Context manager to prevent pipeline execution.

    Yields:
        None.
    """
    token = _prevent_pipeline_execution.set(True)
    try:
        yield
    finally:
        _prevent_pipeline_execution.reset(token)


def submit_pipeline(
    snapshot: "PipelineSnapshotResponse",
    stack: "Stack",
    placeholder_run: Optional["PipelineRunResponse"] = None,
) -> None:
    """Submit a snapshot for execution.

    Args:
        snapshot: The snapshot to submit.
        stack: The stack on which to submit the snapshot.
        placeholder_run: An optional placeholder run for the snapshot.

    # noqa: DAR401
    Raises:
        BaseException: Any exception that happened while submitting or running
            (in case it happens synchronously) the pipeline.
    """
    # Prevent execution of nested pipelines which might lead to
    # unexpected behavior
    with prevent_pipeline_execution():
        try:
            stack.prepare_pipeline_submission(snapshot=snapshot)
            stack.submit_pipeline(
                snapshot=snapshot,
                placeholder_run=placeholder_run,
            )
        except RunMonitoringError as e:
            # Don't mark the run as failed if the error happened during
            # monitoring of the run.
            raise e.original_exception from None
        except BaseException as e:
            if (
                placeholder_run
                and not Client()
                .get_pipeline_run(placeholder_run.id, hydrate=False)
                .status.is_finished
            ):
                # We failed during/before the submission of the run, so we mark
                # the run as failed if it's still in an unfinished state.
                publish_failed_pipeline_run(placeholder_run.id)

            raise e
