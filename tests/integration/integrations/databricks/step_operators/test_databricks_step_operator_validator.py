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
"""Validator tests for the Databricks step operator."""

import importlib.util
from contextlib import ExitStack as does_not_raise
from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.stack import Stack

DATABRICKS_INSTALLED = importlib.util.find_spec("databricks") is not None
pytestmark = pytest.mark.skipif(
    not DATABRICKS_INSTALLED, reason="databricks dependency is not installed."
)

if DATABRICKS_INSTALLED:
    from zenml.integrations.databricks.flavors.databricks_step_operator_flavor import (
        DatabricksStepOperatorConfig,
    )
    from zenml.integrations.databricks.step_operators import (
        DatabricksStepOperator,
    )
else:
    DatabricksStepOperatorConfig = Any
    DatabricksStepOperator = Any


def _get_databricks_step_operator() -> DatabricksStepOperator:
    """Helper function to get a Databricks step operator."""
    return DatabricksStepOperator(
        name="databricks",
        id=uuid4(),
        config=DatabricksStepOperatorConfig(
            host="https://workspace.cloud.databricks.com",
            client_id="client-id",
            client_secret="client-secret",
        ),
        flavor="databricks",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_databricks_step_operator_stack_validation(
    local_orchestrator: Any,
    local_artifact_store: Any,
    s3_artifact_store: Any,
) -> None:
    """Tests Databricks step operator stack validation."""
    step_operator = _get_databricks_step_operator()

    with does_not_raise():
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=s3_artifact_store,
            step_operator=step_operator,
        ).validate()

    with pytest.raises(StackValidationError):
        Stack(
            id=uuid4(),
            name="",
            orchestrator=local_orchestrator,
            artifact_store=local_artifact_store,
            step_operator=step_operator,
        ).validate()
