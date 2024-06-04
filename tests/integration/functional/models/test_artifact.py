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

import pytest
from typing_extensions import Annotated

from tests.integration.functional.conftest import (
    constant_int_output_test_step,
    visualizable_step,
)
from zenml import step
from zenml.artifacts.artifact_config import ArtifactConfig
from zenml.artifacts.utils import load_artifact_visualization
from zenml.enums import ExecutionStatus
from zenml.exceptions import EntityExistsError
from zenml.models import (
    ArtifactVersionResponse,
    ArtifactVisualizationResponse,
    RunMetadataResponse,
)
from zenml.pipelines.base_pipeline import BasePipeline

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


@step
def auto_versioned_step() -> Annotated[int, ArtifactConfig(name="aria")]:
    return 1


@step
def manual_string_version_step() -> (
    Annotated[int, ArtifactConfig(name="aria", version="cat")]
):
    return 1


@step
def manual_int_version_step() -> (
    Annotated[int, ArtifactConfig(name="aria", version=10)]
):
    return 1


def test_artifact_versioning(clean_client: "Client", one_step_pipeline):
    """Test artifact versioning."""
    # First auto-incremented artifact version starts at 1
    pipe: BasePipeline = one_step_pipeline(auto_versioned_step)
    pipe.run(enable_cache=False)
    artifact = pipe.model.last_run.steps["step_"].output
    assert str(artifact.version) == "1"

    # Manual version should be applied
    pipe: BasePipeline = one_step_pipeline(manual_string_version_step)
    pipe.run(enable_cache=False)
    artifact = pipe.model.last_run.steps["step_"].output
    assert artifact.version == "cat"

    # Next auto-incremented artifact version is 2
    pipe: BasePipeline = one_step_pipeline(auto_versioned_step)
    pipe.run(enable_cache=False)
    artifact = pipe.model.last_run.steps["step_"].output
    assert str(artifact.version) == "2"

    # Manual int version should be applied too
    pipe: BasePipeline = one_step_pipeline(manual_int_version_step)
    pipe.run(enable_cache=False)
    artifact = pipe.model.last_run.steps["step_"].output
    assert str(artifact.version) == "10"

    # Next auto-incremented artifact version is 11
    pipe: BasePipeline = one_step_pipeline(auto_versioned_step)
    pipe.run(enable_cache=False)
    artifact = pipe.model.last_run.steps["step_"].output
    assert str(artifact.version) == "11"


@step
def duplicate_int_version_step() -> (
    Annotated[int, ArtifactConfig(name="aria", version="1")]
):
    return 1


def test_artifact_versioning_duplication(
    clean_client: "Client", one_step_pipeline
):
    """Test that duplicated artifact versions are not allowed."""
    pipe: BasePipeline = one_step_pipeline(auto_versioned_step)
    pipe.run(enable_cache=False)
    artifact = pipe.model.last_run.steps["step_"].output
    assert artifact.version == "1"

    pipe: BasePipeline = one_step_pipeline(manual_string_version_step)
    pipe.run(enable_cache=False)
    artifact = pipe.model.last_run.steps["step_"].output
    assert artifact.version == "cat"

    # Test 1: rerunning pipeline with same manual version fails
    pipe: BasePipeline = one_step_pipeline(manual_string_version_step)
    with pytest.raises(EntityExistsError):
        pipe.run(enable_cache=False)

    # Test 2: running pipeline with a manual version corresponding to an
    # existing auto-incremented version fails
    pipe: BasePipeline = one_step_pipeline(duplicate_int_version_step)
    with pytest.raises(EntityExistsError):
        pipe.run(enable_cache=False)


@step
def tagged_artifact_step() -> (
    Annotated[int, ArtifactConfig(name="aria", tags=["cat", "grumpy"])]
):
    return 7


def test_artifact_tagging(clean_client: "Client", one_step_pipeline):
    """Test artifact tagging."""

    pipe: BasePipeline = one_step_pipeline(tagged_artifact_step)
    pipe.run()
    artifact = pipe.model.last_run.steps["step_"].output
    assert {t.name for t in artifact.tags} == {"cat", "grumpy"}


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


def _get_output_of_last_run(clean_client: "Client") -> ArtifactVersionResponse:
    """Get the output of the last run."""
    return list(clean_client.list_pipeline_runs()[0].steps.values())[0].output


def _get_visualizations_of_last_run(
    clean_client: "Client",
) -> Optional[List[ArtifactVisualizationResponse]]:
    """Get the artifact visualizations of the last run."""
    return _get_output_of_last_run(clean_client).visualizations


def _get_metadata_of_last_run(
    clean_client: "Client",
) -> Dict[str, "RunMetadataResponse"]:
    """Get the artifact metadata of the last run."""
    return _get_output_of_last_run(clean_client).run_metadata


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
