#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Utilities for caching."""

import hashlib
from typing import TYPE_CHECKING, Mapping, Optional
from uuid import UUID

from zenml.client import Client
from zenml.constants import CODE_HASH_PARAMETER_NAME
from zenml.enums import ExecutionStatus, SorterOps
from zenml.logger import get_logger
from zenml.orchestrators import step_run_utils

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.config.step_configurations import Step
    from zenml.models import (
        ArtifactVersionResponse,
        PipelineRunResponse,
        PipelineSnapshotResponse,
        StepRunResponse,
    )
    from zenml.stack import Stack


logger = get_logger(__name__)


def generate_cache_key(
    step: "Step",
    input_artifacts: Mapping[str, "ArtifactVersionResponse"],
    artifact_store: "BaseArtifactStore",
    project_id: "UUID",
) -> str:
    """Generates a cache key for a step run.

    If the cache key is the same for two step runs, we conclude that the step
    runs are identical and can be cached.

    The cache key is a MD5 hash of:
    - the project ID,
    - the artifact store ID and path,
    - the source code that defines the step,
    - the parameters of the step,
    - the names and IDs of the input artifacts of the step,
    - the names and source codes of the output artifacts of the step,
    - the source codes of the output materializers of the step.
    - additional custom caching parameters of the step.
    - the environment variables defined for the step.
    - the secrets defined for the step.

    Args:
        step: The step to generate the cache key for.
        input_artifacts: The input artifacts for the step.
        artifact_store: The artifact store of the active stack.
        project_id: The ID of the active project.

    Returns:
        A cache key.
    """
    cache_policy = step.config.cache_policy
    hash_ = hashlib.md5()  # nosec

    # Project ID
    hash_.update(project_id.bytes)

    # Artifact store ID and path
    hash_.update(artifact_store.id.bytes)
    hash_.update(artifact_store.path.encode())

    if artifact_store.custom_cache_key:
        hash_.update(artifact_store.custom_cache_key)

    # Step source. This currently only uses the string representation of the
    # source (e.g. my_module.step_class) instead of the full source to keep
    # the caching behavior of previous versions and to not invalidate caching
    # when committing some unrelated files
    hash_.update(step.spec.source.import_path.encode())

    if cache_policy.include_step_parameters:
        for key, value in sorted(step.config.parameters.items()):
            hash_.update(key.encode())
            hash_.update(str(value).encode())

    # Input artifacts
    for name, artifact_version in input_artifacts.items():
        if name in (cache_policy.ignored_inputs or []):
            continue

        hash_.update(name.encode())

        if (
            artifact_version.content_hash
            and cache_policy.include_artifact_values
        ):
            hash_.update(artifact_version.content_hash.encode())
        elif cache_policy.include_artifact_ids:
            hash_.update(artifact_version.id.bytes)

    # Output artifacts and materializers
    for name, output in step.config.outputs.items():
        hash_.update(name.encode())
        for source in output.materializer_source:
            hash_.update(source.import_path.encode())

    # Custom caching parameters
    for key, value in sorted(step.config.caching_parameters.items()):
        if (
            key == CODE_HASH_PARAMETER_NAME
            and not cache_policy.include_step_code
        ):
            continue

        hash_.update(key.encode())
        hash_.update(str(value).encode())

    # User-defined environment variables
    for key, value in sorted(step.config.environment.items()):
        hash_.update(key.encode())
        hash_.update(str(value).encode())

    # User-defined secrets
    for secret_name_or_id in sorted([str(s) for s in step.config.secrets]):
        hash_.update(secret_name_or_id.encode())

    return hash_.hexdigest()


def get_cached_step_run(cache_key: str) -> Optional["StepRunResponse"]:
    """If a given step can be cached, get the corresponding existing step run.

    A step run can be cached if there is an existing step run in the same
    project which has the same cache key and was successfully executed.

    Args:
        cache_key: The cache key of the step.

    Returns:
        The existing step run if the step can be cached, otherwise None.
    """
    client = Client()

    cache_candidates = client.list_run_steps(
        project=client.active_project.id,
        cache_key=cache_key,
        status=ExecutionStatus.COMPLETED,
        sort_by=f"{SorterOps.DESCENDING}:created",
        size=1,
    ).items

    if cache_candidates:
        return cache_candidates[0]
    return None


def create_cached_step_runs_and_prune_snapshot(
    snapshot: "PipelineSnapshotResponse",
    pipeline_run: "PipelineRunResponse",
    stack: "Stack",
) -> bool:
    """Create cached step runs and prune the cached steps from the snapshot.

    Args:
        snapshot: The pipeline snapshot.
        pipeline_run: The pipeline run for which to create the step runs.
        stack: The stack on which the pipeline run is happening.

    Returns:
        Whether an actual pipeline run is still required.
    """
    cached_invocations = step_run_utils.create_cached_step_runs(
        snapshot=snapshot,
        pipeline_run=pipeline_run,
        stack=stack,
    )

    for invocation_id in cached_invocations:
        # Remove the cached step invocations from the snapshot so
        # the orchestrator does not try to run them
        snapshot.step_configurations.pop(invocation_id)

    for step in snapshot.step_configurations.values():
        for invocation_id in cached_invocations:
            if invocation_id in step.spec.upstream_steps:
                step.spec.upstream_steps.remove(invocation_id)

    if len(snapshot.step_configurations) == 0:
        # All steps were cached, we update the pipeline run status and
        # don't actually use the orchestrator to run the pipeline
        logger.info("All steps of the pipeline run were cached.")
        return False

    return True
