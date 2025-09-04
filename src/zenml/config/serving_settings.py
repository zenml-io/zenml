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
"""Serving settings for ZenML pipeline serving."""

from typing import Any, Dict, Optional

from pydantic import Field

from zenml.config.base_settings import BaseSettings


class ServingSettings(BaseSettings):
    """Settings for pipeline serving configuration.

    These settings control serving-specific behavior like capture policies
    for step-level data tracking and artifact persistence.
    """

    capture: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Step-level capture configuration for fine-grained data tracking control. "
        "Supports 'inputs' and 'outputs' mappings with per-parameter capture settings including "
        "mode, artifacts, sample_rate, max_bytes, and redact fields",
    )
