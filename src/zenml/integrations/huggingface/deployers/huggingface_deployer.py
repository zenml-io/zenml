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

import json
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
from zenml.deployers.server.entrypoint_configuration import (
    DEPLOYMENT_ID_OPTION,
    DeploymentEntrypointConfiguration,
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
        app_port: Port the container exposes (default 8000 for ZenML server)
    """

    space_hardware: Optional[str] = None
    space_storage: Optional[str] = None
    private: bool = False
    app_port: int = 8000


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
            A validator that checks required stack components.
        """

        def _validate_requirements(
            stack: "Stack",
        ) -> Tuple[bool, str]:
            """Check if all requirements are met.

            Args:
                stack: The stack to validate.

            Returns:
                Tuple of (is_valid, message).
            """
            # Check token or secret_name
            if not (self.config.token or self.config.secret_name):
                return False, (
                    "The Hugging Face deployer requires either a token or "
                    "secret_name to be configured."
                )

            # Check container registry
            if not stack.container_registry:
                return False, (
                    "The Hugging Face deployer requires a container registry "
                    "to be part of the stack. The Docker image must be "
                    "pre-built and pushed to a publicly accessible registry."
                )

            return True, ""

        return StackValidator(
            custom_validation_function=_validate_requirements,
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

    def _get_entrypoint_and_command(
        self, deployment: DeploymentResponse
    ) -> Tuple[str, str]:
        """Generate ENTRYPOINT and CMD for the Dockerfile.

        Args:
            deployment: The deployment.

        Returns:
            Tuple of (ENTRYPOINT line, CMD line) for Dockerfile.
        """
        # Get entrypoint command: ["python", "-m", "zenml.entrypoints.entrypoint"]
        entrypoint = DeploymentEntrypointConfiguration.get_entrypoint_command()

        # Get arguments with deployment ID
        arguments = DeploymentEntrypointConfiguration.get_entrypoint_arguments(
            **{DEPLOYMENT_ID_OPTION: deployment.id}
        )

        # Format as JSON arrays for Dockerfile exec form
        # Use json.dumps() to ensure proper JSON with double quotes
        entrypoint_line = f"ENTRYPOINT {json.dumps(entrypoint)}"
        cmd_line = f"CMD {json.dumps(arguments)}"

        return entrypoint_line, cmd_line

    def _generate_image_reference_dockerfile(
        self,
        image: str,
        deployment: DeploymentResponse,
    ) -> str:
        """Generate Dockerfile that references a pre-built image.

        Note: Environment variables and secrets are NOT included in the
        Dockerfile for security reasons. They are set using Hugging Face's
        Space secrets and variables API instead.

        Args:
            image: The pre-built image to reference.
            deployment: The deployment.

        Returns:
            The Dockerfile content.
        """
        lines = [f"FROM {image}"]

        # Add user
        lines.append("USER 1000")

        # Add entrypoint and command
        entrypoint_line, cmd_line = self._get_entrypoint_and_command(
            deployment
        )
        lines.append(entrypoint_line)
        lines.append(cmd_line)

        return "\n".join(lines)

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

        logger.info(
            f"Deploying image {image} to Hugging Face Space. "
            "Ensure the image is publicly accessible."
        )

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
                dockerfile_content = self._generate_image_reference_dockerfile(
                    image, deployment
                )

                with open(dockerfile, "w") as f:
                    f.write(dockerfile_content)

                # Upload README
                api.upload_file(
                    path_or_fileobj=readme,
                    path_in_repo="README.md",
                    repo_id=space_id,
                    repo_type="space",
                )

                # Upload Dockerfile
                api.upload_file(
                    path_or_fileobj=dockerfile,
                    path_in_repo="Dockerfile",
                    repo_id=space_id,
                    repo_type="space",
                )

            # Set environment variables using Space variables API
            # This is secure - variables are not exposed in the Dockerfile
            logger.info(f"Setting {len(environment)} environment variables...")
            for key, value in environment.items():
                try:
                    api.add_space_variable(
                        repo_id=space_id,
                        key=key,
                        value=value,
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to set environment variable {key}: {e}"
                    )

            # Set secrets using Space secrets API
            # This is secure - secrets are encrypted and not exposed
            logger.info(f"Setting {len(secrets)} secrets...")
            for key, value in secrets.items():
                try:
                    api.add_space_secret(
                        repo_id=space_id,
                        key=key,
                        value=value,
                    )
                except Exception as e:
                    logger.warning(f"Failed to set secret {key}: {e}")

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
