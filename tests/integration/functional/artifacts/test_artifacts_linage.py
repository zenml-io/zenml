#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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

from typing import Callable
from uuid import UUID

import pytest
from typing_extensions import Annotated

from zenml import pipeline, step
from zenml.client import Client
from zenml.enums import ModelStages
from zenml.model.model import Model


@step(enable_cache=True)
def simple_producer_step() -> Annotated[int, "trackable_artifact"]:
    return 42


@step(enable_cache=False)
def keep_pipeline_alive() -> None:
    pass


@pipeline
def cacheable_pipeline_which_always_run():
    simple_producer_step()
    keep_pipeline_alive()


@pipeline
def cacheable_pipeline_which_can_be_fully_cached():
    simple_producer_step()


@pipeline
def cacheable_pipeline_where_second_step_is_cached():
    simple_producer_step(id="simple_producer_step_1")
    simple_producer_step(id="simple_producer_step_2")


def _validate_artifacts_state(
    clean_client: Client,
    pr_id: UUID,
    producer_pr_id: UUID,
    expected_version: int,
    step_name: str = "simple_producer_step",
    artifact_name: str = "trackable_artifact",
):
    pr = clean_client.get_pipeline_run(pr_id)
    outputs_1 = pr.steps[step_name].outputs
    step = clean_client.get_run_step(pr.steps[step_name].id)
    outputs_2 = step.outputs
    for outputs in [outputs_1, outputs_2]:
        assert len(outputs) == 1
        assert int(outputs[artifact_name].version) == expected_version
        # producer ID is always the original PR
        assert (
            outputs[artifact_name].producer_pipeline_run_id == producer_pr_id
        )

    artifact = clean_client.get_artifact_version(artifact_name)
    assert artifact.name == artifact_name
    assert int(artifact.version) == expected_version
    # producer ID is always the original PR
    assert artifact.producer_pipeline_run_id == producer_pr_id


# TODO: remove clean client, ones clean env for REST is available
@pytest.mark.parametrize(
    "pipeline",
    [
        cacheable_pipeline_which_always_run,
        cacheable_pipeline_which_can_be_fully_cached,
    ],
)
def test_that_cached_artifact_versions_are_created_properly(
    pipeline: Callable, clean_client: Client
):
    pr_orig = pipeline()

    _validate_artifacts_state(
        clean_client=clean_client,
        pr_id=pr_orig.id,
        producer_pr_id=pr_orig.id,
        expected_version=1,
    )

    pr = pipeline()

    pr = clean_client.get_pipeline_run(pr.id)
    _validate_artifacts_state(
        clean_client=clean_client,
        pr_id=pr.id,
        producer_pr_id=pr_orig.id,
        expected_version=1,  # cached artifact doesn't produce new version
    )


# TODO: remove clean client, ones clean env for REST is available
def test_that_cached_artifact_versions_are_created_properly_for_second_step(
    clean_client: Client,
):
    pr_orig = cacheable_pipeline_where_second_step_is_cached()

    _validate_artifacts_state(
        clean_client=clean_client,
        pr_id=pr_orig.id,
        producer_pr_id=pr_orig.id,
        step_name="simple_producer_step_1",
        expected_version=1,
    )
    _validate_artifacts_state(
        clean_client=clean_client,
        pr_id=pr_orig.id,
        producer_pr_id=pr_orig.id,
        step_name="simple_producer_step_2",
        expected_version=1,
    )

    pr = cacheable_pipeline_where_second_step_is_cached()

    pr = clean_client.get_pipeline_run(pr.id)
    _validate_artifacts_state(
        clean_client=clean_client,
        pr_id=pr.id,
        producer_pr_id=pr_orig.id,
        step_name="simple_producer_step_1",
        expected_version=1,  # cached artifact doesn't produce new version
    )
    _validate_artifacts_state(
        clean_client=clean_client,
        pr_id=pr.id,
        producer_pr_id=pr_orig.id,
        step_name="simple_producer_step_2",
        expected_version=1,  # cached artifact doesn't produce new version
    )


def test_that_cached_artifact_versions_are_created_properly_for_model_version(
    clean_client: Client,
):
    pr_orig = cacheable_pipeline_which_always_run.with_options(
        model=Model(name="foo")
    )()

    mv = clean_client.get_model_version("foo", ModelStages.LATEST)
    assert (
        mv.data_artifacts["trackable_artifact"]["1"].producer_pipeline_run_id
        == pr_orig.id
    )

    cacheable_pipeline_which_always_run.with_options(model=Model(name="foo"))()

    mv = clean_client.get_model_version("foo", ModelStages.LATEST)
    assert (
        mv.data_artifacts["trackable_artifact"]["1"].producer_pipeline_run_id
        == pr_orig.id
    )
