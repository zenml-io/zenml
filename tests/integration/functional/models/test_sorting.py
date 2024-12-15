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

from typing import Annotated

from zenml import Model, pipeline, step
from zenml.constants import (
    SORT_BY_LATEST_VERSION_KEY,
    SORT_PIPELINES_BY_LATEST_RUN_KEY,
)


@step
def first_step() -> Annotated[int, "int_artifact"]:
    """Step to return an int."""
    return 3


@pipeline(enable_cache=False)
def first_pipeline():
    """Pipeline definition to test the different sorting mechanisms."""
    _ = first_step()


@step
def second_step() -> Annotated[str, "str_artifact"]:
    """Step to return a string."""
    return "3"


@pipeline(enable_cache=False)
def second_pipeline():
    """Pipeline definition to test the different sorting mechanisms."""
    _ = second_step()


def test_sorting_entities(clean_client):
    """Testing different sorting functionalities."""
    first_pipeline_first_run = first_pipeline.with_options(
        model=Model(name="Model2"),
    )()
    _ = first_pipeline.with_options(
        model=Model(name="Model1", version="second"),
    )()
    _ = first_pipeline.with_options(
        model=Model(name="Model1", version="first"),
    )()
    second_pipeline_first_run = second_pipeline()

    # Sorting runs by the name of the user
    clean_client.list_pipeline_runs(sort_by="user")
    clean_client.list_pipeline_runs(sort_by="asc:user")
    clean_client.list_pipeline_runs(sort_by="desc:user")

    # Sorting runs by the name of the workspace
    clean_client.list_pipeline_runs(sort_by="workspace")
    clean_client.list_pipeline_runs(sort_by="asc:workspace")
    clean_client.list_pipeline_runs(sort_by="desc:workspace")

    # Sorting pipelines by latest run
    results = clean_client.list_pipelines(
        sort_by=f"{SORT_PIPELINES_BY_LATEST_RUN_KEY}"
    )
    assert results[0].id == first_pipeline_first_run.pipeline.id
    assert results[1].id == second_pipeline_first_run.pipeline.id

    results = clean_client.list_pipelines(
        sort_by=f"asc:{SORT_PIPELINES_BY_LATEST_RUN_KEY}"
    )
    assert results[0].id == first_pipeline_first_run.pipeline.id
    assert results[1].id == second_pipeline_first_run.pipeline.id

    results = clean_client.list_pipelines(
        sort_by=f"desc:{SORT_PIPELINES_BY_LATEST_RUN_KEY}"
    )
    assert results[0].id == second_pipeline_first_run.pipeline.id
    assert results[1].id == first_pipeline_first_run.pipeline.id

    # Sorting runs by pipeline name
    results = clean_client.list_pipeline_runs(sort_by="asc:name")
    assert results[0].name.startswith("first_")
    assert results[-1].name.startswith("second_")

    # Sorting runs by stack name
    clean_client.list_pipeline_runs(sort_by="asc:stack")
    clean_client.list_pipeline_runs(sort_by="desc:stack")

    # Sorting runs by model name
    results = clean_client.list_pipeline_runs(sort_by="asc:model")
    assert results[0].model_version.model.name == "Model1"
    assert results[-1].model_version.model.name == "Model2"
    clean_client.list_pipeline_runs(sort_by="desc:model")

    # Sorting runs by model version
    results = clean_client.list_pipeline_runs(sort_by="asc:model_version")

    assert results[0].model_version.name == "1"
    assert results[-1].model_version.name == "second"

    clean_client.list_pipeline_runs(sort_by="desc:model")

    # Sorting artifacts by latest version
    results = clean_client.list_artifacts(
        sort_by=f"asc:{SORT_BY_LATEST_VERSION_KEY}"
    )
    assert results[0].name == "int_artifact"

    results = clean_client.list_artifacts(
        sort_by=f"desc:{SORT_BY_LATEST_VERSION_KEY}"
    )
    assert results[0].name == "str_artifact"

    # Sorting models by latest version
    results = clean_client.list_models(
        sort_by=f"asc:{SORT_BY_LATEST_VERSION_KEY}"
    )
    assert results[0].name == "Model2"

    results = clean_client.list_models(
        sort_by=f"desc:{SORT_BY_LATEST_VERSION_KEY}"
    )
    assert results[0].name == "Model1"
