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

from typing import TYPE_CHECKING, Dict, Optional, Type
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, field_validator, model_validator

from zenml.integrations.databricks import DATABRICKS_ORCHESTRATOR_FLAVOR
from zenml.integrations.databricks.flavors.databricks_shared_settings import (
    DatabricksAvailabilityType,  # noqa: F401  (re-export for back-compat)
    DatabricksBaseSettings,
)
from zenml.orchestrators.base_orchestrator import (
    BaseOrchestratorConfig,
    BaseOrchestratorFlavor,
)
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.databricks.orchestrators import (
        DatabricksOrchestrator,
    )


class DatabricksOrchestratorSettings(DatabricksBaseSettings):
    """Databricks orchestrator settings."""

    schedule_timezone: Optional[str] = Field(
        default=None,
        description="IANA timezone for scheduled pipeline execution. Used "
        "only when a schedule with a cron expression is configured. "
        "Example: 'America/New_York'.",
    )
    job_tags: Optional[Dict[str, str]] = Field(
        default=None,
        description="Tags associated with the Databricks job, forwarded to "
        "the cluster as cluster tags. Maximum 25 tags. "
        "Example: {'project': 'recommendation-engine', 'owner': 'data-team'}",
    )
    max_concurrent_runs: Optional[int] = Field(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of concurrent runs for this job. "
        "Databricks defaults to 1 if not specified. Maximum is 1000",
    )
    max_retries: Optional[int] = Field(
        default=None,
        ge=-1,
        description="Maximum number of times to retry a failed task. "
        "Use -1 for unlimited retries.",
    )
    min_retry_interval_millis: Optional[int] = Field(
        default=None,
        ge=0,
        description="Minimum interval in milliseconds between retry attempts. "
        "Example: 60000 for 1 minute between retries",
    )
    retry_on_timeout: Optional[bool] = Field(
        default=None,
        description="Whether to retry a task when it times out. Requires "
        "max_retries to be set.",
    )

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
    client_id: Optional[str] = SecretField(default=None)
    client_secret: Optional[str] = SecretField(default=None)

    @model_validator(mode="after")
    def _validate_service_principal_credentials(
        self,
    ) -> "DatabricksOrchestratorConfig":
        """Validates Databricks service principal credentials.

        Returns:
            The validated config.

        Raises:
            ValueError: If only one of `client_id` / `client_secret` is set.
        """
        if bool(self.client_id) != bool(self.client_secret):
            raise ValueError(
                "Databricks service principal authentication requires both "
                "`client_id` and `client_secret` to be configured, or neither."
            )

        return self

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
        """Returns DatabricksOrchestratorConfig config class.

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
