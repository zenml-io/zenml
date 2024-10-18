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

import random
from typing import Callable
from uuid import UUID

import pytest
from typing_extensions import Annotated

from zenml import (
    ExternalArtifact,
    load_artifact,
    pipeline,
    save_artifact,
    step,
)
from zenml.client import Client
from zenml.enums import ModelStages, StepRunInputArtifactType
from zenml.model.model import Model
from zenml.models.v2.core.pipeline_run import PipelineRunResponse


@step(enable_cache=True)
def simple_producer_step() -> Annotated[int, "trackable_artifact"]:
    return 42


@step(enable_cache=False)
def keep_pipeline_alive() -> None:
    pass


@step(enable_cache=True)
def cacheable_multiple_versioned_producer(
    versions_count: int,
) -> Annotated[int, "trackable_artifact"]:
    for _ in range(versions_count):
        save_artifact(42, name="manual_artifact")
    return 42


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


@pipeline
def cacheable_pipeline_with_multiple_versions_producer_where_second_step_is_cached(
    version_count: int,
):
    cacheable_multiple_versioned_producer(
        versions_count=version_count,
        id="cacheable_multiple_versioned_producer_1",
    )
    cacheable_multiple_versioned_producer(
        versions_count=version_count,
        id="cacheable_multiple_versioned_producer_2",
        after=["cacheable_multiple_versioned_producer_1"],
    )


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
        assert len(outputs[artifact_name]) == 1
        assert int(outputs[artifact_name][0].version) == expected_version
        # producer ID is always the original PR
        assert (
            outputs[artifact_name][0].producer_pipeline_run_id
            == producer_pr_id
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


def test_that_cached_artifact_versions_are_created_properly_for_multiple_version_producer(
    clean_client: Client,
):
    vc = random.randint(5, 10)
    pr1: PipelineRunResponse = cacheable_pipeline_with_multiple_versions_producer_where_second_step_is_cached.with_options(
        model=Model(name="foo")
    )(version_count=vc)
    sr1 = pr1.steps["cacheable_multiple_versioned_producer_1"]
    sr1_2 = pr1.steps["cacheable_multiple_versioned_producer_2"]
    for sr in [sr1, sr1_2]:
        assert len(sr.outputs) == 2
        assert len(sr.outputs["trackable_artifact"]) == 1
        assert len(sr.outputs["manual_artifact"]) == vc

    # cached entries should match exactly
    assert (
        sr1.outputs["trackable_artifact"][0].id
        == sr1_2.outputs["trackable_artifact"][0].id
    )
    assert {a.id for a in sr1.outputs["manual_artifact"]} == {
        a.id for a in sr1_2.outputs["manual_artifact"]
    }

    mv1 = clean_client.get_model_version("foo", ModelStages.LATEST)
    assert len(mv1.data_artifacts) == 2
    assert (
        len(mv1.data_artifacts["manual_artifact"]) == vc
    )  # cached show up only once
    assert (
        len(mv1.data_artifacts["trackable_artifact"]) == 1
    )  # cached show up only once

    pr2: PipelineRunResponse = cacheable_pipeline_with_multiple_versions_producer_where_second_step_is_cached.with_options(
        model=Model(name="foo")
    )(version_count=vc)
    for sr2 in pr2.steps.values():
        assert len(sr2.outputs) == 2
        assert len(sr2.outputs["trackable_artifact"]) == 1
        assert len(sr2.outputs["manual_artifact"]) == vc

        # cached entries should match exactly
        assert (
            sr2.outputs["trackable_artifact"][0].id
            == sr1.outputs["trackable_artifact"][0].id
        )
        assert {a.id for a in sr2.outputs["manual_artifact"]} == {
            a.id for a in sr1.outputs["manual_artifact"]
        }

    mv2 = clean_client.get_model_version("foo", ModelStages.LATEST)
    assert len(mv2.data_artifacts) == 2
    assert (
        len(mv2.data_artifacts["manual_artifact"]) == vc
    )  # cached show up only once
    assert (
        len(mv2.data_artifacts["trackable_artifact"]) == 1
    )  # cached show up only once


@step
def producer_step() -> Annotated[int, "shared_name"]:
    save_artifact(41, "shared_name")
    return 42


@step
def consumer_step(shared_name: int, expected: int):
    assert shared_name == expected


@step
def manual_consumer_step_load():
    assert load_artifact("shared_name", 1) == 41


@step
def manual_consumer_step_client():
    assert Client().get_artifact_version("shared_name", 1).load() == 41


def test_input_artifacts_typing(clean_client: Client):
    """Test that input artifacts are correctly typed."""

    @pipeline
    def my_pipeline():
        a = producer_step()
        consumer_step(a, 42, id="cs1", after=["producer_step"])
        consumer_step(ExternalArtifact(value=42), 42, id="cs2", after=["cs1"])
        consumer_step(
            clean_client.get_artifact_version("shared_name", 1),
            41,
            after=["producer_step", "cs2"],
            id="cs3",
        )
        manual_consumer_step_load(id="mcsl", after=["cs3"])
        manual_consumer_step_client(id="mcsc", after=["mcsl"])

    for cache in [False, True]:
        prr: PipelineRunResponse = my_pipeline.with_options(
            enable_cache=cache
        )()
        assert len(prr.steps["producer_step"].input_types) == 0
        assert (
            prr.steps["cs1"].input_types["shared_name"]
            == StepRunInputArtifactType.STEP_OUTPUT
        )
        assert (
            prr.steps["cs2"].input_types["shared_name"]
            == StepRunInputArtifactType.EXTERNAL
        )
        assert (
            prr.steps["cs3"].input_types["shared_name"]
            == StepRunInputArtifactType.LAZY_LOADED
        )
        assert (
            prr.steps["mcsl"].input_types["shared_name"]
            == StepRunInputArtifactType.MANUAL
        )
        assert (
            prr.steps["mcsc"].input_types["shared_name"]
            == StepRunInputArtifactType.MANUAL
        )
