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
"""Initialization of the MLX integration."""

import platform
import sys
from typing import List, Optional

from zenml.integrations.constants import MLX
from zenml.integrations.integration import Integration

def _is_supported_platform() -> bool:
    """Check if the current platform supports MLX.
    
    MLX requires:
    - macOS with ARM64 (Apple Silicon)
    - Linux (any architecture)
    
    Returns:
        True if platform is supported, False otherwise.
    """
    if sys.platform == "linux":
        return True
    elif sys.platform == "darwin":
        # MLX only supports Apple Silicon Macs, not Intel
        machine = platform.machine().lower()
        return machine in ("arm64", "aarch64")
    return False


class MLXIntegration(Integration):
    """Definition of MLX array integration for ZenML."""

    NAME = MLX

    @classmethod
    def check_installation(cls) -> bool:
        return False if not _is_supported_platform() else super().check_installation()

    @classmethod
    def get_requirements(
        cls,
        target_os: Optional[str] = None,
        python_version: Optional[str] = None,
    ) -> List[str]:
        # sys.platform is "darwin", while platform.system() is "Darwin",
        # similarly on Linux.
        target_os = (target_os or sys.platform).lower()
        if target_os == "darwin":
            # Only return requirements if on Apple Silicon
            machine = platform.machine().lower()
            return ["mlx"] if machine in ("arm64", "aarch64") else []
        elif target_os == "linux":
            return ["mlx[cpu]"]
        else:
            return []

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        from zenml.integrations.mlx import materializer  # noqa
