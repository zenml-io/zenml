#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Module for warning configurations organization and resolution."""

from zenml.utils.enum_utils import StrEnum
from zenml.utils.warnings.base import (
    WarningCategory,
    WarningConfig,
    WarningSeverity,
    WarningVerbosity,
)


class WarningCodes(StrEnum):
    """Enum class organizing the warning codes."""

    ZML001 = "ZML001"
    ZML002 = "ZML002"


WARNING_CONFIG_REGISTRY = {
    WarningCodes.ZML001.value: WarningConfig(
        code=WarningCodes.ZML001.value,
        category=WarningCategory.USAGE,
        description="""
        ## Ignored settings warning
        
        The user has provided a settings object without a valid key.
        """,
        verbosity=WarningVerbosity.LOW,
        severity=WarningSeverity.MEDIUM,
        is_throttled=False,
    ),
    WarningCodes.ZML002.value: WarningConfig(
        code=WarningCodes.ZML002.value,
        category=WarningCategory.USAGE,
        description="""
        ## Unused docker settings warning
        
        The user provides a valid docker settings object but the stack
        does not have any components that make use of it.
        """,
        verbosity=WarningVerbosity.LOW,
        severity=WarningSeverity.MEDIUM,
        is_throttled=True,
    ),
}
