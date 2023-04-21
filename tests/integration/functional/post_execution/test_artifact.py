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
"""Integration tests for artifact post-execution functionality."""


from typing import List, Optional

from zenml.models.visualization_models import VisualizationModel
from zenml.pipelines.base_pipeline import BasePipeline
from zenml.post_execution.pipeline_run import get_unlisted_runs
from zenml.steps import step
from zenml.types import HTMLString


@step
def visualizable_step() -> HTMLString:
    """A step that returns a visualizable artifact."""
    return HTMLString("<h1>Test</h1>")


def test_disabling_artifact_visualization(clean_client, one_step_pipeline):
    """Test that disabling artifact visualization works."""

    # By default, artifact visualization should be enabled
    step_ = visualizable_step()
    pipe: BasePipeline = one_step_pipeline(step_)
    pipe.configure(enable_cache=False)
    pipe.run(unlisted=True)
    _assert_visualization_enabled()

    # Test disabling artifact visualization on pipeline level
    pipe.configure(enable_artifact_visualization=False)
    pipe.run(unlisted=True)
    _assert_visualization_disabled()

    pipe.configure(enable_artifact_visualization=True)
    pipe.run(unlisted=True)
    _assert_visualization_enabled()

    # Test disabling artifact visualization on step level
    # This should override the pipeline level setting
    step_.configure(enable_artifact_visualization=False)
    pipe.run(unlisted=True)
    _assert_visualization_disabled()

    step_.configure(enable_artifact_visualization=True)
    pipe.run(unlisted=True)
    _assert_visualization_enabled()

    # Test disabling artifact visualization on run level
    # This should override both the pipeline and step level setting
    pipe.run(unlisted=True, enable_artifact_visualization=False)
    _assert_visualization_disabled()

    pipe.configure(enable_artifact_visualization=False)
    step_.configure(enable_artifact_visualization=False)
    pipe.run(unlisted=True, enable_artifact_visualization=True)
    _assert_visualization_enabled()


def _assert_visualization_enabled():
    """Assert that artifact visualization was enabled in the last run."""
    assert _get_visualization_of_last_run()


def _assert_visualization_disabled():
    """Assert that artifact visualization was disabled in the last run."""
    assert not _get_visualization_of_last_run()


def _get_visualization_of_last_run() -> Optional[List[VisualizationModel]]:
    """Get the artifact visualization of the last run."""
    return get_unlisted_runs()[0].steps[0].output.visualizations
