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
"""Tests for Databricks shared settings validation."""

import pytest
from pydantic import ValidationError

from zenml.integrations.databricks.flavors.databricks_orchestrator_flavor import (
    DatabricksOrchestratorSettings,
)
from zenml.integrations.databricks.flavors.databricks_shared_settings import (
    DatabricksAccessControlRequest,
    DatabricksBaseSettings,
)
from zenml.integrations.databricks.step_operators.databricks_step_operator import (
    DATABRICKS_STEP_OPERATOR_IGNORED_SETTINGS,
)
from zenml.utils.secret_utils import is_secret_field

InvalidNumericSettingsKwargs = dict[str, int | tuple[int, int]]


def test_databricks_flavor_modules_import() -> None:
    """Tests that Databricks flavor modules import safely."""
    from zenml.integrations.databricks.flavors import (  # noqa: PLC0415
        databricks_orchestrator_flavor,
        databricks_step_operator_flavor,
    )

    assert databricks_orchestrator_flavor.DatabricksOrchestratorSettings
    assert databricks_step_operator_flavor.DatabricksStepOperatorSettings


def test_databricks_step_operator_ignored_settings_are_shared() -> None:
    """Tests the shared one-time-run ignored settings contract."""
    assert DATABRICKS_STEP_OPERATOR_IGNORED_SETTINGS == (
        "schedule_timezone",
        "job_tags",
        "max_concurrent_runs",
        "max_retries",
        "min_retry_interval_millis",
        "retry_on_timeout",
    )
    assert (
        "access_control_list" not in DATABRICKS_STEP_OPERATOR_IGNORED_SETTINGS
    )
    assert "timeout_seconds" not in DATABRICKS_STEP_OPERATOR_IGNORED_SETTINGS
    assert (
        "task_timeout_seconds" not in DATABRICKS_STEP_OPERATOR_IGNORED_SETTINGS
    )


def test_databricks_settings_allow_valid_values() -> None:
    """Tests that valid Databricks shared settings are accepted."""
    settings = DatabricksBaseSettings(
        autoscale=(0, 1),
        docker_image_username="username",
        docker_image_password="password",
        init_scripts=["dbfs:/scripts/install_dependencies.sh"],
        schedule_timezone="UTC",
    )

    assert settings.autoscale == (0, 1)
    assert settings.schedule_timezone == "UTC"
    assert is_secret_field(
        DatabricksBaseSettings.model_fields["docker_image_password"]
    )


def test_databricks_settings_model_validate_serialized_values() -> None:
    """Tests shared settings survive model serialization and validation."""
    settings = DatabricksBaseSettings(
        access_control_list=[
            DatabricksAccessControlRequest(
                service_principal_name="service-principal-id",
                permission_level="CAN_MANAGE_RUN",
            )
        ],
        availability_type="SPOT",
        docker_image_username="username",
        docker_image_password="password",
        init_scripts=["dbfs:/scripts/install_dependencies.sh"],
        schedule_timezone="UTC",
    )

    serialized_settings = settings.model_dump(mode="json")
    validated_settings = DatabricksBaseSettings.model_validate(
        serialized_settings
    )

    assert validated_settings == settings
    assert validated_settings.access_control_list
    assert (
        validated_settings.access_control_list[0].service_principal_name
        == "service-principal-id"
    )


def test_databricks_orchestrator_settings_round_trip_serialized_values() -> (
    None
):
    """Tests serialized orchestrator settings validate with the shared base."""
    settings = DatabricksOrchestratorSettings(
        access_control_list=[
            DatabricksAccessControlRequest(
                user_name="user@example.com",
                permission_level="CAN_MANAGE_RUN",
            )
        ],
        availability_type="SPOT_WITH_FALLBACK",
        custom_tags={"cost_center": "ml-team"},
        docker_image_url="registry.example.com/ml:latest",
        docker_image_username="username",
        docker_image_password="password",
        init_scripts=["dbfs:/scripts/install_dependencies.sh"],
        job_tags={"project": "recommendation-engine"},
        max_concurrent_runs=3,
        max_retries=2,
        min_retry_interval_millis=60000,
        schedule_timezone="UTC",
        task_timeout_seconds=3600,
        timeout_seconds=7200,
    )

    serialized_settings = settings.model_dump(mode="json")
    validated_settings = DatabricksOrchestratorSettings.model_validate(
        serialized_settings
    )

    assert validated_settings == settings


@pytest.mark.parametrize(
    "kwargs",
    [
        {"num_workers": -1},
        {"autotermination_minutes": -1},
        {"timeout_seconds": -1},
        {"max_concurrent_runs": 0},
        {"task_timeout_seconds": -1},
        {"max_retries": -2},
        {"min_retry_interval_millis": -1},
        {"autoscale": (-1, 1)},
        {"autoscale": (2, 1)},
    ],
)
def test_databricks_settings_reject_invalid_numeric_values(
    kwargs: InvalidNumericSettingsKwargs,
) -> None:
    """Tests that invalid Databricks numeric settings are rejected."""
    with pytest.raises(ValidationError):
        DatabricksBaseSettings(**kwargs)


def test_databricks_settings_reject_partial_docker_credentials() -> None:
    """Tests that Docker image credentials must be configured together."""
    with pytest.raises(ValidationError):
        DatabricksBaseSettings(docker_image_username="username")

    with pytest.raises(ValidationError):
        DatabricksBaseSettings(docker_image_password="password")


def test_databricks_settings_reject_non_dbfs_init_scripts() -> None:
    """Tests that Databricks init scripts must use DBFS paths."""
    with pytest.raises(ValidationError):
        DatabricksBaseSettings(init_scripts=["s3://bucket/script.sh"])


def test_databricks_settings_reject_invalid_schedule_timezone() -> None:
    """Tests that Databricks schedule timezone must be an IANA timezone."""
    with pytest.raises(ValidationError):
        DatabricksBaseSettings(schedule_timezone="PST")


def test_databricks_access_control_requires_exactly_one_principal() -> None:
    """Tests Databricks access control principal validation."""
    valid_acl = DatabricksAccessControlRequest(
        group_name="users",
        permission_level="CAN_VIEW",
    )

    assert valid_acl.group_name == "users"

    with pytest.raises(ValidationError):
        DatabricksAccessControlRequest(permission_level="CAN_VIEW")

    with pytest.raises(ValidationError):
        DatabricksAccessControlRequest(
            group_name="users",
            user_name="user@example.com",
            permission_level="CAN_VIEW",
        )
