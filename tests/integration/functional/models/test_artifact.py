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
"""Integration tests for artifact models."""


from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from typing_extensions import Annotated

from tests.integration.functional.conftest import (
    constant_int_output_test_step,
    visualizable_step,
)
from zenml import step
from zenml.enums import ExecutionStatus
from zenml.models.artifact_models import ArtifactResponseModel
from zenml.models.run_metadata_models import RunMetadataResponseModel
from zenml.models.visualization_models import VisualizationModel
from zenml.pipelines.base_pipeline import BasePipeline
from zenml.utils.artifact_utils import load_artifact_visualization

if TYPE_CHECKING:
    from zenml.client import Client


def test_default_artifact_name(clean_client: "Client", one_step_pipeline):
    """Integration test for default artifact names."""
    step_ = constant_int_output_test_step()
    pipe: BasePipeline = one_step_pipeline(step_)
    pipe.run()
    pipeline_run = pipe.model.last_run
    step_run = pipeline_run.steps["step_"]
    artifact = step_run.output
    assert artifact.name == f"{pipeline_run.pipeline.name}::step_::output"


@step
def custom_artifact_name_test_step() -> Annotated[int, "number_7"]:
    return 7


def test_custom_artifact_name(clean_client: "Client", one_step_pipeline):
    """Integration test for custom artifact names."""
    pipe: BasePipeline = one_step_pipeline(custom_artifact_name_test_step)
    pipe.run()
    pipeline_run = pipe.model.last_run
    step_run = pipeline_run.steps["step_"]
    artifact = step_run.output
    assert artifact.name == "number_7"


@step
def multi_output_test_step() -> Tuple[Annotated[int, "number_7"], int]:
    return 7, 42


def test_multi_output_artifact_names(
    clean_client: "Client", one_step_pipeline
):
    """Integration test for multi-output artifact names."""
    pipe: BasePipeline = one_step_pipeline(multi_output_test_step)
    pipe.run()
    pipeline_run = pipe.model.last_run
    step_run = pipeline_run.steps["step_"]
    artifact_1 = step_run.outputs["number_7"]
    artifact_2 = step_run.outputs["output_1"]
    assert artifact_1.name == "number_7"
    assert artifact_2.name == f"{pipeline_run.pipeline.name}::step_::output_1"


# TODO: make more efficient once manual versioning exists
def test_auto_incremented_artifact_versioning(
    clean_client: "Client", one_step_pipeline
):
    """Test auto-increment default artifact versioning."""
    step_ = constant_int_output_test_step()
    pipe: BasePipeline = one_step_pipeline(step_)

    for i in range(1, 12):
        pipe.run(enable_cache=False)
        pipeline_run = pipe.model.last_run
        step_run = pipeline_run.steps["step_"]
        artifact = step_run.output
        assert artifact.version == str(i)


def test_artifact_step_run_linkage(clean_client: "Client", one_step_pipeline):
    """Integration test for `artifact.step` and `artifact.run` properties."""
    step_ = constant_int_output_test_step()
    pipe: BasePipeline = one_step_pipeline(step_)
    pipe.run()

    # Non-cached run: producer step is the step that was just run
    pipeline_run = pipe.model.last_run
    step_run = pipeline_run.steps["step_"]
    artifact = step_run.output
    assert artifact.step == step_run
    assert artifact.run == pipeline_run

    # Cached run: producer step is the step that was cached
    pipe.run()
    step_run_2 = pipe.model.last_run.steps["step_"]
    assert step_run_2.status == ExecutionStatus.CACHED
    assert step_run_2.original_step_run_id == step_run.id
    artifact_2 = step_run_2.output
    assert artifact_2.step == step_run
    assert artifact_2.run == pipeline_run


def test_disabling_artifact_visualization(
    clean_client: "Client", one_step_pipeline
):
    """Test that disabling artifact visualization works."""

    # By default, artifact visualization should be enabled
    step_ = visualizable_step()
    pipe: BasePipeline = one_step_pipeline(step_)
    pipe.configure(enable_cache=False)
    pipe.run(unlisted=True)
    _assert_visualization_enabled(clean_client)

    # Test disabling artifact visualization on pipeline level
    pipe.configure(enable_artifact_visualization=False)
    pipe.run(unlisted=True)
    _assert_visualization_disabled(clean_client)

    pipe.configure(enable_artifact_visualization=True)
    pipe.run(unlisted=True)
    _assert_visualization_enabled(clean_client)

    # Test disabling artifact visualization on step level
    # This should override the pipeline level setting
    step_.configure(enable_artifact_visualization=False)
    pipe.run(unlisted=True)
    _assert_visualization_disabled(clean_client)

    step_.configure(enable_artifact_visualization=True)
    pipe.run(unlisted=True)
    _assert_visualization_enabled(clean_client)

    # Test disabling artifact visualization on run level
    # This should override both the pipeline and step level setting
    pipe.run(unlisted=True, enable_artifact_visualization=False)
    _assert_visualization_disabled(clean_client)

    pipe.configure(enable_artifact_visualization=False)
    step_.configure(enable_artifact_visualization=False)
    pipe.run(unlisted=True, enable_artifact_visualization=True)
    _assert_visualization_enabled(clean_client)


def test_load_artifact_visualization(clean_client, one_step_pipeline):
    """Integration test for loading artifact visualizations."""
    step_ = visualizable_step()
    pipe: BasePipeline = one_step_pipeline(step_)
    pipe.configure(enable_cache=False)
    pipe.run(unlisted=True)

    artifact = _get_output_of_last_run(clean_client)
    assert artifact.visualizations
    for i in range(len(artifact.visualizations)):
        load_artifact_visualization(
            artifact=artifact, index=i, zen_store=clean_client.zen_store
        )


def test_disabling_artifact_metadata(clean_client, one_step_pipeline):
    """Test that disabling artifact metadata works."""

    # By default, artifact metadata should be enabled
    step_ = visualizable_step()
    pipe: BasePipeline = one_step_pipeline(step_)
    pipe.configure(enable_cache=False)
    pipe.run(unlisted=True)
    _assert_metadata_enabled(clean_client)

    # Test disabling artifact metadata on pipeline level
    pipe.configure(enable_artifact_metadata=False)
    pipe.run(unlisted=True)
    _assert_metadata_disabled(clean_client)

    pipe.configure(enable_artifact_metadata=True)
    pipe.run(unlisted=True)
    _assert_metadata_enabled(clean_client)

    # Test disabling artifact metadata on step level
    # This should override the pipeline level setting
    step_.configure(enable_artifact_metadata=False)
    pipe.run(unlisted=True)
    _assert_metadata_disabled(clean_client)

    step_.configure(enable_artifact_metadata=True)
    pipe.run(unlisted=True)
    _assert_metadata_enabled(clean_client)

    # Test disabling artifact metadata on run level
    # This should override both the pipeline and step level setting
    pipe.run(unlisted=True, enable_artifact_metadata=False)
    _assert_metadata_disabled(clean_client)

    pipe.configure(enable_artifact_metadata=False)
    step_.configure(enable_artifact_metadata=False)
    pipe.run(unlisted=True, enable_artifact_metadata=True)
    _assert_metadata_enabled(clean_client)


def _get_output_of_last_run(clean_client: "Client") -> ArtifactResponseModel:
    """Get the output of the last run."""
    return list(clean_client.list_pipeline_runs()[0].steps.values())[0].output


def _get_visualizations_of_last_run(
    clean_client: "Client",
) -> Optional[List[VisualizationModel]]:
    """Get the artifact visualizations of the last run."""
    return _get_output_of_last_run(clean_client).visualizations


def _get_metadata_of_last_run(
    clean_client: "Client",
) -> Dict[str, "RunMetadataResponseModel"]:
    """Get the artifact metadata of the last run."""
    return _get_output_of_last_run(clean_client).metadata


def _assert_visualization_enabled(clean_client: "Client"):
    """Assert that artifact visualization was enabled in the last run."""
    assert _get_visualizations_of_last_run(clean_client)


def _assert_visualization_disabled(clean_client: "Client"):
    """Assert that artifact visualization was disabled in the last run."""
    assert not _get_visualizations_of_last_run(clean_client)


def _assert_metadata_enabled(clean_client: "Client"):
    """Assert that artifact metadata was enabled in the last run."""
    assert _get_metadata_of_last_run(clean_client)


def _assert_metadata_disabled(clean_client: "Client"):
    """Assert that artifact metadata was disabled in the last run."""
    assert not _get_metadata_of_last_run(clean_client)
