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
"""Sandbox stack components for isolated code execution."""

from zenml.sandboxes.base import (
    BaseSandbox,
    BaseSandboxConfig,
    BaseSandboxFlavor,
    BaseSandboxSettings,
)
from zenml.sandboxes.local_sandbox import (
    LOCAL_SANDBOX_FLAVOR,
    LocalSandbox,
    LocalSandboxConfig,
    LocalSandboxFlavor,
    LocalSandboxSettings,
)
from zenml.sandboxes.process import (
    SandboxExecError,
    SandboxOutput,
    SandboxProcess,
)
from zenml.sandboxes.session import (
    SandboxSession,
    SandboxSessionClosedError,
)
from zenml.sandboxes.snapshot import SandboxSnapshot

__all__ = [
    "LOCAL_SANDBOX_FLAVOR",
    "BaseSandbox",
    "BaseSandboxConfig",
    "BaseSandboxFlavor",
    "BaseSandboxSettings",
    "SandboxSnapshot",
    "LocalSandbox",
    "LocalSandboxConfig",
    "LocalSandboxFlavor",
    "LocalSandboxSettings",
    "SandboxExecError",
    "SandboxOutput",
    "SandboxProcess",
    "SandboxSession",
    "SandboxSessionClosedError",
]
