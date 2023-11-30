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
                "Inside a step use `from zenml import get_step_context` "
                "instead."
            )

    return PipelineContext(
        pipeline_configuration=Pipeline.ACTIVE_PIPELINE.configuration
    )


class PipelineContext:
    """Provides pipeline configuration during it's composition.

    Usage example:

    ```python
    from zenml import get_pipeline_context

    ...

    @pipeline(
        extra={
            "complex_parameter": [
                ("sklearn.tree", "DecisionTreeClassifier"),
                ("sklearn.ensemble", "RandomForestClassifier"),
            ]
        }
    )
    def my_pipeline():
        context = get_pipeline_context()

        after = []
        search_steps_prefix = "hp_tuning_search_"
        for i, model_search_configuration in enumerate(
            context.extra["complex_parameter"]
        ):
            step_name = f"{search_steps_prefix}{i}"
            cross_validation(
                model_package=model_search_configuration[0],
                model_class=model_search_configuration[1],
                id=step_name
            )
            after.append(step_name)
        select_best_model(
            search_steps_prefix=search_steps_prefix,
            after=after,
        )
    ```
    """

    def __init__(self, pipeline_configuration: "PipelineConfiguration"):
        """Initialize the context of the currently composing pipeline.

        Args:
            pipeline_configuration: The configuration of the pipeline derived
                from Pipeline class.
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
        self.model_version = pipeline_configuration.model_version
