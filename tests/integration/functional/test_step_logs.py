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


from tests.integration.functional.conftest import step_with_logs
from zenml.pipelines.base_pipeline import BasePipeline
from zenml.post_execution.pipeline_run import get_unlisted_runs
from zenml.post_execution.step import StepView


def _get_first_step_of_last_run() -> StepView:
    """Get the output of the last run."""
    return get_unlisted_runs()[0].steps[0]


def _assert_step_logs_enabled():
    """Assert that step logs were enabled in the last run."""
    assert _get_first_step_of_last_run().logs


def _assert_step_logs_disabled():
    """Assert that step logs were disabled in the last run."""
    assert not _get_first_step_of_last_run().logs


def test_disabling_step_logs(clean_client, one_step_pipeline):
    """Test that disabling step logs works."""

    # By default, step logs should be enabled
    step_ = step_with_logs()
    pipe: BasePipeline = one_step_pipeline(step_)
    pipe.configure(enable_cache=False)
    pipe.run(unlisted=True)
    _assert_step_logs_enabled()

    # Test disabling step logs on pipeline level
    pipe.configure(enable_step_logs=False)
    pipe.run(unlisted=True)
    _assert_step_logs_disabled()

    pipe.configure(enable_step_logs=True)
    pipe.run(unlisted=True)
    _assert_step_logs_enabled()

    # Test disabling step logs on step level
    # This should override the pipeline level setting
    step_.configure(enable_step_logs=False)
    pipe.run(unlisted=True)
    _assert_step_logs_disabled()

    step_.configure(enable_step_logs=True)
    pipe.run(unlisted=True)
    _assert_step_logs_enabled()

    # Test disabling step logs on run level
    # This should override both the pipeline and step level setting
    pipe.run(unlisted=True, enable_step_logs=False)
    _assert_step_logs_disabled()

    pipe.configure(enable_step_logs=False)
    step_.configure(enable_step_logs=False)
    pipe.run(unlisted=True, enable_step_logs=True)
    _assert_step_logs_enabled()
