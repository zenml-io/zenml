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
"""Pipeline context class."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zenml.config.pipeline_configurations import PipelineConfiguration


def get_pipeline_context() -> "PipelineContext":
    """Get the context of the currently composing pipeline.

    Returns:
        The context of the currently composing pipeline.

    Raises:
        RuntimeError: If no active pipeline is found.
        RuntimeError: If inside a running step.
    """
    from zenml.new.pipelines.pipeline import Pipeline

    if Pipeline.ACTIVE_PIPELINE is None:
        try:
            from zenml.new.steps.step_context import get_step_context

            get_step_context()
        except RuntimeError:
            raise RuntimeError("No active pipeline found.")
        else:
            raise RuntimeError(
                "Inside a step use `from zenml import get_step_context` instead."
            )

    return PipelineContext(
        pipeline_configuration=Pipeline.ACTIVE_PIPELINE.configuration
    )


class PipelineContext:
    """Provides pipeline configuration during its' composition.

    Usage example:

    ```python
    from zenml import get_pipeline_context

    ...

    @pipeline(extra={
        "complex_parameter": ("sklearn.tree","DecisionTreeClassifier")
        }
    )
    def my_pipeline():
        context = get_pipeline_context()

        model = load_model_step(
            model_config=context.extra["complex_parameter"]
        )

        trained_model = train_model(model=model)
    ```
    """

    def __init__(self, pipeline_configuration: "PipelineConfiguration"):
        """Initialize the context of the currently composing pipeline.

        Args:
            pipeline_configuration: The configuration of the pipeline derived from Pipeline class.
        """
        self.name = pipeline_configuration.name
        self.enable_cache = pipeline_configuration.enable_cache
        self.enable_artifact_metadata = (
            pipeline_configuration.enable_artifact_metadata
        )
        self.enable_artifact_visualization = (
            pipeline_configuration.enable_artifact_visualization
        )
        self.enable_step_logs = pipeline_configuration.enable_step_logs
        self.settings = pipeline_configuration.settings
        self.extra = pipeline_configuration.extra
