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
"""Dynamic pipeline run context."""

import contextvars
from typing import TYPE_CHECKING

from typing_extensions import Self

from zenml.utils import context_utils

if TYPE_CHECKING:
    from zenml.execution.pipeline.dynamic.runner import DynamicPipelineRunner
    from zenml.models import PipelineRunResponse, PipelineSnapshotResponse
    from zenml.pipelines.dynamic.pipeline_definition import DynamicPipeline


class DynamicPipelineRunContext(context_utils.BaseContext):
    """Dynamic pipeline run context."""

    __context_var__ = contextvars.ContextVar("dynamic_pipeline_run_context")

    def __init__(
        self,
        pipeline: "DynamicPipeline",
        snapshot: "PipelineSnapshotResponse",
        run: "PipelineRunResponse",
        runner: "DynamicPipelineRunner",
    ) -> None:
        """Initialize the dynamic pipeline run context.

        Args:
            pipeline: The dynamic pipeline that is being executed.
            snapshot: The snapshot of the pipeline.
            run: The pipeline run.
            runner: The dynamic pipeline runner.
        """
        super().__init__()
        self._pipeline = pipeline
        self._snapshot = snapshot
        self._run = run
        self._runner = runner

    @property
    def pipeline(self) -> "DynamicPipeline":
        """The pipeline that is being executed.

        Returns:
            The pipeline that is being executed.
        """
        return self._pipeline

    @property
    def run(self) -> "PipelineRunResponse":
        """The pipeline run.

        Returns:
            The pipeline run.
        """
        return self._run

    @property
    def snapshot(self) -> "PipelineSnapshotResponse":
        """The snapshot of the pipeline.

        Returns:
            The snapshot of the pipeline.
        """
        return self._snapshot

    @property
    def runner(self) -> "DynamicPipelineRunner":
        """The runner executing the pipeline.

        Returns:
            The runner executing the pipeline.
        """
        return self._runner

    def __enter__(self) -> Self:
        """Enter the dynamic pipeline run context.

        Raises:
            RuntimeError: If the dynamic pipeline run context has already been
                entered.

        Returns:
            The dynamic pipeline run context object.
        """
        if self._token is not None:
            raise RuntimeError(
                "Calling a pipeline within a dynamic pipeline is not allowed."
            )
        return super().__enter__()
