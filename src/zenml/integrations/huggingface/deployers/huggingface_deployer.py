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
"""Implementation of the ZenML Huggingface deployer."""

import os
import re
import tempfile
from typing import (
    TYPE_CHECKING,
    Dict,
    Generator,
    Optional,
    Type,
    cast,
)

from pydantic import BaseModel

from zenml.config.base_settings import BaseSettings
from zenml.deployers.base_deployer import BaseDeployerSettings
from zenml.deployers.containerized_deployer import ContainerizedDeployer
from zenml.deployers.exceptions import (
    DeployerError,
    DeploymentDeprovisionError,
    DeploymentLogsNotFoundError,
    DeploymentNotFoundError,
    DeploymentProvisionError,
)
from zenml.enums import DeploymentStatus
from zenml.integrations.huggingface.flavors.huggingface_deployer_flavor import (
    HuggingfaceDeployerConfig,
)
from zenml.logger import get_logger
from zenml.models import DeploymentOperationalState, DeploymentResponse

if TYPE_CHECKING:
    from zenml.stack import Stack

logger = get_logger(__name__)


class HuggingfaceDeploymentMetadata(BaseModel):
    """Metadata for a Huggingface Space deployment.

    Attributes:
        space_id: Full Space ID in format 'username/space-name'
        space_url: URL to the Space on Huggingface
        space_hardware: Hardware tier the Space is running on
        space_storage: Storage tier for the Space
    """

    space_id: Optional[str] = None
    space_url: Optional[str] = None
    space_hardware: Optional[str] = None
    space_storage: Optional[str] = None

    @classmethod
    def from_deployment(
        cls, deployment: DeploymentResponse
    ) -> "HuggingfaceDeploymentMetadata":
        """Build metadata object from a deployment record.

        Args:
            deployment: The deployment to read metadata from.

        Returns:
            Parsed Huggingface deployment metadata.
        """
        return cls.model_validate(deployment.deployment_metadata or {})


class HuggingfaceDeployerSettings(BaseDeployerSettings):
    """Huggingface deployer settings.

    Attributes:
        space_hardware: Hardware tier to use for the Space. Examples: 'cpu-basic',
            'cpu-upgrade', 't4-small', 't4-medium', 'a10g-small', 'a10g-large'.
            If not specified, uses the config default or 'cpu-basic'
        space_storage: Persistent storage tier for the Space. Options: 'small',
            'medium', 'large'. If not specified, uses ephemeral storage
        private: Whether to create a private Space
        app_port: Port the Docker container exposes for the application. Defaults
            to 7860 which is the standard Huggingface Spaces port
    """

    space_hardware: Optional[str] = None
    space_storage: Optional[str] = None
    private: bool = False
    app_port: int = 7860


class HuggingfaceDeployer(ContainerizedDeployer):
    """Deployer that runs deployments as Huggingface Spaces."""

    @property
    def settings_class(self) -> Optional[Type[BaseSettings]]:
        """Settings class for the Huggingface deployer.

        Returns:
            The settings class.
        """
        return HuggingfaceDeployerSettings

    @property
    def config(self) -> HuggingfaceDeployerConfig:
        """Returns the `HuggingfaceDeployerConfig` config.

        Returns:
            The configuration.
        """
        return cast(HuggingfaceDeployerConfig, self._config)

    def _get_hf_api(self) -> "HfApi":  # type: ignore[name-defined]
        """Get the Huggingface API client.

        Returns:
            The Huggingface API client.

        Raises:
            DeployerError: If huggingface_hub is not installed.
        """
        try:
            from huggingface_hub import HfApi
        except ImportError:
            raise DeployerError(
                "The huggingface_hub package is required to use the "
                "Huggingface deployer. Please install it with: "
                "`pip install huggingface_hub`"
            )

        token = self.config.token or os.environ.get("HF_TOKEN")
        return HfApi(token=token)

    def _sanitize_space_name(self, name: str) -> str:
        """Sanitize a deployment name to be valid for Huggingface Spaces.

        Args:
            name: The deployment name.

        Returns:
            A sanitized Space name.
        """
        # Replace invalid characters with hyphens
        sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "-", name)
        # Remove consecutive hyphens
        sanitized = re.sub(r"-+", "-", sanitized)
        # Remove leading/trailing hyphens
        sanitized = sanitized.strip("-")
        # Handle empty result
        if not sanitized:
            sanitized = "zenml-deployment"
        # Ensure it starts with alphanumeric
        if not sanitized[0].isalnum():
            sanitized = f"z{sanitized}"
        # Limit length (Huggingface has a max length)
        if len(sanitized) > 96:
            sanitized = sanitized[:96].rstrip("-")
        return sanitized.lower()

    def _get_space_id(self, deployment: DeploymentResponse) -> str:
        """Get the Space ID for a deployment.

        Args:
            deployment: The deployment.

        Returns:
            The Space ID in format 'username/space-name'.

        Raises:
            DeployerError: If username cannot be determined.
        """
        api = self._get_hf_api()
        try:
            # Get the username from the API
            user_info = api.whoami()
            username = user_info["name"]
        except Exception as e:
            raise DeployerError(
                f"Failed to get Huggingface username: {e}. "
                "Please ensure your token is valid."
            ) from e

        space_name = self._sanitize_space_name(
            f"{self.config.space_prefix}-{deployment.name}"
        )
        return f"{username}/{space_name}"

    def _create_readme(
        self,
        deployment: DeploymentResponse,
        settings: HuggingfaceDeployerSettings,
    ) -> str:
        """Create README.md content for the Space.

        Args:
            deployment: The deployment.
            settings: The deployer settings.

        Returns:
            README.md content.
        """
        app_port = settings.app_port

        return f"""---
title: {deployment.name}
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_port: {app_port}
---

# {deployment.name}

This is a ZenML deployment running on Huggingface Spaces.
"""

    def _create_dockerfile(
        self,
        deployment: DeploymentResponse,
        image: str,
        environment: Dict[str, str],
        secrets: Dict[str, str],
    ) -> str:
        """Create Dockerfile content for the Space.

        Args:
            deployment: The deployment.
            image: The Docker image to use.
            environment: Environment variables.
            secrets: Secret environment variables.

        Returns:
            Dockerfile content.
        """
        # Combine environment and secrets
        all_env = {**environment, **secrets}

        # Build ENV statements
        env_lines = []
        for key, value in all_env.items():
            # Escape backslashes first, then quotes
            escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
            env_lines.append(f'ENV {key}="{escaped_value}"')

        env_statements = "\n".join(env_lines)

        return f"""FROM {image}

# Set environment variables
{env_statements}

# Huggingface Spaces runs as user ID 1000
USER 1000

# The container is already configured to run the deployment app
"""

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
            HuggingfaceDeployerSettings,
            self.get_settings(deployment.snapshot),
        )

        api = self._get_hf_api()
        space_id = self._get_space_id(deployment)

        try:
            # Get the Docker image
            image = self.get_image(deployment.snapshot)
            logger.info(f"Using Docker image: {image}")

            # Check if Space already exists
            space_exists = False
            try:
                api.space_info(space_id)
                space_exists = True
                logger.info(f"Space {space_id} already exists, updating it")
            except Exception:
                logger.info(f"Creating new Space {space_id}")

            # Create or get the Space
            if not space_exists:
                api.create_repo(
                    repo_id=space_id,
                    repo_type="space",
                    space_sdk="docker",
                    private=settings.private,
                )

            # Create temporary directory for Space files
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create README.md
                readme_content = self._create_readme(deployment, settings)
                readme_path = os.path.join(tmpdir, "README.md")
                with open(readme_path, "w") as f:
                    f.write(readme_content)

                # Create Dockerfile
                dockerfile_content = self._create_dockerfile(
                    deployment, image, environment, secrets
                )
                dockerfile_path = os.path.join(tmpdir, "Dockerfile")
                with open(dockerfile_path, "w") as f:
                    f.write(dockerfile_content)

                # Upload files to the Space
                logger.info(f"Uploading files to Space {space_id}")
                api.upload_file(
                    path_or_fileobj=readme_path,
                    path_in_repo="README.md",
                    repo_id=space_id,
                    repo_type="space",
                )
                api.upload_file(
                    path_or_fileobj=dockerfile_path,
                    path_in_repo="Dockerfile",
                    repo_id=space_id,
                    repo_type="space",
                )

            # Set hardware if specified
            hardware = settings.space_hardware or self.config.space_hardware
            if hardware:
                try:
                    from huggingface_hub import SpaceHardware

                    # Map string to SpaceHardware enum
                    hardware_value = getattr(
                        SpaceHardware, hardware.upper().replace("-", "_")
                    )
                    api.request_space_hardware(
                        repo_id=space_id, hardware=hardware_value
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to set hardware to {hardware}: {e}"
                    )

            # Set storage if specified
            storage = settings.space_storage or self.config.space_storage
            if storage:
                try:
                    from huggingface_hub import SpaceStorage

                    storage_value = getattr(SpaceStorage, storage.upper())
                    api.request_space_storage(
                        repo_id=space_id, storage=storage_value
                    )
                except Exception as e:
                    logger.warning(f"Failed to set storage to {storage}: {e}")

            space_url = f"https://huggingface.co/spaces/{space_id}"
            metadata = HuggingfaceDeploymentMetadata(
                space_id=space_id,
                space_url=space_url,
                space_hardware=hardware,
                space_storage=storage,
            )

            # Return PENDING status - the Space needs time to build and start
            return DeploymentOperationalState(
                status=DeploymentStatus.PENDING,
                url=space_url,
                metadata=metadata.model_dump(exclude_none=True),
            )

        except Exception as e:
            raise DeploymentProvisionError(
                f"Failed to provision Huggingface Space: {e}"
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
        assert deployment.snapshot, "Pipeline snapshot not found"
        meta = HuggingfaceDeploymentMetadata.from_deployment(deployment)

        if not meta.space_id:
            raise DeploymentNotFoundError(
                f"Space ID not found for deployment '{deployment.name}'"
            )

        api = self._get_hf_api()

        try:
            # Get Space runtime information
            runtime = api.get_space_runtime(repo_id=meta.space_id)

            # Determine status based on runtime stage
            # SpaceStage enum values: NO_APP_FILE, CONFIG_ERROR, BUILDING,
            # BUILD_ERROR, RUNNING, RUNNING_BUILDING, RUNTIME_ERROR, DELETING,
            # STOPPED, PAUSED
            status = DeploymentStatus.PENDING
            if runtime.stage in ["RUNNING", "RUNNING_BUILDING"]:
                status = DeploymentStatus.RUNNING
            elif runtime.stage in [
                "BUILD_ERROR",
                "RUNTIME_ERROR",
                "CONFIG_ERROR",
                "STOPPED",
                "PAUSED",
            ]:
                status = DeploymentStatus.ERROR
            elif runtime.stage in ["BUILDING", "NO_APP_FILE"]:
                status = DeploymentStatus.PENDING
            elif runtime.stage == "DELETING":
                status = DeploymentStatus.ERROR
            elif runtime.stage in ["APP_STARTING", "RUNTIME_PREWARM"]:
                # These might be legacy values, keeping for compatibility
                status = DeploymentStatus.PENDING

            return DeploymentOperationalState(
                status=status,
                url=meta.space_url,
                metadata=meta.model_dump(exclude_none=True),
            )

        except Exception as e:
            # If we can't get the Space info, it might not exist
            logger.debug(
                f"Failed to get Space runtime for {meta.space_id}: {e}"
            )
            raise DeploymentNotFoundError(
                f"Space {meta.space_id} not found or inaccessible"
            ) from e

    def do_get_deployment_state_logs(
        self,
        deployment: DeploymentResponse,
        follow: bool = False,
        tail: Optional[int] = None,
    ) -> Generator[str, bool, None]:
        """Get logs from a Huggingface Space deployment.

        Note: Huggingface Spaces API does not currently provide direct log access.
        Users should view logs directly in the Huggingface Spaces UI.

        Args:
            deployment: The deployment to read logs for.
            follow: Stream logs if True (not supported).
            tail: Return only last N lines if set (not supported).

        Yields:
            Log lines.

        Raises:
            DeploymentLogsNotFoundError: Always, as logs are not available via API.
        """
        meta = HuggingfaceDeploymentMetadata.from_deployment(deployment)
        log_url = (
            f"{meta.space_url}/logs" if meta.space_url else "the Space page"
        )
        raise DeploymentLogsNotFoundError(
            f"Logs for Huggingface Space {meta.space_id} cannot be retrieved "
            f"via API. Please view logs at {log_url}"
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
            DeploymentDeprovisionError: If deletion fails.
        """
        meta = HuggingfaceDeploymentMetadata.from_deployment(deployment)
        if not meta.space_id:
            raise DeploymentNotFoundError(
                f"Space ID not found for deployment '{deployment.name}'"
            )

        api = self._get_hf_api()

        try:
            logger.info(f"Deleting Huggingface Space {meta.space_id}")
            api.delete_repo(
                repo_id=meta.space_id,
                repo_type="space",
            )
            logger.info(f"Successfully deleted Space {meta.space_id}")
            return None

        except Exception as e:
            # Check if it's a 404 (already deleted)
            if "404" in str(e) or "not found" in str(e).lower():
                logger.info(
                    f"Space {meta.space_id} already deleted or not found"
                )
                return None

            raise DeploymentDeprovisionError(
                f"Failed to delete Huggingface Space {meta.space_id}: {e}"
            ) from e
