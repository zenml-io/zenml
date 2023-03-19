#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""WhyLabs whylogs data validator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.config.base_settings import BaseSettings
from zenml.data_validators.base_data_validator import (
    BaseDataValidatorConfig,
    BaseDataValidatorFlavor,
)
from zenml.integrations.whylogs import WHYLOGS_DATA_VALIDATOR_FLAVOR
from zenml.stack.authentication_mixin import AuthenticationConfigMixin

if TYPE_CHECKING:
    from zenml.integrations.whylogs.data_validators import WhylogsDataValidator


class WhylogsDataValidatorSettings(BaseSettings):
    """Settings for the Whylogs data validator.

    Attributes:
        enable_whylabs: If set to `True` for a step, all the whylogs data
            profile views returned by the step will automatically be uploaded
            to the Whylabs platform if Whylabs credentials are configured.
        dataset_id: Dataset ID to use when uploading profiles to Whylabs.
    """

    enable_whylabs: bool = False
    dataset_id: Optional[str] = None


class WhylogsDataValidatorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseDataValidatorConfig,
    AuthenticationConfigMixin,
    WhylogsDataValidatorSettings,
):
    """Config for the whylogs data validator."""


class WhylogsDataValidatorFlavor(BaseDataValidatorFlavor):
    """Whylogs data validator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return WHYLOGS_DATA_VALIDATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/data_validator/whylogs.png"

    @property
    def config_class(self) -> Type[WhylogsDataValidatorConfig]:
        """Returns `WhylogsDataValidatorConfig` config class.

        Returns:
                The config class.
        """
        return WhylogsDataValidatorConfig

    @property
    def implementation_class(self) -> Type["WhylogsDataValidator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.whylogs.data_validators import (
            WhylogsDataValidator,
        )

        return WhylogsDataValidator
