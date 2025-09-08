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
"""Default step runtime implementation (blocking publish, standard persistence)."""

import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type

from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact
from zenml.client import Client
from zenml.enums import ArtifactSaveType
from zenml.execution.step_runtime import BaseStepRuntime
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.materializers.materializer_registry import materializer_registry
from zenml.models import ArtifactVersionResponse
from zenml.steps.step_context import get_step_context
from zenml.utils import materializer_utils, source_utils, tag_utils
from zenml.utils.typing_utils import get_origin, is_union

if TYPE_CHECKING:
    from zenml.artifact_stores import BaseArtifactStore
    from zenml.config.step_configurations import Step
    from zenml.materializers.base_materializer import BaseMaterializer
    from zenml.models import PipelineRunResponse, StepRunResponse
    from zenml.models.v2.core.step_run import StepRunInputResponse
    from zenml.stack import Stack
    from zenml.steps.utils import OutputSignature

logger = get_logger(__name__)


class DefaultStepRuntime(BaseStepRuntime):
    """Default runtime delegating to existing ZenML utilities.

    This keeps current behavior intact while providing a single place for the
    step runner to call into. It intentionally mirrors logic from
    `step_runner.py` and `orchestrators/input_utils.py`.
    """

    # --- Input Resolution ---
    def resolve_step_inputs(
        self,
        *,
        step: "Step",
        pipeline_run: "PipelineRunResponse",
        step_runs: Optional[Dict[str, "StepRunResponse"]] = None,
    ) -> Dict[str, "StepRunInputResponse"]:
        """Resolve step inputs.

        Args:
            step: The step to resolve inputs for.
            pipeline_run: The pipeline run to resolve inputs for.
            step_runs: Optional map of step runs.

        Returns:
            Mapping from input name to resolved step run input.
        """
        # Local import to avoid circular import issues
        from zenml.orchestrators import input_utils

        return input_utils.resolve_step_inputs(
            step=step, pipeline_run=pipeline_run, step_runs=step_runs
        )

    # --- Artifact Load ---
    def load_input_artifact(
        self,
        *,
        artifact: ArtifactVersionResponse,
        data_type: Type[Any],
        stack: "Stack",
    ) -> Any:
        """Load an input artifact.

        Args:
            artifact: The artifact to load.
            data_type: The data type of the artifact.
            stack: The stack to load the artifact from.

        Returns:
            The loaded Python value for the input artifact.
        """
        # Skip materialization for `UnmaterializedArtifact`.
        if data_type == UnmaterializedArtifact:
            return UnmaterializedArtifact(
                **artifact.get_hydrated_version().model_dump()
            )

        if data_type in (None, Any) or is_union(get_origin(data_type)):
            # Use the stored artifact datatype when function annotation is not specific
            data_type = source_utils.load(artifact.data_type)

        materializer_class: Type[BaseMaterializer] = (
            source_utils.load_and_validate_class(
                artifact.materializer, expected_class=BaseMaterializer
            )
        )

        def _load(artifact_store: "BaseArtifactStore") -> Any:
            materializer: BaseMaterializer = materializer_class(
                uri=artifact.uri, artifact_store=artifact_store
            )
            materializer.validate_load_type_compatibility(data_type)
            return materializer.load(data_type=data_type)

        if artifact.artifact_store_id == stack.artifact_store.id:
            stack.artifact_store._register()
            return _load(artifact_store=stack.artifact_store)
        else:
            # Local import to avoid circular import issues
            from zenml.orchestrators.utils import (
                register_artifact_store_filesystem,
            )

            with register_artifact_store_filesystem(
                artifact.artifact_store_id
            ) as target_store:
                return _load(artifact_store=target_store)

    # --- Artifact Store ---
    def store_output_artifacts(
        self,
        *,
        output_data: Dict[str, Any],
        output_materializers: Dict[str, Tuple[Type["BaseMaterializer"], ...]],
        output_artifact_uris: Dict[str, str],
        output_annotations: Dict[str, "OutputSignature"],
        artifact_metadata_enabled: bool,
        artifact_visualization_enabled: bool,
    ) -> Dict[str, ArtifactVersionResponse]:
        """Store output artifacts.

        Args:
            output_data: The output data.
            output_materializers: The output materializers.
            output_artifact_uris: The output artifact URIs.
            output_annotations: The output annotations.
            artifact_metadata_enabled: Whether artifact metadata is enabled.
            artifact_visualization_enabled: Whether artifact visualization is enabled.

        Returns:
            Mapping from output name to stored artifact version.

        Raises:
            RuntimeError: If artifact batch creation fails after retries or
                the number of responses does not match requests.
        """
        # Apply capture toggles for metadata and visualizations
        artifact_metadata_enabled = artifact_metadata_enabled and bool(
            getattr(self, "_metadata_enabled", True)
        )
        artifact_visualization_enabled = (
            artifact_visualization_enabled
            and bool(getattr(self, "_visualizations_enabled", True))
        )

        step_context = get_step_context()
        artifact_requests: List[Any] = []

        for output_name, return_value in output_data.items():
            data_type = type(return_value)
            materializer_classes = output_materializers[output_name]
            if materializer_classes:
                materializer_class: Type[BaseMaterializer] = (
                    materializer_utils.select_materializer(
                        data_type=data_type,
                        materializer_classes=materializer_classes,
                    )
                )
            else:
                # Runtime selection if no explicit materializer recorded
                default_materializer_source = (
                    step_context.step_run.config.outputs[
                        output_name
                    ].default_materializer_source
                    if step_context and step_context.step_run
                    else None
                )

                if default_materializer_source:
                    default_materializer_class: Type[BaseMaterializer] = (
                        source_utils.load_and_validate_class(
                            default_materializer_source,
                            expected_class=BaseMaterializer,
                        )
                    )
                    materializer_registry.default_materializer = (
                        default_materializer_class
                    )

                materializer_class = materializer_registry[data_type]

            uri = output_artifact_uris[output_name]
            artifact_config = output_annotations[output_name].artifact_config

            artifact_type = None
            if artifact_config is not None:
                has_custom_name = bool(artifact_config.name)
                version = artifact_config.version
                artifact_type = artifact_config.artifact_type
            else:
                has_custom_name, version = False, None

            # Name resolution mirrors existing behavior
            if has_custom_name:
                artifact_name = output_name
            else:
                if step_context.pipeline_run.pipeline:
                    pipeline_name = step_context.pipeline_run.pipeline.name
                else:
                    pipeline_name = "unlisted"
                step_name = step_context.step_run.name
                artifact_name = f"{pipeline_name}::{step_name}::{output_name}"

            # Collect user metadata and tags
            user_metadata = step_context.get_output_metadata(output_name)
            tags = step_context.get_output_tags(output_name)
            if step_context.pipeline_run.config.tags is not None:
                for tag in step_context.pipeline_run.config.tags:
                    if isinstance(tag, tag_utils.Tag) and tag.cascade is True:
                        tags.append(tag.name)

            # Store artifact data and prepare a request to the server.
            from zenml.artifacts.utils import (
                _store_artifact_data_and_prepare_request,
            )

            artifact_request = _store_artifact_data_and_prepare_request(
                name=artifact_name,
                data=return_value,
                materializer_class=materializer_class,
                uri=uri,
                artifact_type=artifact_type,
                store_metadata=artifact_metadata_enabled,
                store_visualizations=artifact_visualization_enabled,
                has_custom_name=has_custom_name,
                version=version,
                tags=tags,
                save_type=ArtifactSaveType.STEP_OUTPUT,
                metadata=user_metadata,
            )
            artifact_requests.append(artifact_request)

        max_retries = 2
        delay = 1.0

        for attempt in range(max_retries + 1):
            try:
                responses = Client().zen_store.batch_create_artifact_versions(
                    artifact_requests
                )
                if len(responses) != len(artifact_requests):
                    raise RuntimeError(
                        f"Artifact batch creation returned {len(responses)}/{len(artifact_requests)} responses"
                    )
                return dict(zip(output_data.keys(), responses))
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(
                        "Artifact creation attempt %s failed: %s. Retrying in %.1fs...",
                        attempt + 1,
                        e,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= 1.5
                else:
                    logger.error(
                        "Failed to create artifacts after %s attempts: %s. Failing step to avoid inconsistency.",
                        max_retries + 1,
                        e,
                    )
                    raise

        # TODO(beta->prod): Align with server to provide atomic batch create or
        # compensating deletes. Consider idempotent requests and retriable error
        # categories with jittered backoff.
        raise RuntimeError(
            "Artifact creation failed unexpectedly without raising"
        )
