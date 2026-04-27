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
"""Databricks step operator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.databricks import DATABRICKS_STEP_OPERATOR_FLAVOR
from zenml.integrations.databricks.flavors.databricks_shared_settings import (
    DatabricksBaseSettings,
)
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.databricks.step_operators import (
        DatabricksStepOperator,
    )


class DatabricksStepOperatorSettings(DatabricksBaseSettings):
    """Databricks step operator settings."""


class DatabricksStepOperatorConfig(
    BaseStepOperatorConfig, DatabricksStepOperatorSettings
):
    """Databricks step operator config."""

    host: str
    client_id: Optional[str] = SecretField(default=None)
    client_secret: Optional[str] = SecretField(default=None)

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            False, because the Databricks step operator always runs remotely.
        """
        return False

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        Returns:
            True, because the Databricks step operator always runs remotely.
        """
        return True


class DatabricksStepOperatorFlavor(BaseStepOperatorFlavor):
    """Databricks step operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return DATABRICKS_STEP_OPERATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs URL.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs URL.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/databricks.png"

    @property
    def config_class(self) -> Type[DatabricksStepOperatorConfig]:
        """Returns DatabricksStepOperatorConfig config class.

        Returns:
            The config class.
        """
        return DatabricksStepOperatorConfig

    @property
    def implementation_class(self) -> Type["DatabricksStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.databricks.step_operators import (
            DatabricksStepOperator,
        )

        return DatabricksStepOperator
