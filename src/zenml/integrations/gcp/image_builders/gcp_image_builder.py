#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Google Cloud Builder image builder implementation."""

from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, cast
from urllib.parse import urlparse

from google.cloud.devtools import cloudbuild_v1

from zenml.enums import ContainerRegistryFlavor, StackComponentType
from zenml.image_builders import BaseImageBuilder
from zenml.integrations.gcp import GCP_ARTIFACT_STORE_FLAVOR
from zenml.integrations.gcp.flavors import GCPImageBuilderConfig
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsMixin,
)
from zenml.logger import get_logger
from zenml.stack import StackValidator

if TYPE_CHECKING:
    from zenml.container_registries import BaseContainerRegistry
    from zenml.image_builders import BuildContext
    from zenml.stack import Stack

logger = get_logger(__name__)


class GCPImageBuilder(BaseImageBuilder, GoogleCredentialsMixin):
    """Google Cloud Builder image builder implementation."""

    @property
    def config(self) -> GCPImageBuilderConfig:
        """The stack component configuration.

        Returns:
            The configuration.
        """
        return cast(GCPImageBuilderConfig, self._config)

    @property
    def is_building_locally(self) -> bool:
        """Whether the image builder builds the images on the client machine.

        Returns:
            True if the image builder builds locally, False otherwise.
        """
        return False

    @property
    def validator(self) -> Optional["StackValidator"]:
        """Validates the stack for the GCP Image Builder.

        The GCP Image Builder requires a remote container registry to push the
        image to, and a GCP Artifact Store to upload the build context, so
        Cloud Build can access it.

        Returns:
            Stack validator.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            assert stack.container_registry

            if (
                stack.container_registry.flavor
                != ContainerRegistryFlavor.GCP.value
            ):
                return False, (
                    "The GCP Image Builder requires a GCP container registry to "
                    "push the image to. Please update your stack to include a "
                    "GCP container registry and try again."
                )

            if stack.artifact_store.flavor != GCP_ARTIFACT_STORE_FLAVOR:
                return False, (
                    "The GCP Image Builder requires a GCP Artifact Store to "
                    "upload the build context, so Cloud Build can access it."
                    "Please update your stack to include a GCP Artifact Store "
                    "and try again."
                )

            return True, ""

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_validate_remote_components,
        )

    def build(
        self,
        image_name: str,
        build_context: "BuildContext",
        docker_build_options: Dict[str, Any],
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> str:
        """Builds and pushes a Docker image.

        Args:
            image_name: Name of the image to build and push.
            build_context: The build context to use for the image.
            docker_build_options: Docker build options.
            container_registry: Optional container registry to push to.

        Returns:
            The Docker image name with digest.

        Raises:
            RuntimeError: If no container registry is passed, or if the Cloud
                Build build fails.
        """
        if not container_registry:
            raise RuntimeError(
                "The GCP Image Builder requires a container registry to push "
                "the image to. Please provide one and try again."
            )

        logger.info("Using Cloud Build to build image `%s`", image_name)
        cloud_build_context = self._upload_build_context(
            build_context=build_context,
            parent_path_directory_name="cloud-build-contexts",
        )
        build = self._configure_cloud_build(
            image_name=image_name,
            cloud_build_context=cloud_build_context,
            build_options=docker_build_options,
        )
        image_digest = self._run_cloud_build(build=build)
        image_name_without_tag, _ = image_name.rsplit(":", 1)
        image_name_with_digest = f"{image_name_without_tag}@{image_digest}"
        return image_name_with_digest

    def _configure_cloud_build(
        self,
        image_name: str,
        cloud_build_context: str,
        build_options: Dict[str, Any],
    ) -> cloudbuild_v1.Build:
        """Configures the build to be run to generate the Docker image.

        Args:
            image_name: The name of the image to build.
            cloud_build_context: The path to the build context.
            build_options: Docker build options.

        Returns:
            The build to run.
        """
        url_parts = urlparse(cloud_build_context)
        bucket = url_parts.netloc
        object_path = url_parts.path.lstrip("/")
        logger.info(
            "Build context located in bucket `%s` and object path `%s`",
            bucket,
            object_path,
        )

        cloud_builder_image = self.config.cloud_builder_image
        cloud_builder_network_option = f"--network={self.config.network}"
        logger.info(
            "Using Cloud Builder image `%s` to run the steps in the build. "
            "Container will be attached to network using option `%s`.",
            cloud_builder_image,
            cloud_builder_network_option,
        )

        # Convert the docker_build_options dictionary to a list of strings
        docker_build_args = []
        for key, value in build_options.items():
            option = f"--{key}"
            if isinstance(value, list):
                for val in value:
                    docker_build_args.extend([option, val])
            elif value is not None and not isinstance(value, bool):
                docker_build_args.extend([option, value])
            elif value is not False:
                docker_build_args.extend([option])

        return cloudbuild_v1.Build(
            source=cloudbuild_v1.Source(
                storage_source=cloudbuild_v1.StorageSource(
                    bucket=bucket, object=object_path
                ),
            ),
            steps=[
                {
                    "name": cloud_builder_image,
                    "args": [
                        "build",
                        cloud_builder_network_option,
                        "-t",
                        image_name,
                        ".",
                        *docker_build_args,
                    ],
                },
                {
                    "name": cloud_builder_image,
                    "args": ["push", image_name],
                },
            ],
            images=[image_name],
            timeout=f"{self.config.build_timeout}s",
        )

    def _run_cloud_build(self, build: cloudbuild_v1.Build) -> str:
        """Executes the Cloud Build run to build the Docker image.

        Args:
            build: The build to run.

        Returns:
            The Docker image repo digest.

        Raises:
            RuntimeError: If the Cloud Build run has failed.
        """
        credentials, project_id = self._get_authentication()
        client = cloudbuild_v1.CloudBuildClient(credentials=credentials)

        operation = client.create_build(project_id=project_id, build=build)
        log_url = operation.metadata.build.log_url
        logger.info(
            "Running Cloud Build to build the Docker image. Cloud Build logs: `%s`",
            log_url,
        )

        result = operation.result(timeout=self.config.build_timeout)

        if result.status != cloudbuild_v1.Build.Status.SUCCESS:
            raise RuntimeError(
                f"The Cloud Build run to build the Docker image has failed. More "
                f"information can be found in the Cloud Build logs: {log_url}."
            )

        logger.info(
            f"The Docker image has been built successfully. More information can "
            f"be found in the Cloud Build logs: `{log_url}`."
        )

        image_digest: str = result.results.images[0].digest
        return image_digest
