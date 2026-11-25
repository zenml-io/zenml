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


from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from zenml.enums import ExecutionStatus, HookType
from zenml.models import HookInvocationFilter, HookInvocationRequest


def _request_kwargs(**overrides):
    """Build the mandatory kwargs for a hook invocation request."""
    kwargs = dict(
        project=uuid4(),
        hook_type=HookType.CUSTOM,
        status=ExecutionStatus.COMPLETED,
        start_time=datetime.utcnow(),
        pipeline_run_id=uuid4(),
    )
    kwargs.update(overrides)
    return kwargs


@pytest.mark.parametrize(
    "name",
    [
        "pre_tool_call",
        "before_model_request",
        "pydantic_ai.before_tool_execute",
        "before-model",
        "_private",
        "A1.b-c_d",
    ],
)
def test_hook_invocation_request_accepts_valid_names(name: str):
    """Test that valid custom hook names pass validation."""
    request = HookInvocationRequest(**_request_kwargs(name=name))
    assert request.name == name


def test_hook_invocation_request_accepts_none_name():
    """Test that a missing custom hook name is allowed."""
    request = HookInvocationRequest(**_request_kwargs(name=None))
    assert request.name is None


@pytest.mark.parametrize(
    "name",
    [
        "1starts_with_digit",
        ".starts_with_dot",
        "-starts_with_hyphen",
        "has space",
        "foo/bar",
        "foo@bar",
        "",
    ],
)
def test_hook_invocation_request_rejects_invalid_names(name: str):
    """Test that invalid custom hook names fail validation."""
    with pytest.raises(ValidationError):
        HookInvocationRequest(**_request_kwargs(name=name))


def test_hook_invocation_filter_does_not_validate_name():
    """Test that the filter does not enforce the name regex."""
    filter_model = HookInvocationFilter(name="has space")
    assert filter_model.name == "has space"
