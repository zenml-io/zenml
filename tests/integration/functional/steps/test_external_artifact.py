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


from typing import Annotated

import pytest
from tests.integration.functional.utils import model_killer

from zenml import pipeline, step
from zenml.model import ArtifactConfig, ModelConfig
from zenml.steps.external_artifact import ExternalArtifact


@step
def producer(
    run_number: int,
) -> Annotated[int, "predictions", ArtifactConfig(overwrite=False)]:
    """Step producing versioned output and linking it to a model."""
    return run_number


@step
def consumer(external_artifact: int, expected_value: int):
    """Step receiving external artifact and asserting it."""
    assert external_artifact == expected_value


@pipeline(
    name="bar",
    enable_cache=False,
)
def producer_pipeline(run_count: int):
    producer(run_count)


@pipeline(name="bar", enable_cache=False, model_config=ModelConfig(name="foo"))
def consumer_pipeline(
    model_artifact_version: int,
    model_artifact_pipeline_name: str = None,
    model_artifact_step_name: str = None,
):
    consumer(
        ExternalArtifact(
            model_artifact_name="predictions",
            model_artifact_version=model_artifact_version,
            model_artifact_pipeline_name=model_artifact_pipeline_name,
            model_artifact_step_name=model_artifact_step_name,
        ),
        model_artifact_version,
    )


@pipeline(
    name="bar",
    enable_cache=False,
    model_config=ModelConfig(name="foo", create_new_model_version=True),
)
def two_step_producer_pipeline():
    producer(1)
    producer(1)


def test_exchange_of_model_artifacts_between_pipelines():
    """Test that model config was passed to step context via step."""
    with model_killer():
        producer_pipeline.with_options(
            model_config=ModelConfig(name="foo", create_new_model_version=True)
        )(1)
        producer_pipeline.with_options(model_config=ModelConfig(name="foo"))(
            2
        )  # add to latest version
        consumer_pipeline(1)
        consumer_pipeline(2)


def test_external_artifact_fails_on_name_collision_without_pipeline_and_step():
    """Test that model config was passed to step context via step."""
    with model_killer():
        two_step_producer_pipeline()
        with pytest.raises(
            RuntimeError,
            match="Found more than one artifact linked to this model version",
        ):
            consumer_pipeline(1)


def test_external_artifact_fails_on_name_collision_without_step():
    """Test that model config was passed to step context via step."""
    with model_killer():
        two_step_producer_pipeline()
        with pytest.raises(
            RuntimeError,
            match="Found more than one artifact linked to this model version",
        ):
            consumer_pipeline(1, model_artifact_pipeline_name="bar")


def test_external_artifact_pass_on_name_collision_with_pipeline_and_step():
    """Test that model config was passed to step context via step."""
    with model_killer():
        two_step_producer_pipeline()
        consumer_pipeline(
            1,
            model_artifact_pipeline_name="bar",
            model_artifact_step_name="producer",
        )
