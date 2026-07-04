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
"""Initialization of the Harbor integration for ZenML.

Harbor (https://www.harborframework.com/) is an agent-evaluation framework:
a *task* is one containerized problem with a verifier, a *trial* is one
agent attempt on one task, and a *job* runs a set of trials. This
integration runs Harbor eval campaigns as ZenML pipelines — ZenML owns the
outer orchestration (matrix expansion, per-shard steps, retries, caching,
artifacts, reports) while Harbor keeps the trial eval kernel (task loading,
agent loop, verifier, reward). Trials execute inside the active stack's
Sandbox component via :class:`ZenMLSandboxEnvironment`.
"""

import sys
from typing import List, Optional

from zenml.integrations.constants import HARBOR
from zenml.integrations.integration import Integration
from zenml.logger import get_logger

logger = get_logger(__name__)

# Import path Harbor uses to load the ZenML Sandbox environment bridge —
# usable programmatically via `EnvironmentConfig(import_path=...)` or on
# the CLI via `harbor run --environment-import-path <this>`.
ZENML_HARBOR_ENV_IMPORT_PATH = (
    "zenml.integrations.harbor.environment:ZenMLSandboxEnvironment"
)

# Harbor publishes wheels for Python >= 3.12 only, while ZenML supports
# older interpreters too. Requirements are reported as empty below 3.12 so
# requirement exports and bulk installs stay resolvable there.
_HARBOR_MIN_PYTHON = (3, 12)


class HarborIntegration(Integration):
    """Definition of Harbor integration for ZenML."""

    NAME = HARBOR
    REQUIREMENTS = ["harbor>=0.8,<0.9"]

    @classmethod
    def check_installation(cls) -> bool:
        """Method to check whether the integration is usable.

        Returns:
            True if Harbor's requirements are installed and the running
            interpreter meets Harbor's minimum Python version. Without
            the version guard, the empty requirements list reported
            below that version would make this vacuously True.
        """
        if sys.version_info[:2] < _HARBOR_MIN_PYTHON:
            return False
        return super().check_installation()

    @classmethod
    def get_requirements(
        cls,
        target_os: Optional[str] = None,
        python_version: Optional[str] = None,
    ) -> List[str]:
        """Method to get the requirements for the integration.

        Args:
            target_os: The target operating system to get the requirements
                for.
            python_version: The Python version to use for the requirements.
                Falls back to the running interpreter's version if not
                given.

        Returns:
            A list of requirements, empty if the Python version is below
            Harbor's minimum supported version.
        """
        if python_version:
            parts = python_version.split(".")
            version = (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
        else:
            version = sys.version_info[:2]

        if version < _HARBOR_MIN_PYTHON:
            # Warn only on the explicit-version path (installs and Docker
            # builds); `check_installation` hits the interpreter fallback
            # on every pipeline run, which must stay quiet.
            log = logger.warning if python_version else logger.debug
            log(
                "The Harbor integration requires Python %s or newer "
                "(requested version: %s). Returning no requirements.",
                ".".join(str(v) for v in _HARBOR_MIN_PYTHON),
                ".".join(str(v) for v in version),
            )
            return []

        return cls.REQUIREMENTS

    @classmethod
    def activate(cls) -> None:
        """Activate the Harbor integration."""
        from zenml.integrations.harbor import materializers  # noqa
