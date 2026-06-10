#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Tests for start/end hook validation and decorator wiring."""

from typing import Optional

import pytest

from zenml.exceptions import HookValidationException
from zenml.hooks.validation import resolve_and_validate_hook
from zenml.pipelines import pipeline
from zenml.steps import step


def on_start_no_params() -> None:
    pass


def on_start_with_param(a: int) -> None:
    pass


def on_end_no_params() -> None:
    pass


def on_end_with_exception(exception: Optional[BaseException] = None) -> None:
    pass


def on_end_with_too_many_params(a: int, b: int) -> None:
    pass


def _validate_on_end(func):
    return resolve_and_validate_hook(func, Exception())


@pytest.mark.parametrize(
    "func",
    [on_end_no_params, on_end_with_exception],
)
def test_on_end_accepts_supported_signatures(func):
    """Tests that on_end accepts no-arg and exception signatures."""
    source, _ = _validate_on_end(func)
    assert source is not None


def test_on_end_rejects_too_many_params():
    """Tests that on_end rejects more than one argument."""
    with pytest.raises(HookValidationException):
        _validate_on_end(on_end_with_too_many_params)


def test_on_start_accepts_no_params():
    """Tests that on_start accepts a no-argument function."""
    source, _ = resolve_and_validate_hook(on_start_no_params)
    assert source is not None


def test_on_start_rejects_required_param():
    """Tests that on_start rejects a function with a required argument."""
    with pytest.raises(HookValidationException):
        resolve_and_validate_hook(on_start_with_param)


def test_step_decorator_stores_hook_sources():
    """Tests that the step decorator stores start/end hook sources."""

    @step(on_start=on_start_no_params, on_end=on_end_with_exception)
    def my_step() -> None:
        pass

    assert my_step.configuration.start_hook_source is not None
    assert my_step.configuration.end_hook_source is not None


def test_pipeline_decorator_stores_hook_sources():
    """Tests that the pipeline decorator stores start/end hook sources."""

    @pipeline(on_start=on_start_no_params, on_end=on_end_with_exception)
    def my_pipeline() -> None:
        pass

    assert my_pipeline.configuration.start_hook_source is not None
    assert my_pipeline.configuration.end_hook_source is not None
