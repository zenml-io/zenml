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
from typing import Callable, Optional
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
from zenml.enums import ArtifactType, ModelStages, StepRunInputArtifactType
from zenml.model.model import Model
from zenml.models.v2.core.pipeline_run import PipelineRunResponse


@step(enable_cache=True)
def simple_producer_step() -> Annotated[int, "trackable_artifact"]:
    """A simple ZenML step that produces a single integer artifact named 'trackable_artifact'.

    This step is cacheable.

    Returns:
        An integer value (42).
    """
    return 42


@step(enable_cache=False)
def keep_pipeline_alive() -> None:
    """A simple ZenML step that does nothing.

    Its purpose is to ensure a pipeline runs even if all other steps might be
    cached, by being a non-cacheable step itself.
    """
    pass


@step(enable_cache=True)
def cacheable_multiple_versioned_producer(
    versions_count: int, artifact_type: Optional[ArtifactType] = None
) -> Annotated[int, "trackable_artifact"]:
    """A cacheable step that produces one primary artifact and multiple versions of a manually saved artifact.

    Args:
        versions_count: The number of versions to create for the manually
            saved artifact "manual_artifact".
        artifact_type: Optional artifact type for the manually saved artifact.

    Returns:
        An integer value (42) for the primary artifact "trackable_artifact".
    """
    for _ in range(versions_count):
        save_artifact(42, name="manual_artifact", artifact_type=artifact_type)
    return 42


@pipeline
def cacheable_pipeline_which_always_run() -> None:
    """Defines a pipeline with one cacheable step and one non-cacheable step.

    The `simple_producer_step` is cacheable, while `keep_pipeline_alive` is
    not, ensuring that the pipeline will execute `keep_pipeline_alive` on
    every run, even if `simple_producer_step` is served from cache. This is
    useful for testing caching behavior in scenarios where a pipeline run is
    always triggered.
    """
    simple_producer_step()
    keep_pipeline_alive()


@pipeline
def cacheable_pipeline_which_can_be_fully_cached() -> None:
    """Defines a pipeline consisting of a single cacheable step.

    This pipeline is designed to be fully cacheable after its initial run,
    as it only contains `simple_producer_step`, which is cacheable.
    """
    simple_producer_step()


@pipeline
def cacheable_pipeline_where_second_step_is_cached() -> None:
    """Defines a two-step pipeline where both steps are instances of the same cacheable step.

    This pipeline structure is used to test how caching affects artifact
    versioning and lineage when subsequent steps in a sequence might be
    served from cache based on the execution of identical preceding steps.
    Both steps are instances of `simple_producer_step`.
    """
    simple_producer_step(id="simple_producer_step_1")
    simple_producer_step(id="simple_producer_step_2")


@pipeline
def cacheable_pipeline_with_multiple_versions_producer_where_second_step_is_cached(
    version_count: int, artifact_type: Optional[ArtifactType] = None
) -> None:
    """Defines a pipeline with two steps, each producing multiple artifact versions.

    This pipeline is used to test artifact versioning and caching, particularly
    when steps that manually save multiple versions of an artifact are involved.
    The second step is expected to be cacheable based on the first.

    Args:
        version_count: The number of versions for the manually saved artifact
            within each producer step.
        artifact_type: Optional artifact type for the manually saved artifacts.
    """
    cacheable_multiple_versioned_producer(
        versions_count=version_count,
        artifact_type=artifact_type,
        id="cacheable_multiple_versioned_producer_1",
    )
    cacheable_multiple_versioned_producer(
        versions_count=version_count,
        artifact_type=artifact_type,
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
) -> None:
    """Validates the state of an artifact version produced by a pipeline run.

    This helper function checks:
    - The artifact version number in the step's output.
    - The `producer_pipeline_run_id` of the artifact version in the step's output.
    - The artifact version number retrieved directly via `get_artifact_version`.
    - The `producer_pipeline_run_id` of the artifact version retrieved directly.

    Args:
        clean_client: The ZenML client instance.
        pr_id: The ID of the pipeline run to inspect for the artifact.
        producer_pr_id: The expected ID of the pipeline run that originally
            produced this artifact version.
        expected_version: The expected version number of the artifact.
        step_name: The name of the step that produced the artifact.
        artifact_name: The name of the artifact to validate.
    """
    pr = clean_client.get_pipeline_run(pr_id)
    outputs_1 = pr.steps[step_name].outputs
    step_run_resp = clean_client.get_run_step(pr.steps[step_name].id)
    outputs_2 = step_run_resp.outputs
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
    "pipeline_callable",  # Renamed from "pipeline" to avoid conflict
    [
        cacheable_pipeline_which_always_run,
        cacheable_pipeline_which_can_be_fully_cached,
    ],
)
def test_that_cached_artifact_versions_are_created_properly(
    pipeline_callable: Callable, clean_client: Client
) -> None:
    """Tests how artifact versions and producer IDs are handled when pipelines/steps are cached.

    This test runs a given pipeline twice. It validates that after the first run,
    the artifact has version 1 and its producer ID is the ID of that first run.
    After the second run (which should hit the cache for relevant steps), it
    validates that the artifact version is still 1 (no new version created due to
    caching) and that the producer ID still points to the original first run.

    Args:
        pipeline_callable: A callable that returns a ZenML pipeline instance.
        clean_client: A ZenML client instance.
    """
    pr_orig = pipeline_callable()

    _validate_artifacts_state(
        clean_client=clean_client,
        pr_id=pr_orig.id,
        producer_pr_id=pr_orig.id,
        expected_version=1,
    )

    pr = pipeline_callable()

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
) -> None:
    """Tests artifact versioning when a later step in a sequence is cached.

    This test runs a two-step pipeline where both steps are instances of the
    same cacheable step. It verifies that artifacts produced by both steps in
    the first run have version 1 and their producer ID is that of the first run.
    In the second run (where both steps should be cached), it verifies that the
    artifact versions remain 1 and producer IDs correctly point to the first run.

    Args:
        clean_client: A ZenML client instance.
    """
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
) -> None:
    """Tests the producer ID of artifacts linked to model versions when caching is involved.

    This test runs a pipeline associated with a model version twice. It checks
    that the `producer_pipeline_run_id` for an artifact linked to the model
    version correctly points to the ID of the original pipeline run that
    produced the artifact, even when subsequent runs use cached versions of
    that artifact.

    Args:
        clean_client: A ZenML client instance.
    """
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
) -> None:
    """Tests artifact versioning with steps that produce multiple artifact versions, especially under caching.

    This test runs a pipeline containing steps that manually save multiple
    versions of an artifact (`manual_artifact`) and also output a primary
    artifact (`trackable_artifact`). It verifies:
    - Correct number of artifact versions for both manual and primary artifacts.
    - Consistency of artifact IDs when steps are cached (i.e., cached steps
      should link to the same, original artifact versions).
    - Correct accounting of artifact versions linked to the model version,
      ensuring cached versions are not double-counted.

    Args:
        clean_client: A ZenML client instance.
    """
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
    """A step that produces a primary artifact and manually saves another version of the same artifact.

    The primary output is named "shared_name" and returns 42.
    It also manually saves an artifact named "shared_name" with value 41.

    Returns:
        An integer value (42) for the primary output.
    """
    save_artifact(41, "shared_name")
    return 42


@step
def consumer_step(shared_name: int, expected: int) -> None:
    """A step that consumes an artifact and asserts its value.

    Args:
        shared_name: The input artifact (expected to be an integer).
        expected: The expected integer value of the input artifact.
    """
    assert shared_name == expected


@step
def manual_consumer_step_load() -> None:
    """A step that tests loading a specific version of an artifact using `load_artifact`."""
    assert load_artifact("shared_name", 1) == 41


@step
def manual_consumer_step_client() -> None:
    """A step that tests loading a specific version of an artifact using `client.get_artifact_version().load()`."""
    assert Client().get_artifact_version("shared_name", 1).load() == 41


def test_input_artifacts_typing(clean_client: Client) -> None:
    """Tests the correct typing of input artifacts under various scenarios.

    This test defines a pipeline (`_input_typing_pipeline`) that consumes artifacts
    in different ways:
    - As direct output from a previous step.
    - As an `ExternalArtifact`.
    - By lazy-loading via `client.get_artifact_version()`.
    - By manually loading within steps using `load_artifact()` or client methods.

    It verifies that the `input_type` attribute of the step run's input
    metadata is correctly set for each scenario, both with and without caching.

    Args:
        clean_client: A ZenML client instance.
    """

    @pipeline
    def _input_typing_pipeline() -> None:
        """Pipeline demonstrating various ways of consuming artifacts in steps."""
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
        prr: PipelineRunResponse = _input_typing_pipeline.with_options(
            enable_cache=cache
        )()
        assert len(prr.steps["producer_step"].inputs) == 0
        assert (
            prr.steps["cs1"].inputs["shared_name"].input_type
            == StepRunInputArtifactType.STEP_OUTPUT
        )
        assert (
            prr.steps["cs2"].inputs["shared_name"].input_type
            == StepRunInputArtifactType.EXTERNAL
        )
        assert (
            prr.steps["cs3"].inputs["shared_name"].input_type
            == StepRunInputArtifactType.LAZY_LOADED
        )
        assert (
            prr.steps["mcsl"].inputs["shared_name"].input_type
            == StepRunInputArtifactType.MANUAL
        )
        assert (
            prr.steps["mcsc"].inputs["shared_name"].input_type
            == StepRunInputArtifactType.MANUAL
        )


# TODO: Enable this test after fixing the issue with `is_model_artifact` and `is_deployment_artifact` flags
@pytest.mark.skip(
    "Enable this test after fixing the issue with `is_model_artifact` and `is_deployment_artifact` flags"
)
def test_that_cached_manual_artifact_has_proper_type_on_second_run(
    clean_client: Client,
) -> None:
    """Tests that manually saved artifacts (model/service types) retain their correct type information across cached runs.

    This test iterates through `ArtifactType.MODEL` and `ArtifactType.SERVICE`.
    For each type, it runs a pipeline twice. The pipeline contains a step that
    manually saves an artifact with the specified type. It then verifies that
    the artifact linked to the model version has the correct type information
    (i.e., is listed under `model_artifacts` or `deployment_artifacts` respectively)
    after both the first and the second (cached) run.

    Args:
        clean_client: A ZenML client instance.
    """
    for artifact_type in [ArtifactType.MODEL, ArtifactType.SERVICE]:
        for _ in range(2):
            cacheable_pipeline_with_multiple_versions_producer_where_second_step_is_cached.with_options(
                model=Model(name="foo")
            )(version_count=1, artifact_type=artifact_type)

            mv = clean_client.get_model_version("foo", ModelStages.LATEST)
            assert len(mv.data_artifacts) == 1
            if artifact_type == ArtifactType.MODEL:
                assert len(mv.model_artifacts) == 1
            if artifact_type == ArtifactType.SERVICE:
                assert len(mv.deployment_artifacts) == 1

[end of tests/integration/functional/artifacts/test_artifacts_linage.py]
