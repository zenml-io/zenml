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


from typing import Annotated, Tuple

import pytest

from zenml import ArtifactConfig, Tag, add_tags, pipeline, remove_tags, step


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
