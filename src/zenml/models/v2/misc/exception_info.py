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
"""Exception information models."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zenml.utils.pydantic_utils import before_validator_handler


class ExceptionInfo(BaseModel):
    """Exception information."""

    traceback: str = Field(
        title="The traceback of the exception.",
    )
    user_code_line: Optional[int] = Field(
        default=None,
        title="The line number of the user code that raised the exception.",
    )

    # Keep the old attribute for dashboard backwards compatibility
    model_config = ConfigDict(extra="allow")

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _migrate_attributes(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Pydantic validator function for migrating attributes.

        Args:
            data: The data to migrate.

        Returns:
            The migrated data.
        """
        if step_code_line := data.get("step_code_line", None):
            data.setdefault("user_code_line", step_code_line)

        return data
