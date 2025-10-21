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


import os
from typing import Annotated, Tuple

import pytest

from tests.integration.functional.zen_stores.utils import PipelineRunContext
from zenml import ArtifactConfig, Tag, add_tags, pipeline, remove_tags, step
from zenml.client import Client
from zenml.constants import ENV_ZENML_PREVENT_CLIENT_SIDE_CACHING
from zenml.enums import ExecutionStatus
from zenml.utils.string_utils import random_str


@step
def step_no_output() -> None:
    """Step calls add_tags."""
    add_tags(tags=["axl"])


@step
def step_single_output() -> Annotated[int, "single"]:
    """Step calls add_tags."""
    add_tags(tags=["aria"], infer_artifact=True)
    return 1


@step
def step_multiple_outputs() -> Tuple[
    Annotated[int, "first"], Annotated[int, "second"]
]:
    """Step calls add_tags."""
    add_tags(tags=["blupus"], infer_artifact=True, artifact_name="first")
    return 1, 2


@step
def step_artifact_config() -> Annotated[
    int, ArtifactConfig(name="luna", tags=["nova"])
]:
    """Step calls add_tags."""
    return 1


@pipeline(
    tags=[
        "normal_tag",
        Tag(name="cascade_tag", cascade=True),
        Tag(name="exclusive_tag", exclusive=True),
    ],
    enable_cache=False,
)
def pipeline_to_tag():
    """Pipeline definition to test the tag utils."""
    step_no_output()
    step_single_output()
    step_multiple_outputs()
    step_artifact_config()


def test_tag_utils(clean_client):
    """Testing different functionalities of the add_tags function."""
    # Run the pipeline
    first_run = pipeline_to_tag()
    first_run_tags = [t.name for t in first_run.tags]
    assert all(
        tag in first_run_tags
        for tag in ["normal_tag", "cascade_tag", "exclusive_tag", "axl"]
    )

    single_output_tags = [
        t.name
        for t in first_run.steps["step_single_output"]
        .outputs["single"][0]
        .tags
    ]
    assert all(tag in single_output_tags for tag in ["cascade_tag", "aria"])

    multiple_output_tags = [
        t.name
        for t in first_run.steps["step_multiple_outputs"]
        .outputs["first"][0]
        .tags
    ]
    assert all(
        tag in multiple_output_tags for tag in ["cascade_tag", "blupus"]
    )

    second_run = pipeline_to_tag()
    second_run_tags = [t.name for t in second_run.tags]
    assert all(
        tag in second_run_tags
        for tag in ["normal_tag", "cascade_tag", "exclusive_tag", "axl"]
    )

    run = clean_client.get_pipeline_run(first_run.id)
    first_run_tags = [t.name for t in run.tags]
    assert "exclusive_tag" not in first_run_tags

    runs = clean_client.list_pipeline_runs(
        tags=["startswith:c", "equals:exclusive_tag"]
    )
    assert len(runs.items) == 1
    assert runs.items[0].id == second_run.id

    runs = clean_client.list_pipeline_runs(
        tags=["startswith:wrong", "equals:exclusive_tag"]
    )
    assert len(runs.items) == 0

    remove_tags(
        tags=["cascade_tag", "exclusive_tag"],
        run=second_run.id,
    )
    run = clean_client.get_pipeline_run(second_run.id)
    second_run_tags = [t.name for t in run.tags]
    assert "cascade_tag" not in second_run_tags
    assert "exclusive_tag" not in second_run_tags

    pipeline_model = clean_client.get_pipeline(first_run.pipeline.id)
    with pytest.raises(ValueError):
        add_tags(
            tags=[Tag(name="new_exclusive_tag", exclusive=True)],
            pipeline=pipeline_model.id,
        )

    add_tags(tags=["regular_tag_for_pipeline"], pipeline=pipeline_model.id)

    non_exclusive_tag = clean_client.get_tag("regular_tag_for_pipeline")
    with pytest.raises(ValueError):
        clean_client.update_tag(
            tag_name_or_id=non_exclusive_tag.id, exclusive=True
        )


@pipeline(
    tags=[Tag(name="cascade_tag", cascade=True)],
    enable_cache=False,
)
def pipeline_with_cascade_tag():
    """Pipeline definition to test the tag utils."""
    _ = step_single_output()


def test_cascade_tags_for_output_artifacts_of_cached_pipeline_run(
    clean_client,
):
    """Test that the cascade tags are added to the output artifacts of a cached step."""
    # Run the pipeline once without caching
    pipeline_with_cascade_tag()

    pipeline_runs = clean_client.list_pipeline_runs(sort_by="created")
    assert len(pipeline_runs.items) == 1
    assert (
        pipeline_runs.items[0].steps["step_single_output"].status
        == ExecutionStatus.COMPLETED
    )
    assert "cascade_tag" in [
        t.name
        for t in pipeline_runs.items[0]
        .steps["step_single_output"]
        .outputs["single"][0]
        .tags
    ]

    # Run it once again with caching
    pipeline_with_cascade_tag.configure(enable_cache=True)
    pipeline_with_cascade_tag()
    pipeline_runs = clean_client.list_pipeline_runs(sort_by="created")
    assert len(pipeline_runs.items) == 2
    assert (
        pipeline_runs.items[1].steps["step_single_output"].status
        == ExecutionStatus.CACHED
    )

    # Run it once again with caching and a new cascade tag
    pipeline_with_cascade_tag.configure(
        tags=[Tag(name="second_cascade_tag", cascade=True)]
    )
    pipeline_with_cascade_tag()
    pipeline_runs = clean_client.list_pipeline_runs(sort_by="created")
    assert len(pipeline_runs.items) == 3
    assert (
        pipeline_runs.items[2].steps["step_single_output"].status
        == ExecutionStatus.CACHED
    )

    assert "second_cascade_tag" in [
        t.name
        for t in pipeline_runs.items[0]
        .steps["step_single_output"]
        .outputs["single"][0]
        .tags
    ]
    assert "second_cascade_tag" in [
        t.name
        for t in pipeline_runs.items[2]
        .steps["step_single_output"]
        .outputs["single"][0]
        .tags
    ]

    # Run it once again with caching (preventing client side caching) and a new cascade tag
    os.environ[ENV_ZENML_PREVENT_CLIENT_SIDE_CACHING] = "true"
    pipeline_with_cascade_tag.configure(
        tags=[Tag(name="third_cascade_tag", cascade=True)]
    )
    pipeline_with_cascade_tag()

    pipeline_runs = clean_client.list_pipeline_runs(sort_by="created")
    assert len(pipeline_runs.items) == 4
    assert (
        pipeline_runs.items[3].steps["step_single_output"].status
        == ExecutionStatus.CACHED
    )

    assert "third_cascade_tag" in [
        t.name
        for t in pipeline_runs.items[0]
        .steps["step_single_output"]
        .outputs["single"][0]
        .tags
    ]
    assert "third_cascade_tag" in [
        t.name
        for t in pipeline_runs.items[3]
        .steps["step_single_output"]
        .outputs["single"][0]
        .tags
    ]
    os.environ.pop(ENV_ZENML_PREVENT_CLIENT_SIDE_CACHING, None)


def test_tags_with_special_characters():
    """Test that tags with special characters are handled correctly."""
    client = Client()

    tags = [
        f"_tag_with_underscore_{random_str(15)}_",
        f".tag.with.dots.{random_str(15)}.",
        f"/tag/with/slashes/{random_str(15)}/",
        f"=tag=with=equals={random_str(15)}=",
        f"?tag?with?question?marks?{random_str(15)}?",
        f".tag.with?special=characters/{random_str(15)}/",
        f"tag/{random_str(15)}?hydrate=false",
    ]

    tag_responses = []
    for tag in tags:
        tag_responses.append(client.create_tag(tag))

    with PipelineRunContext(1) as pipeline_runs:
        pipeline_run = pipeline_runs[0]
        add_tags(tags=tags, run=pipeline_run.id)

        pipeline_run = client.get_pipeline_run(pipeline_run.id)
        assert all(tag in [t.name for t in pipeline_run.tags] for tag in tags)
        remove_tags(tags=tags, run=pipeline_run.id)

    for tag_response in tag_responses:
        client.get_tag(tag_response.id)

    for tag in tags:
        client.get_tag(tag)
        client.delete_tag(tag)
