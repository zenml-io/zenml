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
from typing_extensions import Annotated

from zenml import Model, pipeline, step
from zenml.client import Client
from zenml.models.v2.core.pipeline_run import PipelineRunResponse


@step
def my_step() -> Annotated[str, "artifact_{date}_{time}_{placeholder}"]:
    return "42"


@pipeline(
    enable_cache=False,
    model=Model(
        name="model_{date}_{time}_{placeholder}",
        version="model_version_{date}_{time}_{placeholder}",
    ),
    substitutions={"placeholder": "42"},
)
def my_pipeline():
    my_step()


def test_that_naming_is_consistent_across_the_board(clean_client: Client):
    """Test that naming is consistent across the entities for standard placeholders.

    Putting simply: `time` and `date` placeholders should be consistent across
    all entities in the pipeline run.
    """
    p: PipelineRunResponse = my_pipeline.with_options(
        run_name="run_{date}_{time}_{placeholder}"
    )()
    assert p.name.startswith("run_")
    tail = p.name.split("run_")[1]
    mv = clean_client.get_model_version(
        model_name_or_id=f"model_{tail}",
        model_version_name_or_number_or_id=f"model_version_{tail}",
    )
    assert mv.name == f"model_version_{tail}"
    assert mv.model.name == f"model_{tail}"
    assert (
        clean_client.get_artifact_version(f"artifact_{tail}").name
        == f"artifact_{tail}"
    )
