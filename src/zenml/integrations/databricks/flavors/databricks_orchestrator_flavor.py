#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Databricks orchestrator base config and settings."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.databricks import DATABRICKS_ORCHESTRATOR_FLAVOR
from zenml.integrations.databricks.flavors.databricks_shared_settings import (
    DatabricksBaseSettings,
)
from zenml.orchestrators import BaseOrchestratorConfig
from zenml.orchestrators.base_orchestrator import BaseOrchestratorFlavor
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.databricks.orchestrators import (
        DatabricksOrchestrator,
    )

logger = get_logger(__name__)


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
    """Databricks job access control entry.

    Exactly one of group_name, user_name, or service_principal_name
    must be specified.
    """

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


class DatabricksOrchestratorSettings(BaseSettings):
    """Databricks orchestrator base settings.

    Configuration for Databricks cluster and Spark execution settings.
    Field descriptions are defined inline using Field() descriptors.
    """

    # Cluster Configuration
    spark_version: Optional[str] = Field(
        default=None,
        description="Apache Spark version for the Databricks cluster. "
        "Uses workspace default if not specified. Example: '16.4.x-scala2.12'",
    )
    num_workers: Optional[int] = Field(
        default=None,
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
        description="Minutes of inactivity before automatic cluster termination. "
        "Helps control costs by shutting down idle clusters.",
    )
    autoscale: Tuple[int, int] = Field(
        default=(0, 1),
        description="Cluster autoscaling bounds as (min_workers, max_workers). "
        "Automatically adjusts cluster size based on workload.",
    )
    single_user_name: Optional[str] = Field(
        default=None,
        description="Databricks username for single-user cluster access mode.",
    )
    spark_conf: Optional[Dict[str, str]] = Field(
        default=None,
        description="Custom Spark configuration properties as key-value pairs. "
        "Example: {'spark.sql.adaptive.enabled': 'true', 'spark.sql.adaptive.coalescePartitions.enabled': 'true'}",
    )
    spark_env_vars: Optional[Dict[str, str]] = Field(
        default=None,
        description="Environment variables for the Spark driver and executors. "
        "Example: {'SPARK_WORKER_MEMORY': '4g', 'SPARK_DRIVER_MEMORY': '2g'}",
    )
    schedule_timezone: Optional[str] = Field(
        default=None,
        description="Timezone for scheduled pipeline execution. "
        "Uses IANA timezone format (e.g., 'America/New_York').",
    )
    availability_type: Optional[DatabricksAvailabilityType] = Field(
        default=None,
        description="Instance availability type: ON_DEMAND (guaranteed), SPOT (cost-optimized), "
        "or SPOT_WITH_FALLBACK (spot with on-demand backup).",
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
        "cluster as cluster tags. Maximum 25 tags. "
        "Example: {'project': 'recommendation-engine', 'owner': 'data-team'}",
    )
    access_control_list: Optional[List[DatabricksAccessControlRequest]] = (
        Field(
            default=None,
            description="Access control list for the Databricks job. Grants "
            "permissions to users, groups, or service principals. By default, "
            "only the job creator (service principal) can access the job. "
            "Example: [{'group_name': 'users', 'permission_level': 'CAN_VIEW'}]",
        )
    )

    # Job-level execution control
    timeout_seconds: Optional[int] = Field(
        default=None,
        description="Timeout in seconds applied to each run of the job. "
        "Value of 0 means no timeout. Example: 3600 for a 1-hour timeout",
    )
    max_concurrent_runs: Optional[int] = Field(
        default=None,
        description="Maximum number of concurrent runs for this job. "
        "Databricks defaults to 1 if not specified. Maximum is 1000",
    )

    # Task-level retry and timeout
    task_timeout_seconds: Optional[int] = Field(
        default=None,
        description="Timeout in seconds for each task (step) in the job. "
        "Value of 0 means no timeout",
    )
    max_retries: Optional[int] = Field(
        default=None,
        description="Maximum number of times to retry a failed task. "
        "Use -1 for unlimited retries",
    )
    min_retry_interval_millis: Optional[int] = Field(
        default=None,
        description="Minimum interval in milliseconds between retry attempts. "
        "Example: 60000 for 1 minute between retries",
    )
    retry_on_timeout: Optional[bool] = Field(
        default=None,
        description="Whether to retry a task when it times out. "
        "Requires max_retries to be set",
    )

class DatabricksOrchestratorSettings(DatabricksBaseSettings):
    """Databricks orchestrator settings."""


class DatabricksOrchestratorConfig(
    BaseOrchestratorConfig, DatabricksOrchestratorSettings
):
    """Databricks orchestrator base config.

    Attributes:
        host: Databricks host.
        client_id: Databricks client id.
        client_secret: Databricks client secret.
    """

    host: str
    client_id: str = SecretField(default=None)
    client_secret: str = SecretField(default=None)

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            True if this config is for a local component, False otherwise.
        """
        return False

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return True

    @property
    def is_schedulable(self) -> bool:
        """Whether the orchestrator is schedulable or not.

        Returns:
            Whether the orchestrator is schedulable or not.
        """
        return True


class DatabricksOrchestratorFlavor(BaseOrchestratorFlavor):
    """Databricks orchestrator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return DATABRICKS_ORCHESTRATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/databricks.png"

    @property
    def config_class(self) -> Type[DatabricksOrchestratorConfig]:
        """Returns `KubeflowOrchestratorConfig` config class.

        Returns:
                The config class.
        """
        return DatabricksOrchestratorConfig

    @property
    def implementation_class(self) -> Type["DatabricksOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.databricks.orchestrators import (
            DatabricksOrchestrator,
        )

        return DatabricksOrchestrator
