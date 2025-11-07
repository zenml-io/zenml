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
"""Dynamic pipeline definition."""

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Type,
)

from pydantic import BaseModel, ConfigDict, create_model

from zenml.client import Client
from zenml.config.source import Source
from zenml.execution.pipeline.utils import (
    should_prevent_pipeline_execution,
)
from zenml.logger import get_logger
from zenml.models import PipelineRunResponse
from zenml.pipelines.pipeline_definition import Pipeline
from zenml.steps.utils import (
    parse_return_type_annotations,
)
from zenml.utils import source_utils

if TYPE_CHECKING:
    from zenml.steps import BaseStep

logger = get_logger(__name__)


class DynamicPipeline(Pipeline):
    """Dynamic pipeline class."""

    def __init__(
        self,
        *args: Any,
        depends_on: Optional[List["BaseStep"]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the pipeline.

        Args:
            *args: Pipeline constructor arguments.
            depends_on: The steps that the pipeline depends on.
            **kwargs: Pipeline constructor keyword arguments.
        """
        super().__init__(*args, **kwargs)
        self._depends_on = depends_on or []
        self._validate_depends_on(self._depends_on)

    def _validate_depends_on(self, depends_on: List["BaseStep"]) -> None:
        """Validates the steps that the pipeline depends on.

        Args:
            depends_on: The steps that the pipeline depends on.

        Raises:
            RuntimeError: If some of the steps in `depends_on` are duplicated.
        """
        static_ids = set()
        for step in depends_on:
            static_id = step._static_id
            if static_id in static_ids:
                raise RuntimeError(
                    f"The pipeline {self.name} depends on the same step "
                    f"({step.name}) multiple times. To fix this, remove the "
                    "duplicate from the `depends_on` list. You can pass the "
                    "same step function with multiple configurations by using "
                    "the `step.with_options(...)` method."
                )

            static_ids.add(static_id)

    @property
    def depends_on(self) -> List["BaseStep"]:
        """The steps that the pipeline depends on.

        Returns:
            The steps that the pipeline depends on.
        """
        return self._depends_on

    @property
    def is_dynamic(self) -> bool:
        """If the pipeline is dynamic.

        Returns:
            If the pipeline is dynamic.
        """
        return True

    def resolve(self) -> "Source":
        """Resolves the pipeline.

        Raises:
            RuntimeError: If the resolved source is not loadable for dynamic
                pipelines.

        Returns:
            The pipeline source.
        """
        source = super().resolve()
        # We need to validate that the source is loadable for dynamic
        # pipelines as the orchestration environment will need to load the
        # source.
        try:
            source_utils.load(source)
        except Exception as e:
            raise RuntimeError(
                "Unable to resolve dynamic pipeline source. Make sure "
                "your pipeline is defined at the top level of your module."
            ) from e

        return source

    def _prepare_invocations(self, **kwargs: Any) -> None:
        """Prepares the invocations of the pipeline.

        Args:
            **kwargs: Keyword arguments.
        """
        for step in self._depends_on:
            self.add_step_invocation(
                step,
                input_artifacts={},
                external_artifacts={},
                model_artifacts_or_metadata={},
                client_lazy_loaders={},
                parameters={},
                default_parameters={},
                upstream_steps=set(),
            )

    def __call__(
        self, *args: Any, **kwargs: Any
    ) -> Optional[PipelineRunResponse]:
        """Run the pipeline on the active stack.

        Args:
            *args: Entrypoint function arguments.
            **kwargs: Entrypoint function keyword arguments.

        Raises:
            RuntimeError: If the active orchestrator does not support running
                dynamic pipelines.

        Returns:
            The pipeline run or `None` if running with a schedule.
        """
        if should_prevent_pipeline_execution():
            logger.info("Preventing execution of pipeline '%s'.", self.name)
            return None

        stack = Client().active_stack
        if not stack.orchestrator.supports_dynamic_pipelines:
            raise RuntimeError(
                f"The {stack.orchestrator.__class__.__name__} does not "
                "support dynamic pipelines. "
            )

        logger.warning(
            "Dynamic pipelines are currently an experimental feature. There "
            "are known issues and limitations and the interface is subject to "
            "change. If you encounter any issues or have feedback, please "
            "let us know at https://github.com/zenml-io/zenml/issues."
        )

        self.prepare(*args, **kwargs)
        return self._run()

    def _compute_output_schema(self) -> Optional[Dict[str, Any]]:
        """Computes the output schema for the pipeline.

        Returns:
            The output schema for the pipeline.
        """
        try:
            outputs = parse_return_type_annotations(self.entrypoint)
            model_fields: Dict[str, Any] = {
                name: (output.resolved_annotation, ...)
                for name, output in outputs.items()
            }
            output_model: Type[BaseModel] = create_model(
                "PipelineOutput",
                __config__=ConfigDict(extra="forbid"),
                **model_fields,
            )
            return output_model.model_json_schema(mode="serialization")
        except Exception as e:
            logger.debug(
                f"Failed to generate the output schema for pipeline "
                f"`{self.name}: {e}. This means that the pipeline cannot be "
                "deployed.",
            )
            return None
