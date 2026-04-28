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
"""Shared Databricks settings models."""

from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator, model_validator

from zenml.config.base_settings import BaseSettings
from zenml.utils.enum_utils import StrEnum
from zenml.utils.secret_utils import SecretField

DATABRICKS_DEFAULT_AUTOSCALE = (0, 1)
DATABRICKS_STEP_OPERATOR_IGNORED_SETTINGS: Tuple[str, ...] = (
    "schedule_timezone",
    "job_tags",
    "max_concurrent_runs",
    "max_retries",
    "min_retry_interval_millis",
    "retry_on_timeout",
)


class DatabricksAvailabilityType(StrEnum):
    """Databricks availability type."""

    ON_DEMAND = "ON_DEMAND"
    SPOT = "SPOT"
    SPOT_WITH_FALLBACK = "SPOT_WITH_FALLBACK"


class DatabricksPermissionLevel(StrEnum):
    """Databricks job permission levels."""

    CAN_VIEW = "CAN_VIEW"
    CAN_MANAGE_RUN = "CAN_MANAGE_RUN"
    CAN_MANAGE = "CAN_MANAGE"
    IS_OWNER = "IS_OWNER"


class DatabricksAccessControlRequest(BaseModel):
    """Databricks job access control entry."""

    group_name: Optional[str] = Field(
        default=None,
        description="Databricks group name to grant permissions to. "
        "Example: 'data-science-team'",
    )
    user_name: Optional[str] = Field(
        default=None,
        description="Databricks user email to grant permissions to. "
        "Example: 'user@company.com'",
    )
    service_principal_name: Optional[str] = Field(
        default=None,
        description="Application ID of a Databricks service principal "
        "to grant permissions to",
    )
    permission_level: DatabricksPermissionLevel = Field(
        description="Permission level to grant. Valid values for jobs: "
        "CAN_VIEW, CAN_MANAGE_RUN, CAN_MANAGE, IS_OWNER",
    )

    @model_validator(mode="after")
    def _validate_single_principal(
        self,
    ) -> "DatabricksAccessControlRequest":
        """Ensures that exactly one Databricks principal is configured.

        Returns:
            The validated access control request.

        Raises:
            ValueError: If none or multiple Databricks principals are set.
        """
        principals = [
            self.group_name,
            self.user_name,
            self.service_principal_name,
        ]
        if sum(bool(principal) for principal in principals) != 1:
            raise ValueError(
                "Exactly one of `group_name`, `user_name`, or "
                "`service_principal_name` must be specified for a "
                "Databricks access control request."
            )

        return self


class DatabricksBaseSettings(BaseSettings):
    """Databricks execution settings shared by orchestrator and step operator."""

    spark_version: Optional[str] = Field(
        default=None,
        description="Apache Spark version for the Databricks cluster. "
        "Uses workspace default if not specified. Example: '16.4.x-scala2.12'",
    )
    num_workers: Optional[int] = Field(
        default=None,
        ge=0,
        description="Fixed number of worker nodes. Cannot be used with autoscaling.",
    )
    node_type_id: Optional[str] = Field(
        default=None,
        description="Databricks node type identifier. "
        "Refer to Databricks documentation for available instance types. "
        "Example: 'i3.xlarge'",
    )
    policy_id: Optional[str] = Field(
        default=None,
        description="Databricks cluster policy ID for governance and cost control.",
    )
    autotermination_minutes: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minutes of inactivity before automatic cluster termination. "
        "Helps control costs by shutting down idle clusters.",
    )
    autoscale: Tuple[int, int] = Field(
        default=DATABRICKS_DEFAULT_AUTOSCALE,
        description="Cluster autoscaling bounds as (min_workers, max_workers). "
        "The default (0, 1) intentionally permits driver-only Databricks "
        "clusters while still allowing one worker when needed.",
    )
    single_user_name: Optional[str] = Field(
        default=None,
        description="Databricks username for single-user cluster access mode.",
    )
    spark_conf: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom Spark configuration properties as key-value pairs. "
        "Example: {'spark.sql.adaptive.enabled': 'true', "
        "'spark.sql.adaptive.coalescePartitions.enabled': 'true'}",
    )
    spark_env_vars: Optional[Dict[str, str]] = Field(
        default=None,
        description="Environment variables for the Spark driver and executors. "
        "Example: {'SPARK_WORKER_MEMORY': '4g', 'SPARK_DRIVER_MEMORY': '2g'}",
    )
    schedule_timezone: Optional[str] = Field(
        default=None,
        description="IANA timezone for scheduled pipeline execution. "
        "Used only by the Databricks orchestrator when a schedule is configured. "
        "Example: 'America/New_York'.",
    )
    availability_type: Optional[DatabricksAvailabilityType] = Field(
        default=None,
        description="Instance availability type: ON_DEMAND (guaranteed), SPOT "
        "(cost-optimized), or SPOT_WITH_FALLBACK (spot with on-demand backup).",
    )
    custom_tags: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom tags applied to Databricks cluster resources (e.g., AWS "
        "instances, EBS volumes). Useful for cost allocation and governance. "
        "Maximum 45 tags. "
        "Example: {'cost_center': 'ml-team', 'environment': 'production'}",
    )
    job_tags: Optional[Dict[str, str]] = Field(
        default=None,
        description="Tags associated with the Databricks job, forwarded to the "
        "cluster as cluster tags. Used only by the Databricks orchestrator. "
        "Maximum 25 tags. "
        "Example: {'project': 'recommendation-engine', 'owner': 'data-team'}",
    )
    access_control_list: Optional[List[DatabricksAccessControlRequest]] = (
        Field(
            default=None,
            description="Access control list for the Databricks job. Grants "
            "permissions to users, groups, or service principals. By default, "
            "only the job creator can access the job. "
            "Example: [{'group_name': 'users', 'permission_level': 'CAN_VIEW'}]",
        )
    )
    timeout_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Timeout in seconds applied to each run of the job. "
        "Value of 0 means no timeout. Example: 3600 for a 1-hour timeout",
    )
    max_concurrent_runs: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of concurrent runs for this job. "
        "Used only by the Databricks orchestrator. Databricks defaults to 1 "
        "if not specified. Maximum is 1000",
    )
    task_timeout_seconds: Optional[int] = Field(
        default=None,
        ge=0,
        description="Timeout in seconds for each task (step) in the job. "
        "Value of 0 means no timeout",
    )
    max_retries: Optional[int] = Field(
        default=None,
        ge=-1,
        description="Maximum number of times to retry a failed task. "
        "Use -1 for unlimited retries. Used only by the Databricks orchestrator.",
    )
    min_retry_interval_millis: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum interval in milliseconds between retry attempts. "
        "Used only by the Databricks orchestrator. Example: 60000 for "
        "1 minute between retries",
    )
    retry_on_timeout: Optional[bool] = Field(
        default=None,
        description="Whether to retry a task when it times out. Requires "
        "max_retries to be set. Used only by the Databricks orchestrator.",
    )
    driver_node_type_id: Optional[str] = Field(
        default=None,
        description="Databricks node type for the Spark driver. Defaults to "
        "the same type as worker nodes if not specified. "
        "Example: 'i3.xlarge'",
    )
    init_scripts: Optional[List[str]] = Field(
        default=None,
        description="DBFS paths to init scripts for cluster setup. Only "
        "`dbfs:/` paths are supported. Example: "
        "['dbfs:/scripts/install_dependencies.sh']",
    )
    docker_image_url: Optional[str] = Field(
        default=None,
        description="Docker image URL for the cluster. Must be accessible "
        "from the Databricks workspace. "
        "Example: 'my-registry.com/my-image:latest'",
    )
    docker_image_username: Optional[str] = Field(
        default=None,
        description="Username for authenticating to the Docker registry. "
        "Must be provided together with `docker_image_password`.",
    )
    docker_image_password: Optional[str] = SecretField(
        default=None,
        description="Password for authenticating to the Docker registry. "
        "Must be provided together with `docker_image_username`.",
    )

    @field_validator("autoscale")
    @classmethod
    def _validate_autoscale_bounds(
        cls, value: Tuple[int, int]
    ) -> Tuple[int, int]:
        """Validates Databricks autoscale worker bounds.

        Args:
            value: The autoscale worker bounds.

        Returns:
            The validated autoscale worker bounds.

        Raises:
            ValueError: If the autoscale worker bounds are invalid.
        """
        min_workers, max_workers = value
        if min_workers < 0 or max_workers < 0:
            raise ValueError(
                "Databricks autoscale worker counts must be greater than "
                "or equal to 0."
            )
        if min_workers > max_workers:
            raise ValueError(
                "Databricks autoscale `min_workers` must be less than or "
                "equal to `max_workers`."
            )

        return value

    @field_validator("init_scripts")
    @classmethod
    def _validate_init_script_paths(
        cls, value: Optional[List[str]]
    ) -> Optional[List[str]]:
        """Validates that init scripts use DBFS paths.

        Args:
            value: The init script paths.

        Returns:
            The validated init script paths.

        Raises:
            ValueError: If any init script path is not a DBFS path.
        """
        if value is None:
            return None

        invalid_paths = [
            path for path in value if not path.startswith("dbfs:/")
        ]
        if invalid_paths:
            raise ValueError(
                "Databricks init scripts must use DBFS paths starting with "
                f"`dbfs:/`. Invalid paths: {invalid_paths}."
            )

        return value

    @field_validator("schedule_timezone")
    @classmethod
    def _validate_schedule_timezone(
        cls, value: Optional[str]
    ) -> Optional[str]:
        """Validates the schedule timezone.

        Args:
            value: The schedule timezone.

        Returns:
            The validated schedule timezone.

        Raises:
            ValueError: If the timezone is not a valid IANA timezone.
        """
        if value is None:
            return None

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as e:
            raise ValueError(
                "Databricks `schedule_timezone` must be a valid IANA "
                "timezone, e.g. 'America/New_York' or 'UTC'."
            ) from e

        return value

    @model_validator(mode="after")
    def _validate_docker_image_credentials(self) -> "DatabricksBaseSettings":
        """Validates Docker image registry credentials.

        Returns:
            The validated settings.

        Raises:
            ValueError: If only one Docker registry credential is configured.
        """
        has_username = bool(self.docker_image_username)
        has_password = bool(self.docker_image_password)
        if has_username != has_password:
            raise ValueError(
                "Databricks Docker image authentication requires both "
                "`docker_image_username` and `docker_image_password` to be "
                "configured."
            )

        return self
