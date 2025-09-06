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
"""Capture policy scaffolding and presets.

This is a lightweight placeholder to enable runtime selection without changing
public pipeline APIs. The capture mode can be controlled via the environment
variable `ZENML_CAPTURE_MODE` with values: `BATCH` (default), `REALTIME`,
`OFF`, or `CUSTOM`.
"""

import os
from enum import Enum
from typing import Any, Dict, Optional, Union


class CaptureMode(str, Enum):
    """Capture mode enum."""

    BATCH = "BATCH"
    REALTIME = "REALTIME"
    OFF = "OFF"
    CUSTOM = "CUSTOM"


class CapturePolicy:
    """Minimal capture policy container with optional options."""

    def __init__(
        self,
        mode: CaptureMode = CaptureMode.BATCH,
        options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize the capture policy.

        Args:
            mode: The capture mode.
            options: The capture options.
        """
        self.mode = mode
        self.options = options or {}

    @staticmethod
    def from_env() -> "CapturePolicy":
        """Create a capture policy from the environment.

        Returns:
            The capture policy.
        """
        val = os.getenv("ZENML_CAPTURE_MODE", "BATCH").upper()
        try:
            mode = CaptureMode(val)
        except ValueError:
            mode = CaptureMode.BATCH
        # No options provided from env here; runtimes may read env as fallback
        return CapturePolicy(mode=mode, options={})

    @staticmethod
    def from_value(
        value: Optional[Union[str, Dict[str, Any]]],
    ) -> "CapturePolicy":
        """Create a capture policy from a value.

        Args:
            value: The value to create the capture policy from.

        Returns:
            The capture policy.
        """
        if value is None:
            return CapturePolicy.from_env()
        if isinstance(value, dict):
            mode = str(value.get("mode", "BATCH")).upper()
            try:
                cm = CaptureMode(mode)
            except Exception:
                cm = CaptureMode.BATCH
            # store other keys as options
            options = {k: v for k, v in value.items() if k != "mode"}
            return CapturePolicy(mode=cm, options=options)
        else:
            try:
                return CapturePolicy(mode=CaptureMode(str(value).upper()))
            except Exception:
                return CapturePolicy.from_env()

    def get_option(self, key: str, default: Any = None) -> Any:
        """Get an option from the capture policy.

        Args:
            key: The key of the option to get.
            default: The default value to return if the option is not found.

        Returns:
            The option value.
        """
        return self.options.get(key, default)
