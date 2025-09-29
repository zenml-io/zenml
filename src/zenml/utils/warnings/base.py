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
"""Warning configuration class and helper enums."""

from pydantic import BaseModel, Field

from zenml.utils.enum_utils import StrEnum


class WarningSeverity(StrEnum):
    """Enum class describing the warning severity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WarningCategory(StrEnum):
    """Enum class describing the warning category."""

    USAGE = "USAGE"


class WarningVerbosity(StrEnum):
    """Enum class describing the warning verbosity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class WarningConfig(BaseModel, use_enum_values=True):
    """Warning config class describing how warning messages should be displayed."""

    description: str = Field(description="Description of the warning message")
    severity: WarningSeverity = WarningSeverity.MEDIUM
    category: WarningCategory
    code: str
    is_throttled: bool = Field(
        description="If the warning is throttled. Throttled warnings should be displayed once per session.",
        default=False,
    )
    verbosity: WarningVerbosity = Field(
        description="Verbosity of the warning. Low verbosity displays basic details (code & message). Medium displays also call details like module & line number. High displays description and additional info.",
        default=WarningVerbosity.MEDIUM,
    )
