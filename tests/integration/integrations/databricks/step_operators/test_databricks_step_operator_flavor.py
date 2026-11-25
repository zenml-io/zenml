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
"""Tests for the Databricks step operator flavor config."""

from __future__ import annotations

import importlib.util

import pytest

DATABRICKS_INSTALLED = importlib.util.find_spec("databricks") is not None
pytestmark = pytest.mark.skipif(
    not DATABRICKS_INSTALLED, reason="databricks dependency is not installed."
)

if DATABRICKS_INSTALLED:
    from zenml.integrations.databricks.flavors.databricks_step_operator_flavor import (
        DatabricksStepOperatorConfig,
    )


def test_databricks_step_operator_config_uses_shared_settings() -> None:
    """Tests that Databricks step operator config exposes shared settings."""
    config = DatabricksStepOperatorConfig(
        host="https://workspace.cloud.databricks.com",
        client_id="client-id",
        client_secret="client-secret",
        spark_version="16.4.x-scala2.12",
        num_workers=2,
    )

    assert config.spark_version == "16.4.x-scala2.12"
    assert config.num_workers == 2
    assert config.is_remote is True
    assert config.is_local is False
