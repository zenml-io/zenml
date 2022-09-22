#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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


import json
import os

from zenml.constants import (
    MLMD_CONTEXT_PIPELINE_CONFIG_PROPERTY_NAME,
    MLMD_CONTEXT_STACK_PROPERTY_NAME,
    MLMD_CONTEXT_STEP_CONFIG_PROPERTY_NAME,
    ZENML_MLMD_CONTEXT_TYPE,
)
from zenml.orchestrators.utils import get_cache_status
from zenml.pipelines import pipeline
from zenml.repository import Repository
from zenml.steps import step


def test_get_cache_status_raises_no_error_when_none_passed():
    """Ensure get_cache_status raises no error when None is passed."""
    get_cache_status(None)


def test_get_cache_status_works_when_running_pipeline_twice(clean_repo, mocker):
    """Check that steps are cached when a pipeline is run twice successively."""
    from zenml.pipelines import pipeline
    from zenml.steps import step

    @step
    def step_one() -> int:
        return 1

    @pipeline
    def some_pipeline(
        step_one,
    ):
        step_one()

    pipeline = some_pipeline(
        step_one=step_one(),
    )

    def _expect_not_cached(execution_info):
        return_value = get_cache_status(execution_info)
        assert return_value is False
        return return_value

    def _expect_cached(execution_info):
        return_value = get_cache_status(execution_info)
        assert return_value is True
        return return_value

    mock = mocker.patch(
        "zenml.orchestrators.base_orchestrator.get_cache_status",
        side_effect=_expect_not_cached,
    )
    pipeline.run()
    mock.assert_called_once()

    mock = mocker.patch(
        "zenml.orchestrators.base_orchestrator.get_cache_status",
        side_effect=_expect_cached,
    )
    pipeline.run()
    mock.assert_called_once()


def test_pipeline_storing_context_in_the_metadata_store():
    """Tests that storing the ZenML context in the metadata store works."""

    @step
    def some_step_1() -> int:
        return 3

    @pipeline
    def p(step_):
        step_()

    pipeline_ = p(some_step_1())
    pipeline_.run()

    repo = Repository()
    contexts = repo.active_stack.metadata_store.store.get_contexts_by_type(
        ZENML_MLMD_CONTEXT_TYPE
    )

    assert len(contexts) == 1

    assert contexts[0].custom_properties[
        MLMD_CONTEXT_STACK_PROPERTY_NAME
    ].string_value == json.dumps(repo.active_stack.dict(), sort_keys=True)

    from zenml.config.compiler import Compiler
    from zenml.config.pipeline_configurations import PipelineRunConfiguration

    compiled = Compiler().compile(
        pipeline=pipeline_,
        stack=repo.active_stack,
        run_configuration=PipelineRunConfiguration(),
    )
    dag_filepath = os.path.abspath(__file__)
    compiled.pipeline.extra["dag_filepath"] = dag_filepath
    compiled.steps["step_"].config.extra["dag_filepath"] = dag_filepath

    expected_pipeline_config = compiled.pipeline.json(sort_keys=True)
    assert (
        contexts[0]
        .custom_properties[MLMD_CONTEXT_PIPELINE_CONFIG_PROPERTY_NAME]
        .string_value
        == expected_pipeline_config
    )

    expected_step_config = compiled.steps["step_"].json(sort_keys=True)
    assert (
        contexts[0]
        .custom_properties[MLMD_CONTEXT_STEP_CONFIG_PROPERTY_NAME]
        .string_value
        == expected_step_config
    )
