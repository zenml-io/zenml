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

from typing import TYPE_CHECKING, Type

from zenml.data_validators.base_data_validator import (
    BaseDataValidatorConfig,
    BaseDataValidatorFlavor,
)
from zenml.integrations.whylogs import WHYLOGS_DATA_VALIDATOR_FLAVOR
from zenml.stack.authentication_mixin import AuthenticationConfigMixin

if TYPE_CHECKING:
    from zenml.integrations.whylogs.data_validators import WhylogsDataValidator


class WhylogsDataValidatorConfig(
    BaseDataValidatorConfig, AuthenticationConfigMixin
):
    """Config for the whylogs data validator."""


class WhylogsDataValidatorFlavor(BaseDataValidatorFlavor):
    """Whylogs data validator flavor."""

    @property
    def name(self) -> str:
        return WHYLOGS_DATA_VALIDATOR_FLAVOR

    @property
    def config_class(self) -> Type[WhylogsDataValidatorConfig]:
        return WhylogsDataValidatorConfig

    @property
    def implementation_class(self) -> Type["WhylogsDataValidator"]:
        from zenml.integrations.whylogs.data_validators import (
            WhylogsDataValidator,
        )

        return WhylogsDataValidator
