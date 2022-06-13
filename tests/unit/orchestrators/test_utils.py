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


from zenml.orchestrators.utils import get_cache_status


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
