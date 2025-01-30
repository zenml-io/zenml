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


from typing import Annotated, Tuple

import pytest

from zenml import Model, log_metadata, pipeline, step


@step
def step_multiple_calls() -> None:
    """Step calls log_metadata twice, latest value should be returned."""
    log_metadata(metadata={"blupus": 1})
    log_metadata(metadata={"blupus": 2})


@step
def step_single_output() -> Annotated[int, "first"]:
    """Step that tests the usage of infer_artifact flag."""
    log_metadata(metadata={"aria": 1}, infer_artifact=True)
    log_metadata(
        metadata={"aria": 2}, infer_artifact=True, artifact_name="first"
    )
    return 1


@step
def step_multiple_outputs() -> (
    Tuple[Annotated[int, "second"], Annotated[int, "third"]]
):
    """Step that tests infer_artifact flag with multiple outputs."""
    log_metadata(
        metadata={"axl": 1}, infer_artifact=True, artifact_name="second"
    )
    return 1, 2


@step
def step_pipeline_model() -> None:
    """Step that tests the infer_model flag."""
    log_metadata(metadata={"p": 1}, infer_model=True)


@step(model=Model(name="model_name", version="89a"))
def step_step_model() -> None:
    """Step that tests the infer_model flag with a custom model version."""
    log_metadata(metadata={"s": 1}, infer_model=True)


@pipeline(model=Model(name="model_name", version="a89"), enable_cache=True)
def pipeline_to_log_metadata():
    """Pipeline definition to test the metadata utils."""
    step_multiple_calls()
    step_single_output()
    step_multiple_outputs()
    step_pipeline_model()
    step_step_model()


def test_metadata_utils(clean_client):
    """Testing different functionalities of the log_metadata function."""
    # Run the pipeline
    first_run = pipeline_to_log_metadata()
    first_steps = first_run.steps

    # Check if the metadata was tagged correctly
    assert first_run.run_metadata["step_multiple_calls::blupus"] == 2
    assert first_steps["step_multiple_calls"].run_metadata["blupus"] == 2
    assert (
        first_steps["step_single_output"]
        .outputs["first"][0]
        .run_metadata["aria"]
        == 2
    )
    assert (
        first_steps["step_multiple_outputs"]
        .outputs["second"][0]
        .run_metadata["axl"]
        == 1
    )

    model_version_s = Model(name="model_name", version="89a")
    assert model_version_s.run_metadata["s"] == 1

    model_version_p = Model(name="model_name", version="a89")
    assert model_version_p.run_metadata["p"] == 1

    # Manually tag the run
    log_metadata(
        metadata={"manual_run": True}, run_id_name_or_prefix=first_run.id
    )

    # Manually tag the step
    log_metadata(
        metadata={"manual_step_1": True},
        step_id=first_run.steps["step_multiple_calls"].id,
    )
    log_metadata(
        metadata={"manual_step_2": True},
        step_name="step_multiple_calls",
        run_id_name_or_prefix=first_run.id,
    )

    # Manually tag a model
    log_metadata(
        metadata={"manual_model_1": True}, model_version_id=model_version_p.id
    )
    log_metadata(
        metadata={"manual_model_2": True},
        model_name=model_version_p.name,
        model_version=model_version_p.version,
    )

    # Manually tag an artifact
    log_metadata(
        metadata={"manual_artifact_1": True},
        artifact_version_id=first_run.steps["step_single_output"].output.id,
    )
    log_metadata(
        metadata={"manual_artifact_2": True},
        artifact_name=first_run.steps["step_single_output"].output.name,
        artifact_version=first_run.steps["step_single_output"].output.version,
    )

    # Manually tag one step to test the caching logic later
    log_metadata(
        metadata={"blupus": 3},
        step_id=first_run.steps["step_multiple_calls"].id,
    )

    # Fetch the run and steps again
    first_run_fetched = clean_client.get_pipeline_run(
        name_id_or_prefix=first_run.id
    )
    first_steps_fetched = first_run_fetched.steps

    assert first_run_fetched.run_metadata["manual_run"]
    assert first_run_fetched.run_metadata["step_multiple_calls::manual_step_1"]
    assert first_run_fetched.run_metadata["step_multiple_calls::manual_step_2"]
    assert first_steps_fetched["step_multiple_calls"].run_metadata[
        "manual_step_1"
    ]
    assert first_steps_fetched["step_multiple_calls"].run_metadata[
        "manual_step_2"
    ]
    assert first_steps_fetched["step_single_output"].output.run_metadata[
        "manual_artifact_1"
    ]
    assert first_steps_fetched["step_single_output"].output.run_metadata[
        "manual_artifact_2"
    ]

    # Fetch the model again
    model_version_p_fetched = Model(name="model_name", version="a89")

    assert model_version_p_fetched.run_metadata["manual_model_1"]
    assert model_version_p_fetched.run_metadata["manual_model_2"]

    # Run the cached pipeline
    second_run = pipeline_to_log_metadata()
    assert second_run.steps["step_multiple_calls"].run_metadata["blupus"] == 2

    # Test some of the invalid usages
    with pytest.raises(ValueError):
        log_metadata(metadata={"auto_step_1": True})

    with pytest.raises(ValueError):
        log_metadata(metadata={"auto_model_1": True}, infer_model=True)

    with pytest.raises(ValueError):
        log_metadata(metadata={"auto_artifact_1": True}, infer_artifact=True)
