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

from typing import Optional

from pydantic import BaseModel, Field


class ExceptionInfo(BaseModel):
    """Exception information."""

    traceback: str = Field(
        title="The traceback of the exception.",
    )
    step_code_line: Optional[int] = Field(
        default=None,
        title="The line number of the step code that raised the exception.",
    )
