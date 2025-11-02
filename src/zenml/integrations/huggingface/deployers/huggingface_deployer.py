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
"""Implementation of the ZenML Hugging Face deployer."""

import os
import re
import tempfile
from typing import (
    TYPE_CHECKING,
    Dict,
    Generator,
    Optional,
    Tuple,
    Type,
    cast,
)

from zenml.client import Client
from zenml.config.base_settings import BaseSettings
from zenml.deployers.base_deployer import BaseDeployerSettings
from zenml.deployers.containerized_deployer import ContainerizedDeployer
from zenml.deployers.exceptions import (
    DeployerError,
    DeploymentLogsNotFoundError,
    DeploymentNotFoundError,
    DeploymentProvisionError,
)
from zenml.enums import DeploymentStatus
from zenml.integrations.huggingface.flavors.huggingface_deployer_flavor import (
    HuggingFaceDeployerConfig,
)
from zenml.logger import get_logger
from zenml.models import DeploymentOperationalState, DeploymentResponse
from zenml.stack.stack_validator import StackValidator

if TYPE_CHECKING:
    from huggingface_hub import HfApi

    from zenml.stack import Stack

logger = get_logger(__name__)


class HuggingFaceDeployerSettings(BaseDeployerSettings):
    """Hugging Face deployer settings.

    Attributes:
        space_hardware: Hardware tier for the Space (e.g., 'cpu-basic', 't4-small')
        space_storage: Persistent storage tier (e.g., 'small', 'medium', 'large')
        private: Whether to create a private Space
        app_port: Port the container exposes (default 7860)
    """

    space_hardware: Optional[str] = None
    space_storage: Optional[str] = None
    private: bool = False
    app_port: int = 7860


class HuggingFaceDeployer(ContainerizedDeployer):
    """Deployer that runs deployments as Hugging Face Spaces."""

    @property
    def settings_class(self) -> Optional[Type[BaseSettings]]:
        """Settings class for the Hugging Face deployer.

        Returns:
            The settings class.
        """
        return HuggingFaceDeployerSettings

    @property
    def config(self) -> HuggingFaceDeployerConfig:
        """Returns the `HuggingFaceDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(HuggingFaceDeployerConfig, self._config)

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks token or secret_name is present.
        """

        def _validate_token_or_secret(
            stack: "Stack",
        ) -> Tuple[bool, str]:
            """Check if secret or token is present.

            Args:
                stack: The stack to validate.

            Returns:
                Tuple of (is_valid, message).
            """
            return bool(self.config.token or self.config.secret_name), (
                "The Hugging Face deployer requires either a token or "
                "secret_name to be configured."
            )

        return StackValidator(
            custom_validation_function=_validate_token_or_secret,
        )

    def _get_token(self) -> Optional[str]:
        """Get the Hugging Face token.

        Returns:
            The token from config, secret, or environment.
        """
        if self.config.token:
            return self.config.token

        if self.config.secret_name:
            client = Client()
            secret = client.get_secret(self.config.secret_name)
            return secret.secret_values.get("token")

        return os.environ.get("HF_TOKEN")

    def _get_hf_api(self) -> "HfApi":
        """Get the Hugging Face API client.

        Returns:
            The Hugging Face API client.

        Raises:
            DeployerError: If huggingface_hub is not installed.
        """
        try:
            from huggingface_hub import HfApi
        except ImportError:
            raise DeployerError(
                "huggingface_hub is required. Install with: pip install huggingface_hub"
            )

        token = self._get_token()
        return HfApi(token=token)

    def _get_space_id(self, deployment: DeploymentResponse) -> str:
        """Get the Space ID for a deployment.

        Args:
            deployment: The deployment.

        Returns:
            The Space ID in format 'username/space-name'.
        """
        api = self._get_hf_api()
        username = api.whoami()["name"]

        # Simple sanitization: alphanumeric, hyphens, underscores only
        sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "-", deployment.name).lower()
        sanitized = sanitized.strip("-") or "deployment"
        space_name = f"{self.config.space_prefix}-{sanitized}"

        return f"{username}/{space_name}"

    def do_provision_deployment(
        self,
        deployment: DeploymentResponse,
        stack: "Stack",
        environment: Dict[str, str],
        secrets: Dict[str, str],
        timeout: int,
    ) -> DeploymentOperationalState:
        """Provision a Huggingface Space deployment.

        Args:
            deployment: The deployment to run.
            stack: The active stack.
            environment: Environment variables for the app.
            secrets: Secret environment variables for the app.
            timeout: Maximum time to wait for deployment.

        Returns:
            Operational state of the provisioned deployment.

        Raises:
            DeploymentProvisionError: If the deployment cannot be provisioned.
        """
        assert deployment.snapshot, "Pipeline snapshot not found"

        settings = cast(
            HuggingFaceDeployerSettings,
            self.get_settings(deployment.snapshot),
        )

        api = self._get_hf_api()
        space_id = self._get_space_id(deployment)
        image = self.get_image(deployment.snapshot)

        try:
            # Create Space if it doesn't exist
            try:
                api.space_info(space_id)
                logger.info(f"Updating existing Space: {space_id}")
            except Exception:
                logger.info(f"Creating new Space: {space_id}")
                api.create_repo(
                    repo_id=space_id,
                    repo_type="space",
                    space_sdk="docker",
                    private=settings.private,
                )

            # Upload Dockerfile and README
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create README
                readme = os.path.join(tmpdir, "README.md")
                with open(readme, "w") as f:
                    f.write(
                        f"---\ntitle: {deployment.name}\nsdk: docker\n"
                        f"app_port: {settings.app_port}\n---\n"
                    )

                # Create Dockerfile
                dockerfile = os.path.join(tmpdir, "Dockerfile")
                env_vars = {**environment, **secrets}
                # Escape backslashes and quotes in environment variable values
                env_lines = [
                    f'ENV {k}="{v.replace(chr(92), chr(92) * 2).replace(chr(34), chr(92) + chr(34))}"'
                    for k, v in env_vars.items()
                ]
                with open(dockerfile, "w") as f:
                    f.write(
                        f"FROM {image}\n"
                        + "\n".join(env_lines)
                        + "\nUSER 1000\n"
                    )

                # Upload files
                api.upload_file(
                    path_or_fileobj=readme,
                    path_in_repo="README.md",
                    repo_id=space_id,
                    repo_type="space",
                )
                api.upload_file(
                    path_or_fileobj=dockerfile,
                    path_in_repo="Dockerfile",
                    repo_id=space_id,
                    repo_type="space",
                )

            # Set hardware and storage if specified
            hardware = settings.space_hardware or self.config.space_hardware
            if hardware:
                try:
                    from huggingface_hub import SpaceHardware

                    api.request_space_hardware(
                        repo_id=space_id,
                        hardware=getattr(
                            SpaceHardware, hardware.upper().replace("-", "_")
                        ),
                    )
                except Exception as e:
                    logger.warning(f"Failed to set hardware {hardware}: {e}")

            storage = settings.space_storage or self.config.space_storage
            if storage:
                try:
                    from huggingface_hub import SpaceStorage

                    api.request_space_storage(
                        repo_id=space_id,
                        storage=getattr(SpaceStorage, storage.upper()),
                    )
                except Exception as e:
                    logger.warning(f"Failed to set storage {storage}: {e}")

            space_url = f"https://huggingface.co/spaces/{space_id}"
            return DeploymentOperationalState(
                status=DeploymentStatus.PENDING,
                url=space_url,
                metadata={"space_id": space_id},
            )

        except Exception as e:
            raise DeploymentProvisionError(
                f"Failed to provision Space: {e}"
            ) from e

    def do_get_deployment_state(
        self, deployment: DeploymentResponse
    ) -> DeploymentOperationalState:
        """Get information about a Huggingface Space deployment.

        Args:
            deployment: The deployment to inspect.

        Returns:
            Operational state of the deployment.

        Raises:
            DeploymentNotFoundError: If the Space is not found.
        """
        space_id = deployment.deployment_metadata.get("space_id")
        if not space_id:
            raise DeploymentNotFoundError("Space ID not found in metadata")

        api = self._get_hf_api()

        try:
            runtime = api.get_space_runtime(repo_id=space_id)

            # Map Space stage to deployment status
            if runtime.stage in ["RUNNING", "RUNNING_BUILDING"]:
                status = DeploymentStatus.RUNNING
            elif runtime.stage in ["BUILDING", "NO_APP_FILE"]:
                status = DeploymentStatus.PENDING
            else:
                # BUILD_ERROR, RUNTIME_ERROR, STOPPED, etc.
                status = DeploymentStatus.ERROR

            return DeploymentOperationalState(
                status=status,
                url=f"https://huggingface.co/spaces/{space_id}",
                metadata={"space_id": space_id},
            )

        except Exception as e:
            raise DeploymentNotFoundError(
                f"Space {space_id} not found: {e}"
            ) from e

    def do_get_deployment_state_logs(
        self,
        deployment: DeploymentResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get logs from a Huggingface Space deployment.

        Args:
            deployment: The deployment to read logs for.
            follow: Stream logs if True (not supported).
            tail: Return only last N lines if set (not supported).

        Raises:
            DeploymentLogsNotFoundError: Always, as logs are not available via API.
        """
        space_id = deployment.deployment_metadata.get("space_id")
        raise DeploymentLogsNotFoundError(
            f"Logs not available via API. View at: "
            f"https://huggingface.co/spaces/{space_id}/logs"
        )

    def do_deprovision_deployment(
        self, deployment: DeploymentResponse, timeout: int
    ) -> Optional[DeploymentOperationalState]:
        """Deprovision a Huggingface Space deployment.

        Args:
            deployment: The deployment to stop.
            timeout: Maximum time to wait for deprovision.

        Returns:
            None, indicating immediate deletion completed.

        Raises:
            DeploymentNotFoundError: If the Space is not found.
            Exception: If deletion fails for reasons other than 404.
        """
        space_id = deployment.deployment_metadata.get("space_id")
        if not space_id:
            raise DeploymentNotFoundError("Space ID not found in metadata")

        api = self._get_hf_api()

        try:
            api.delete_repo(repo_id=space_id, repo_type="space")
            logger.info(f"Deleted Space: {space_id}")
            return None
        except Exception as e:
            if "404" in str(e):
                logger.info(f"Space {space_id} already deleted")
                return None
            raise
