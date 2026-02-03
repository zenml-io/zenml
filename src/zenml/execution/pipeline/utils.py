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
from typing import TYPE_CHECKING, Any, Dict, Generator, Optional, Set, Union

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
    from zenml.steps import BaseStep

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


def compute_invocation_id(
    existing_invocations: Set[str],
    step: "BaseStep",
    custom_id: Optional[str] = None,
    allow_suffix: bool = True,
) -> str:
    """Compute the invocation ID.

    Args:
        existing_invocations: The existing invocation IDs.
        step: The step for which to compute the ID.
        custom_id: Custom ID to use for the invocation.
        allow_suffix: Whether a suffix can be appended to the invocation
            ID.

    Raises:
        RuntimeError: If no ID suffix is allowed and an invocation for the
            same ID already exists.
        RuntimeError: If no unique invocation ID can be found.

    Returns:
        The invocation ID.
    """
    base_id = id_ = custom_id or step.name

    if id_ not in existing_invocations:
        return id_

    if not allow_suffix:
        raise RuntimeError(f"Duplicate step ID `{id_}`")

    for index in range(2, 10000):
        id_ = f"{base_id}_{index}"
        if id_ not in existing_invocations:
            return id_

    raise RuntimeError("Unable to find step ID")


def skip_steps_and_prune_snapshot(
    snapshot: "PipelineSnapshotResponse",
    pipeline_run: "PipelineRunResponse",
) -> bool:
    """Skip steps and prune the snapshot.

    Args:
        snapshot: The snapshot to prune.
        pipeline_run: The pipeline run to skip steps for.

    Raises:
        RuntimeError: If the pipeline run is not a replayed run.
        RuntimeError: If a step has an upstream step that is not skipped.
        RuntimeError: If a step run request cannot be populated.

    Returns:
        Whether a pipeline run is still required.
    """
    from zenml.orchestrators.step_run_utils import StepRunRequestFactory

    if snapshot.is_dynamic:
        # In dynamic pipelines, the steps will be skipped at runtime.
        return True

    if not pipeline_run.original_run:
        raise RuntimeError(
            "Unable to skip steps because the pipeline run is not a "
            "replayed run."
        )

    request_factory = StepRunRequestFactory(
        snapshot=snapshot,
        pipeline_run=pipeline_run,
        stack=Client().active_stack,
    )

    steps_to_skip = pipeline_run.config.steps_to_skip
    skipped_invocations = set()

    for invocation_id, step in snapshot.step_configurations.items():
        if invocation_id not in steps_to_skip:
            continue

        for upstream_step in step.spec.upstream_steps:
            if upstream_step not in skipped_invocations:
                raise RuntimeError(
                    f"Unable to skip step `{invocation_id}` because it has an "
                    f"upstream step `{upstream_step}` that is not skipped."
                )

        request = request_factory.create_request(invocation_id)
        try:
            request_factory.populate_request(request)
        except Exception as e:
            # We failed to populate the step run request. This might be due
            # to some input resolution error, or an error importing the step
            # source (there might be some missing dependencies). We do not want
            # the orchestrator to spin up an environment for this step, so we
            # fail early here.
            raise RuntimeError(
                "Failed to populate step run request for step "
                f"`{invocation_id}`: {str(e)}"
            ) from e

        Client().zen_store.create_run_step(request)
        skipped_invocations.add(invocation_id)
        logger.info("Skipping step `%s`.", invocation_id)

    for invocation_id in skipped_invocations:
        # Remove the skipped step invocations from the snapshot so
        # the orchestrator does not try to run them
        snapshot.step_configurations.pop(invocation_id)

    for step in snapshot.step_configurations.values():
        for invocation_id in skipped_invocations:
            if invocation_id in step.spec.upstream_steps:
                step.spec.upstream_steps.remove(invocation_id)

    if len(snapshot.step_configurations) == 0:
        logger.info("All steps were skipped.")
        return False

    return True
