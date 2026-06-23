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
"""SSH step operator flavor."""

from typing import TYPE_CHECKING, List, Optional, Type

from pydantic import Field

from zenml.config.base_settings import BaseSettings
from zenml.integrations.ssh import SSH_STEP_OPERATOR_FLAVOR
from zenml.integrations.ssh.flavors.ssh_base_flavor import (
    SSHConnectionConfigMixin,
)
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor

if TYPE_CHECKING:
    from zenml.integrations.ssh.step_operators import SSHStepOperator


class SSHStepOperatorSettings(BaseSettings):
    """Per-step settings for SSH step operator execution.

    Attributes:
        gpu_indices: Specific GPU device indices to expose to the container
            via Docker --gpus flag.
        docker_run_args: Additional arguments to pass to docker run (do not
            include secrets here as they may appear in process listings).
    """

    gpu_indices: Optional[List[int]] = Field(
        default=None,
        description="GPU device indices to expose inside the container via "
        "the Docker --gpus flag, or None for CPU-only execution. Give "
        "concurrent steps on the same host distinct indices to avoid "
        "oversubscribing a GPU",
    )
    docker_run_args: Optional[List[str]] = Field(
        default=None,
        description="Additional arguments for the docker run command, "
        "inserted before the image name. Do not include secrets here",
    )


class SSHStepOperatorConfig(
    BaseStepOperatorConfig, SSHConnectionConfigMixin, SSHStepOperatorSettings
):
    """Configuration for the SSH step operator.

    Connection/auth fields (hostname, username, ssh_key_path, ...) come from
    :class:`SSHConnectionConfigMixin`.

    Example registration:
    ```bash
    zenml step-operator register my-gpu-box \\
        --flavor=ssh \\
        --hostname=gpu-server.example.com \\
        --username=ubuntu \\
        --ssh_key_path=~/.ssh/id_ed25519
    ```
    """

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        Returns:
            True because the SSH step operator always runs remotely.
        """
        return True

    @property
    def is_local(self) -> bool:
        """Checks if this stack component is running locally.

        Returns:
            False because the SSH step operator always runs remotely.
        """
        return False


class SSHStepOperatorFlavor(BaseStepOperatorFlavor):
    """SSH step operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return SSH_STEP_OPERATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/ssh.png"

    @property
    def config_class(self) -> Type[SSHStepOperatorConfig]:
        """Returns SSHStepOperatorConfig config class.

        Returns:
            The config class.
        """
        return SSHStepOperatorConfig

    @property
    def implementation_class(self) -> Type["SSHStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.ssh.step_operators import SSHStepOperator

        return SSHStepOperator
