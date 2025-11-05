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

from zenml.config.base_settings import BaseSettings
from zenml.deployers.containerized_deployer import ContainerizedDeployer
from zenml.deployers.exceptions import (
    DeployerError,
    DeploymentDeprovisionError,
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
    HuggingFaceDeployerSettings,
)
from zenml.logger import get_logger
from zenml.models import DeploymentOperationalState, DeploymentResponse
from zenml.stack.stack_validator import StackValidator

if TYPE_CHECKING:
    from huggingface_hub import HfApi

    from zenml.stack import Stack

# HF Space name max length (repo name limit)
HF_SPACE_NAME_MAX_LENGTH = 96

logger = get_logger(__name__)


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
            # Check token
            if not self.config.token:
                return False, (
                    "The Hugging Face deployer requires a token to be "
                    "configured. Use --token parameter with a direct token "
                    "value or reference a ZenML secret with {{secret.key}} syntax."
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
            The token from config or environment. If config.token uses secret
            reference syntax like {{secret.key}}, ZenML automatically resolves it.
        """
        return self.config.token or os.environ.get("HF_TOKEN")

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

        Supports deploying to either a user account or organization.

        Args:
            deployment: The deployment.

        Returns:
            The Space ID in format 'owner/space-name' where owner is either
            the username or organization name, and space-name includes a
            UUID suffix for uniqueness.

        Raises:
            DeployerError: If the space name exceeds HF's maximum length.
        """
        # Get owner (organization or username)
        if self.config.organization:
            owner = self.config.organization
        else:
            api = self._get_hf_api()
            owner = api.whoami()["name"]

        # Sanitize deployment name: alphanumeric, hyphens, underscores only
        sanitized = re.sub(r"[^a-zA-Z0-9\-_]", "-", deployment.name).lower()
        sanitized = sanitized.strip("-") or "deployment"

        # Add UUID suffix for uniqueness (first 8 chars of deployment ID)
        uuid_suffix = str(deployment.id)[:8]
        space_name = f"{self.config.space_prefix}-{sanitized}-{uuid_suffix}"

        # Validate length (HF has 96 char limit for repo names)
        if len(space_name) > HF_SPACE_NAME_MAX_LENGTH:
            raise DeployerError(
                f"Space name '{space_name}' exceeds Hugging Face's "
                f"maximum length of {HF_SPACE_NAME_MAX_LENGTH} characters. "
                f"Please use a shorter deployment name or space_prefix."
            )

        return f"{owner}/{space_name}"

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
            timeout: Maximum time to wait for deployment (unused).

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

        # Handle space_id mismatch (e.g., renamed deployment or changed prefix)
        old_space_id = deployment.deployment_metadata.get("space_id")
        if old_space_id and old_space_id != space_id:
            logger.info(
                f"Space ID changed from {old_space_id} to {space_id}. "
                f"Cleaning up old Space..."
            )
            try:
                self.do_deprovision_deployment(deployment, timeout=0)
            except Exception as e:
                logger.warning(
                    f"Failed to clean up old Space {old_space_id}: {e}"
                )

        logger.info(
            f"Deploying image {image} to Hugging Face Space. "
            "Ensure the image is publicly accessible."
        )

        try:
            from huggingface_hub import SpaceStage
            from huggingface_hub.errors import HfHubHTTPError

            # Create Space if it doesn't exist, or update visibility if needed
            try:
                space_info = api.space_info(space_id)
                logger.info(f"Updating existing Space: {space_id}")

                # Check if Space is sleeping/paused and restart it
                # Note: runtime.stage is a string, compare using enum.value
                runtime = api.get_space_runtime(repo_id=space_id)
                if runtime.stage in [
                    SpaceStage.STOPPED.value,
                    SpaceStage.PAUSED.value,
                ]:
                    logger.info(
                        f"Space {space_id} is {runtime.stage}. Restarting..."
                    )
                    api.restart_space(repo_id=space_id)

                # Update visibility if changed
                if space_info.private != settings.private:
                    logger.info(
                        f"Updating Space visibility: "
                        f"{'private' if settings.private else 'public'}"
                    )
                    api.update_repo_settings(
                        repo_id=space_id,
                        private=settings.private,
                        repo_type="space",
                    )
            except HfHubHTTPError as e:
                if e.response.status_code != 404:
                    raise DeploymentProvisionError(
                        f"Failed to check Space {space_id}: {e}"
                    ) from e
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
                # Get port from deployment settings
                port = deployment.snapshot.pipeline_configuration.deployment_settings.uvicorn_port
                with open(readme, "w") as f:
                    f.write(
                        f"---\ntitle: {deployment.name}\nsdk: docker\n"
                        f"app_port: {port}\n---\n"
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
            # Note: add_space_variable is an upsert operation (adds or updates)
            logger.info(f"Setting {len(environment)} environment variables...")
            for key, value in environment.items():
                try:
                    api.add_space_variable(
                        repo_id=space_id,
                        key=key,
                        value=value,
                    )
                except Exception as e:
                    raise DeploymentProvisionError(
                        f"Failed to set environment variable {key}: {e}"
                    ) from e

            # Set secrets using Space secrets API
            # This is secure - secrets are encrypted and not exposed
            # Note: add_space_secret is an upsert operation (adds or updates)
            logger.info(f"Setting {len(secrets)} secrets...")
            for key, value in secrets.items():
                try:
                    api.add_space_secret(
                        repo_id=space_id,
                        key=key,
                        value=value,
                    )
                except Exception as e:
                    raise DeploymentProvisionError(
                        f"Failed to set secret {key}: {e}"
                    ) from e

            # Set hardware if specified (fail if this doesn't work)
            # Note: request_space_hardware replaces the current hardware tier
            hardware = settings.space_hardware or self.config.space_hardware
            if hardware:
                from huggingface_hub import SpaceHardware

                try:
                    api.request_space_hardware(
                        repo_id=space_id,
                        hardware=getattr(
                            SpaceHardware, hardware.upper().replace("-", "_")
                        ),
                    )
                    logger.info(f"Requested hardware: {hardware}")
                except AttributeError:
                    raise DeploymentProvisionError(
                        f"Invalid hardware tier '{hardware}'. "
                        f"See https://huggingface.co/docs/hub/spaces-gpus"
                    )
                except Exception as e:
                    raise DeploymentProvisionError(
                        f"Failed to set hardware {hardware}: {e}"
                    ) from e

            # Set storage if specified (fail if this doesn't work)
            # Note: request_space_storage replaces the current storage tier
            storage = settings.space_storage or self.config.space_storage
            if storage:
                from huggingface_hub import SpaceStorage

                try:
                    api.request_space_storage(
                        repo_id=space_id,
                        storage=getattr(SpaceStorage, storage.upper()),
                    )
                    logger.info(f"Requested storage: {storage}")
                except AttributeError:
                    raise DeploymentProvisionError(
                        f"Invalid storage tier '{storage}'. "
                        f"Valid options: small, medium, large"
                    )
                except Exception as e:
                    raise DeploymentProvisionError(
                        f"Failed to set storage {storage}: {e}"
                    ) from e

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
            from huggingface_hub import SpaceStage

            runtime = api.get_space_runtime(repo_id=space_id)

            domains = runtime.raw.get("domains", [])
            domain_stage = domains[0].get("stage") if domains else None

            # Map HuggingFace Space stages to ZenML standard deployment states
            # Note: runtime.stage is a string, compare using enum.value
            # Only RUNNING + domain READY means fully provisioned with health endpoint available
            if runtime.stage == SpaceStage.RUNNING.value:
                # Check if domain is also ready (not just Space running)
                if domains and domains[0].get("stage") == "READY":
                    status = DeploymentStatus.RUNNING
                else:
                    # Space is running but domain not ready yet (DNS propagating, etc.)
                    status = DeploymentStatus.PENDING
            # Building/updating states - health endpoint not yet available
            elif runtime.stage in [
                SpaceStage.BUILDING.value,
                SpaceStage.RUNNING_BUILDING.value,
                "RUNNING_APP_STARTING",  # New HF stage: app is starting
            ]:
                status = DeploymentStatus.PENDING
            # Error states - deployment failed or misconfigured
            elif runtime.stage in [
                SpaceStage.BUILD_ERROR.value,
                SpaceStage.RUNTIME_ERROR.value,
                SpaceStage.CONFIG_ERROR.value,
                SpaceStage.NO_APP_FILE.value,
            ]:
                status = DeploymentStatus.ERROR
            # Stopped/paused states - deployment exists but not running
            elif runtime.stage in [
                SpaceStage.STOPPED.value,
                SpaceStage.PAUSED.value,
                SpaceStage.DELETING.value,
            ]:
                status = DeploymentStatus.ABSENT
            else:
                # Unknown/future stages - log once for visibility
                logger.warning(
                    f"Space {space_id} has unrecognized stage: '{runtime.stage}'"
                )
                status = DeploymentStatus.UNKNOWN

            # Get deployment URL from Space domains (only when fully ready)
            url = None
            if (
                domain_stage == "READY"
                and domains
                and domains[0].get("domain")
            ):
                url = f"https://{domains[0]['domain']}"

            return DeploymentOperationalState(
                status=status,
                url=url,
                metadata={
                    "space_id": space_id,
                    "external_state": runtime.stage,
                    "domain_stage": domain_stage,
                },
            )

        except Exception as e:
            raise DeploymentNotFoundError(
                f"Space {space_id} not found: {e}"
            ) from e

    def _check_deployment_health(
        self,
        deployment: DeploymentResponse,
    ) -> bool:
        """Check if the deployment is healthy.

        For HuggingFace Spaces, we skip the HTTP health check because:
        1. Private Spaces block unauthenticated health check requests (404)
        2. We already have reliable state from HuggingFace API
        3. If Space stage is RUNNING and domain is READY, deployment is healthy

        Args:
            deployment: The deployment to check.

        Returns:
            True if the deployment is healthy (always True for HF Spaces).
        """
        # HuggingFace Spaces: Skip HTTP health check, rely on Space runtime state
        # We already verified Space is RUNNING and domain is READY in get_deployment_state
        return True

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
            timeout: Maximum time to wait for deprovision (unused - deletion is immediate).

        Returns:
            None, indicating immediate deletion completed.

        Raises:
            DeploymentNotFoundError: If the Space ID is not in metadata.
            DeploymentDeprovisionError: If deletion fails.
        """
        space_id = deployment.deployment_metadata.get("space_id")
        if not space_id:
            raise DeploymentNotFoundError("Space ID not found in metadata")

        api = self._get_hf_api()

        try:
            from huggingface_hub.errors import HfHubHTTPError

            api.delete_repo(repo_id=space_id, repo_type="space")
            logger.info(f"Deleted Space: {space_id}")
            return None
        except HfHubHTTPError as e:
            if e.response.status_code == 404:
                logger.info(f"Space {space_id} already deleted")
                return None
            raise DeploymentDeprovisionError(
                f"Failed to delete Space {space_id}: {e}"
            ) from e
