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
"""Unit tests for the Run:AI step operator flavor config."""

import importlib.util
from typing import Any

import pytest
from pydantic import ValidationError

RUNAI_INSTALLED = importlib.util.find_spec("runai") is not None
pytestmark = pytest.mark.skipif(
    not RUNAI_INSTALLED, reason="runai dependency is not installed."
)

if RUNAI_INSTALLED:
    from zenml.integrations.runai.flavors.runai_step_operator_flavor import (
        RunAIStepOperatorConfig,
    )
else:
    RunAIStepOperatorConfig = Any


def _build_config(runai_base_url: str) -> RunAIStepOperatorConfig:
    """Build a minimal valid Run:AI step operator config."""
    return RunAIStepOperatorConfig(
        client_id="client-id",
        client_secret="client-secret",
        runai_base_url=runai_base_url,
        project_name="demo-project",
    )


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://my-org.run.ai", "https://my-org.run.ai"),
        ("https://my-org.run.ai/", "https://my-org.run.ai"),
        (
            "http://runai.local:8443/control-plane/",
            "http://runai.local:8443/control-plane",
        ),
    ],
)
def test_runai_base_url_accepts_valid_urls(url: str, expected: str) -> None:
    """Tests validation and normalization of valid Run:AI base URLs."""
    config = _build_config(url)
    assert config.runai_base_url == expected


@pytest.mark.parametrize(
    "url,error_match",
    [
        ("my-org.run.ai", "Must start with http:// or https://"),
        ("ftp://my-org.run.ai", "Must start with http:// or https://"),
        ("https://", "must include a hostname"),
        ("http://", "must include a hostname"),
        (
            "https://my-org.run.ai/control-plane?foo=bar",
            "Query parameters and fragments are not supported",
        ),
        (
            "https://my-org.run.ai/control-plane#section",
            "Query parameters and fragments are not supported",
        ),
    ],
)
def test_runai_base_url_rejects_invalid_urls(
    url: str, error_match: str
) -> None:
    """Tests validation errors for invalid Run:AI base URLs."""
    with pytest.raises(ValidationError, match=error_match):
        _build_config(url)
