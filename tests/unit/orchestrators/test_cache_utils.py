#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from datetime import datetime
from unittest import mock
from unittest.mock import ANY
from uuid import uuid4

import pytest

from zenml.config.compiler import Compiler
from zenml.config.step_configurations import Step
from zenml.enums import ExecutionStatus
from zenml.models import (
    ProjectResponseModel,
    StepRunResponseModel,
    UserResponseModel,
)
from zenml.orchestrators import cache_utils
from zenml.steps import Output, step
from zenml.steps.base_step import BaseStep


def test_is_cache_enabled():
    """Unit test for `is_cache_enabled()`.

    Tests that:
    - caching is enabled by default (when neither step nor pipeline set it),
    - caching is always enabled if explicitly enabled for the step,
    - caching is always disabled if explicitly disabled for the step,
    - caching is set to the pipeline cache if not configured for the step.
    """
    # Caching is enabled by default
    assert (
        cache_utils.is_cache_enabled(
            step_enable_cache=None, pipeline_enable_cache=None
        )
        is True
    )

    # Caching is always enabled if explicitly enabled for the step
    assert (
        cache_utils.is_cache_enabled(
            step_enable_cache=True,
            pipeline_enable_cache=True,
        )
        is True
    )

    assert (
        cache_utils.is_cache_enabled(
            step_enable_cache=True,
            pipeline_enable_cache=False,
        )
        is True
    )

    assert (
        cache_utils.is_cache_enabled(
            step_enable_cache=True,
            pipeline_enable_cache=None,
        )
        is True
    )

    # Caching is always disabled if explicitly disabled for the step
    assert (
        cache_utils.is_cache_enabled(
            step_enable_cache=False,
            pipeline_enable_cache=True,
        )
        is False
    )

    assert (
        cache_utils.is_cache_enabled(
            step_enable_cache=False,
            pipeline_enable_cache=False,
        )
        is False
    )

    assert (
        cache_utils.is_cache_enabled(
            step_enable_cache=False,
            pipeline_enable_cache=None,
        )
        is False
    )

    # Caching is set to the pipeline cache if not configured for the step
    assert (
        cache_utils.is_cache_enabled(
            step_enable_cache=None,
            pipeline_enable_cache=True,
        )
        is True
    )

    assert (
        cache_utils.is_cache_enabled(
            step_enable_cache=None,
            pipeline_enable_cache=False,
        )
        is False
    )


def _compile_step(step: BaseStep) -> Step:
    # Call the step here to finalize the configuration
    step()

    compiler = Compiler()
    return compiler._compile_step(
        step=step,
        pipeline_settings={},
        pipeline_extra={},
        stack=None,
    )


@step
def _cache_test_step() -> Output(output_1=str, output_2=int):
    return "Hello World", 42


@pytest.fixture
def generate_cache_key_kwargs(local_artifact_store):
    """Returns a dictionary of inputs for the cache key generation."""
    return {
        "step": _compile_step(_cache_test_step()),
        "input_artifact_ids": {"input_1": uuid4()},
        "artifact_store": local_artifact_store,
        "project_id": uuid4(),
    }


def test_generate_cache_key_is_deterministic(generate_cache_key_kwargs):
    """Check that the cache key does not change if the inputs are the same."""
    key_1 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    key_2 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    assert key_1 == key_2


def test_generate_cache_key_considers_project_id(generate_cache_key_kwargs):
    """Check that the cache key changes if the project ID changes."""
    key_1 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    generate_cache_key_kwargs["project_id"] = uuid4()
    key_2 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    assert key_1 != key_2


def test_generate_cache_key_considers_artifact_store_id(
    generate_cache_key_kwargs,
):
    """Check that the cache key changes if the artifact store ID changes."""
    key_1 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    generate_cache_key_kwargs["artifact_store"].id = uuid4()
    key_2 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    assert key_1 != key_2


def test_generate_cache_key_considers_artifact_store_path(
    generate_cache_key_kwargs, mocker
):
    """Check that the cache key changes if the artifact store path changes."""
    key_1 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    mock_path = mock.PropertyMock(return_value="new/path")
    mocker.patch.object(
        type(generate_cache_key_kwargs["artifact_store"]),
        "path",
        new_callable=mock_path,
    )
    key_2 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    assert key_1 != key_2


def test_generate_cache_key_considers_step_source(generate_cache_key_kwargs):
    """Check that the cache key changes if the step source changes."""
    key_1 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    generate_cache_key_kwargs["step"].spec.__config__.allow_mutation = True
    generate_cache_key_kwargs["step"].spec.source = "Some.new.source"
    key_2 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    assert key_1 != key_2


def test_generate_cache_key_considers_step_parameters(
    generate_cache_key_kwargs,
):
    """Check that the cache key changes if the step parameters change."""
    key_1 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    generate_cache_key_kwargs["step"].config.__config__.allow_mutation = True
    generate_cache_key_kwargs["step"].config.parameters = {"new_param": 42}
    key_2 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    assert key_1 != key_2


def test_generate_cache_key_considers_input_artifacts(
    generate_cache_key_kwargs,
):
    """Check that the cache key changes if the input artifacts change."""
    key_1 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    generate_cache_key_kwargs["input_artifact_ids"] = {"input_1": uuid4()}
    key_2 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    assert key_1 != key_2


def test_generate_cache_key_considers_output_artifacts(
    generate_cache_key_kwargs,
):
    """Check that the cache key changes if the output artifacts change."""
    key_1 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    generate_cache_key_kwargs["step"].config.__config__.allow_mutation = True
    generate_cache_key_kwargs["step"].config.outputs.pop("output_1")
    key_2 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    assert key_1 != key_2


def test_generate_cache_key_considers_caching_parameters(
    generate_cache_key_kwargs,
):
    """Check that the cache key changes if the caching parameters change."""
    key_1 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    generate_cache_key_kwargs["step"].config.__config__.allow_mutation = True
    generate_cache_key_kwargs["step"].config.caching_parameters = {
        "Aria hates caching": False
    }
    key_2 = cache_utils.generate_cache_key(**generate_cache_key_kwargs)
    assert key_1 != key_2


def _create_step_run(
    user: UserResponseModel,
    project: ProjectResponseModel,
):
    """Creates a step run with the given user and project."""
    step = Step.parse_obj(
        {
            "spec": {"source": "", "upstream_steps": [], "inputs": {}},
            "config": {
                "name": "step_name",
            },
        }
    )

    return StepRunResponseModel(
        id=uuid4(),
        name="sample_step",
        pipeline_run_id=uuid4(),
        step=step,
        status=ExecutionStatus.COMPLETED,
        created=datetime.now(),
        updated=datetime.now(),
        project=project,
        user=user,
    )


def test_fetching_cached_step_run(
    mocker, sample_user_model, sample_project_model
):
    """Tests fetching a cached step run."""
    step_run_1 = _create_step_run(
        user=sample_user_model, project=sample_project_model
    )
    step_run_2 = _create_step_run(
        user=sample_user_model, project=sample_project_model
    )

    assert step_run_2.created > step_run_1.created

    mock_list_run_steps = mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.list_run_steps",
        return_value=[step_run_1, step_run_2],
    )

    cached_step = cache_utils.get_cached_step_run(cache_key="cache_key")
    assert cached_step is step_run_2
    mock_list_run_steps.assert_called_with(
        project_id=ANY,
        cache_key="cache_key",
        status=ExecutionStatus.COMPLETED,
    )

    # Switch the order of the returned step runs
    mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.list_run_steps",
        return_value=[step_run_2, step_run_1],
    )

    cached_step = cache_utils.get_cached_step_run(cache_key="cache_key")
    assert cached_step is step_run_2

    # No step run found
    mocker.patch(
        "zenml.zen_stores.sql_zen_store.SqlZenStore.list_run_steps",
        return_value=[],
    )

    cached_step = cache_utils.get_cached_step_run(cache_key="cache_key")
    assert cached_step is None
