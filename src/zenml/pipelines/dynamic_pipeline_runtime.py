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

from typing import Optional

from zenml.models import PipelineRunResponse, PipelineSnapshotResponse
from zenml.pipelines.dynamic_pipeline import DynamicPipeline


class DynamicPipelineRuntime:
    def __init__(
        self,
        pipeline: DynamicPipeline,
        snapshot: PipelineSnapshotResponse,
        run: PipelineRunResponse,
    ) -> None:
        self.pipeline = pipeline
        self.snapshot = snapshot
        self.run = run


_active_runtime = None


def initialize_runtime(
    pipeline: DynamicPipeline,
    snapshot: PipelineSnapshotResponse,
    run: PipelineRunResponse,
):
    global _active_runtime
    _active_runtime = DynamicPipelineRuntime(
        pipeline=pipeline,
        snapshot=snapshot,
        run=run,
    )


def get_pipeline_runtime() -> Optional[DynamicPipelineRuntime]:
    return _active_runtime
