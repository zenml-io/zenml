#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""End-to-end test for steps that rely on PEP 563 stringized annotations."""

from tests.integration.functional.steps.future_annotations_pipeline import (
    ARTIFACT_NAME,
    future_annotations_pipeline,
)

from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.materializers.cloudpickle_materializer import (
    CloudpickleMaterializer,
)
from zenml.utils import source_utils


def test_pipeline_with_future_annotations_runs(clean_client: "Client") -> None:
    """A pipeline whose module uses `from __future__ import annotations`
    should resolve stringized annotations and pick the correct materializer.
    """
    future_annotations_pipeline(x=3)

    last_run = future_annotations_pipeline.model.last_run
    assert last_run.status == ExecutionStatus.COMPLETED

    produce_step = last_run.steps["produce"]
    artifact = produce_step.outputs[ARTIFACT_NAME][0]

    # Type resolution worked: the artifact knows its data type is `int`.
    assert source_utils.load(artifact.data_type) is int

    # And we did not silently fall back to the cloudpickle materializer.
    materializer_class = source_utils.load(artifact.materializer)
    assert materializer_class is not CloudpickleMaterializer

    # End-to-end correctness: produce returns x * 2.
    assert artifact.load() == 6
