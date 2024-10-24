#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Step invocation class definition."""

from typing import TYPE_CHECKING, Any, Dict, Set, Union

from zenml.models import ArtifactVersionResponse

if TYPE_CHECKING:
    from zenml.artifacts.external_artifact import ExternalArtifact
    from zenml.client_lazy_loader import ClientLazyLoader
    from zenml.config.step_configurations import StepConfiguration
    from zenml.model.lazy_load import ModelVersionDataLazyLoader
    from zenml.pipelines.pipeline_definition import Pipeline
    from zenml.steps import BaseStep
    from zenml.steps.entrypoint_function_utils import StepArtifact


class StepInvocation:
    """Step invocation class."""

    def __init__(
        self,
        id: str,
        step: "BaseStep",
        input_artifacts: Dict[str, "StepArtifact"],
        external_artifacts: Dict[
            str, Union["ExternalArtifact", "ArtifactVersionResponse"]
        ],
        model_artifacts_or_metadata: Dict[str, "ModelVersionDataLazyLoader"],
        client_lazy_loaders: Dict[str, "ClientLazyLoader"],
        parameters: Dict[str, Any],
        default_parameters: Dict[str, Any],
        upstream_steps: Set[str],
        pipeline: "Pipeline",
    ) -> None:
        """Initialize a step invocation.

        Args:
            id: The invocation ID.
            step: The step that is represented by the invocation.
            input_artifacts: The input artifacts for the invocation.
            external_artifacts: The external artifacts for the invocation.
            model_artifacts_or_metadata: The model artifacts or metadata for
                the invocation.
            client_lazy_loaders: The client lazy loaders for the invocation.
            parameters: The parameters for the invocation.
            default_parameters: The default parameters for the invocation.
            upstream_steps: The upstream steps for the invocation.
            pipeline: The parent pipeline of the invocation.
        """
        self.id = id
        self.step = step
        self.input_artifacts = input_artifacts
        self.external_artifacts = external_artifacts
        self.model_artifacts_or_metadata = model_artifacts_or_metadata
        self.client_lazy_loaders = client_lazy_loaders
        self.parameters = parameters
        self.default_parameters = default_parameters
        self.upstream_steps = upstream_steps
        self.pipeline = pipeline

    def finalize(self, parameters_to_ignore: Set[str]) -> "StepConfiguration":
        """Finalizes a step invocation.

        It will validate the upstream steps and run final configurations on the
        step that is represented by the invocation.

        Args:
            parameters_to_ignore: Set of parameters that should not be applied
                to the step instance.

        Returns:
            The finalized step configuration.
        """
        from zenml.artifacts.external_artifact_config import (
            ExternalArtifactConfiguration,
        )

        parameters_to_apply = {
            key: value
            for key, value in self.parameters.items()
            if key not in parameters_to_ignore
        }
        parameters_to_apply.update(
            {
                key: value
                for key, value in self.default_parameters.items()
                if key not in parameters_to_ignore
                and key not in parameters_to_apply
            }
        )
        self.step.configure(parameters=parameters_to_apply)

        external_artifacts: Dict[str, ExternalArtifactConfiguration] = {}
        for key, artifact in self.external_artifacts.items():
            if isinstance(artifact, ArtifactVersionResponse):
                external_artifacts[key] = ExternalArtifactConfiguration(
                    id=artifact.id
                )
            else:
                if artifact.value is not None:
                    artifact.upload_by_value()
                external_artifacts[key] = artifact.config

        return self.step._finalize_configuration(
            input_artifacts=self.input_artifacts,
            external_artifacts=external_artifacts,
            model_artifacts_or_metadata=self.model_artifacts_or_metadata,
            client_lazy_loaders=self.client_lazy_loaders,
        )
