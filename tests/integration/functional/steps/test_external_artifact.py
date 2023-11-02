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


import pytest
from tests.integration.functional.utils import model_killer
from typing_extensions import Annotated

from zenml import pipeline, step
from zenml.artifacts.external_artifact import ExternalArtifact
from zenml.client import Client
from zenml.model import (
    ArtifactConfig,
    ModelVersionConsumerConfig,
    ModelVersionProducerConfig,
)


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


@pipeline(
    name="bar",
    enable_cache=False,
    model_config=ModelVersionConsumerConfig(name="foo"),
)
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


@pipeline(name="bar", enable_cache=False)
def consumer_pipeline_with_external_artifact_from_another_model(
    model_artifact_version: int,
    model_artifact_pipeline_name: str = None,
    model_artifact_step_name: str = None,
):
    consumer(
        ExternalArtifact(
            model_name="foo",
            model_version=1,
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
    model_config=ModelVersionProducerConfig(name="foo"),
)
def two_step_producer_pipeline():
    producer(1)
    producer(1)


@pytest.mark.parametrize(
    "consumer_pipeline",
    [
        consumer_pipeline,
        consumer_pipeline_with_external_artifact_from_another_model,
    ],
    ids=["model context given", "no model context"],
)
def test_exchange_of_model_artifacts_between_pipelines(consumer_pipeline):
    """Test that ExternalArtifact helps to exchange data from Model between pipelines."""
    with model_killer():
        producer_pipeline.with_options(
            model_config=ModelVersionProducerConfig(name="foo")
        )(1)
        producer_pipeline.with_options(
            model_config=ModelVersionConsumerConfig(name="foo")
        )(
            2
        )  # add to latest version
        consumer_pipeline(1)
        consumer_pipeline(2)


def test_external_artifact_fails_on_name_collision_without_pipeline_and_step():
    """Test that ExternalArtifact will raise in case there is a naming collision not
    resolved with given arguments (here only name and version).

    Two step producer pipeline produces two artifacts with the same name, but from different steps.
    """
    with model_killer():
        two_step_producer_pipeline()
        with pytest.raises(
            RuntimeError,
            match="Found more than one artifact linked to this model version",
        ):
            consumer_pipeline(1)


def test_external_artifact_fails_on_name_collision_without_step():
    """Test that ExternalArtifact will raise in case there is a naming collision not
    resolved with given arguments (here only name, version and pipeline).

    Two step producer pipeline produces two artifacts with the same name, but from different steps.
    """
    with model_killer():
        two_step_producer_pipeline()
        with pytest.raises(
            RuntimeError,
            match="Found more than one artifact linked to this model version",
        ):
            consumer_pipeline(1, model_artifact_pipeline_name="bar")


def test_external_artifact_pass_on_name_collision_with_pipeline_and_step():
    """Test that ExternalArtifact will resolve collision smoothly by full set of arguments.

    Two step producer pipeline produces two artifacts with the same name, but from different steps.
    """
    with model_killer():
        two_step_producer_pipeline()
        consumer_pipeline(
            1,
            model_artifact_pipeline_name="bar",
            model_artifact_step_name="producer",
        )


def test_exchange_of_model_artifacts_between_pipelines_by_model_version_number():
    """Test that ExternalArtifact helps to exchange data from Model between pipelines using model version number."""
    with model_killer():
        producer_pipeline.with_options(
            model_config=ModelVersionProducerConfig(name="foo")
        )(1)
        producer_pipeline.with_options(
            model_config=ModelVersionConsumerConfig(name="foo")
        )(
            2
        )  # add to latest version
        consumer_pipeline.with_options(
            model_config=ModelVersionConsumerConfig(name="foo", version=1)
        )(1)
        consumer_pipeline.with_options(
            model_config=ModelVersionConsumerConfig(name="foo", version=1)
        )(2)


@pytest.mark.parametrize(
    "model_version_name,expected",
    [[1, 42], ["1", 42], ["foo", 23]],
    ids=[
        "By model version number",
        "By model version number as string",
        "By model version name",
    ],
)
def test_direct_consumption(model_version_name, expected):
    """Test that ExternalArtifact can fetch data by full config with model version name/number combinations."""
    with model_killer():
        producer_pipeline.with_options(
            model_config=ModelVersionProducerConfig(name="foo")
        )(42)
        producer_pipeline.with_options(
            model_config=ModelVersionProducerConfig(name="foo", version="foo")
        )(23)
        artifact_id = ExternalArtifact(
            model_name="foo",
            model_version=model_version_name,
            model_artifact_name="predictions",
        ).get_artifact_id()
        assert Client().get_artifact(artifact_id).load() == expected
