#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""AWS Code Build image builder implementation."""

import time
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, cast
from urllib.parse import urlparse
from uuid import uuid4

import boto3

from zenml.enums import StackComponentType
from zenml.image_builders import BaseImageBuilder
from zenml.integrations.aws import (
    AWS_CONTAINER_REGISTRY_FLAVOR,
)
from zenml.integrations.aws.flavors import AWSImageBuilderConfig
from zenml.logger import get_logger
from zenml.stack import StackValidator
from zenml.utils.archivable import ArchiveType

if TYPE_CHECKING:
    from zenml.container_registries import BaseContainerRegistry
    from zenml.image_builders import BuildContext
    from zenml.stack import Stack

logger = get_logger(__name__)


class AWSImageBuilder(BaseImageBuilder):
    """AWS Code Build image builder implementation."""

    _code_build_client: Optional[Any] = None

    @property
    def config(self) -> AWSImageBuilderConfig:
        """The stack component configuration.

        Returns:
            The configuration.
        """
        return cast(AWSImageBuilderConfig, self._config)

    @property
    def is_building_locally(self) -> bool:
        """Whether the image builder builds the images on the client machine.

        Returns:
            True if the image builder builds locally, False otherwise.
        """
        return False

    @property
    def validator(self) -> Optional["StackValidator"]:
        """Validates the stack for the AWS Code Build Image Builder.

        The AWS Code Build Image Builder requires a container registry to
        push the image to and an S3 Artifact Store to upload the build context,
        so AWS Code Build can access it.

        Returns:
            Stack validator.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.flavor != "s3":
                return False, (
                    "The AWS Image Builder requires an S3 Artifact Store to "
                    "upload the build context, so AWS Code Build can access it."
                    "Please update your stack to include an S3 Artifact Store "
                    "and try again."
                )

            return True, ""

        return StackValidator(
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_validate_remote_components,
        )

    @property
    def code_build_client(self) -> Any:
        """The authenticated AWS Code Build client to use for interacting with AWS services.

        Returns:
            The authenticated AWS Code Build client.

        Raises:
            RuntimeError: If the AWS Code Build client cannot be created.
        """
        if (
            self._code_build_client is not None
            and self.connector_has_expired()
        ):
            self._code_build_client = None
        if self._code_build_client is not None:
            return self._code_build_client

        # Option 1: Service connector
        if connector := self.get_connector():
            boto_session = connector.connect()
            if not isinstance(boto_session, boto3.Session):
                raise RuntimeError(
                    f"Expected to receive a `boto3.Session` object from the "
                    f"linked connector, but got type `{type(boto_session)}`."
                )
        # Option 2: Implicit configuration
        else:
            boto_session = boto3.Session()

        self._code_build_client = boto_session.client("codebuild")
        return self._code_build_client

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
            RuntimeError: If no container registry is passed.
            RuntimeError: If the Cloud Build build fails.
        """
        if not container_registry:
            raise RuntimeError(
                "The AWS Image Builder requires a container registry to push "
                "the image to. Please provide one and try again."
            )

        logger.info("Using AWS Code Build to build image `%s`", image_name)
        cloud_build_context = self._upload_build_context(
            build_context=build_context,
            parent_path_directory_name=f"code-build-contexts/{str(self.id)}",
            archive_type=ArchiveType.ZIP,
        )

        url_parts = urlparse(cloud_build_context)
        bucket = url_parts.netloc
        object_path = url_parts.path.lstrip("/")
        logger.info(
            "Build context located in bucket `%s` and object path `%s`",
            bucket,
            object_path,
        )

        # Pass authentication credentials as environment variables, if
        # the container registry has credentials and if implicit authentication
        # is disabled
        environment_variables_override = []
        pre_build_commands = []
        if not self.config.implicit_container_registry_auth:
            credentials = container_registry.credentials
            if credentials:
                environment_variables_override = [
                    {
                        "name": "CONTAINER_REGISTRY_USERNAME",
                        "value": credentials[0],
                        "type": "PLAINTEXT",
                    },
                    {
                        "name": "CONTAINER_REGISTRY_PASSWORD",
                        "value": credentials[1],
                        "type": "PLAINTEXT",
                    },
                ]
                pre_build_commands = [
                    "echo Logging in to container registry",
                    'echo "$CONTAINER_REGISTRY_PASSWORD" | docker login --username "$CONTAINER_REGISTRY_USERNAME" --password-stdin '
                    f"{container_registry.config.uri}",
                ]
        elif container_registry.flavor == AWS_CONTAINER_REGISTRY_FLAVOR:
            pre_build_commands = [
                "echo Logging in to EKS",
                f"aws ecr get-login-password --region {self.code_build_client._client_config.region_name} | docker login --username AWS --password-stdin {container_registry.config.uri}",
            ]

        # Convert the docker_build_options dictionary to a list of strings
        docker_build_args = ""
        for key, value in docker_build_options.items():
            option = f"--{key}"
            if isinstance(value, list):
                for val in value:
                    docker_build_args += f"{option} {val} "
            elif value is not None and not isinstance(value, bool):
                docker_build_args += f"{option} {value} "
            elif value is not False:
                docker_build_args += f"{option} "

        pre_build_commands_str = "\n".join(
            [f"            - {command}" for command in pre_build_commands]
        )

        # Generate and use a unique tag for the Docker image. This is easier
        # than trying to parse the image digest from the Code Build logs.
        build_id = str(uuid4())
        # Replace the tag in the image name with the unique build ID
        repo_name = image_name.split(":")[0]
        alt_image_name = f"{repo_name}:{build_id}"

        buildspec = f"""
version: 0.2
phases:
    pre_build:
        commands:
{pre_build_commands_str}
    build:
        commands:
            - echo Build started on `date`
            - echo Building the Docker image...
            - docker build -t {image_name} . {docker_build_args}
            - echo Build completed on `date`
    post_build:
        commands:
            - echo Pushing the Docker image...
            - docker push {image_name}
            - docker tag {image_name} {alt_image_name}
            - docker push {alt_image_name}
            - echo Pushed the Docker image
artifacts:
    files:
        - '**/*'
"""

        # Override the build project with the parameters needed to run a
        # docker-in-docker build, as covered here: https://docs.aws.amazon.com/codebuild/latest/userguide/sample-docker-section.html
        response = self.code_build_client.start_build(
            projectName=self.config.code_build_project,
            environmentTypeOverride="LINUX_CONTAINER",
            imageOverride="bentolor/docker-dind-awscli",
            computeTypeOverride="BUILD_GENERAL1_SMALL",
            privilegedModeOverride=False,
            sourceTypeOverride="S3",
            sourceLocationOverride=f"{bucket}/{object_path}",
            buildspecOverride=buildspec,
            environmentVariablesOverride=environment_variables_override,
            # no artifacts
            artifactsOverride={"type": "NO_ARTIFACTS"},
        )

        logs_url = response["build"]["logs"]["deepLink"]

        logger.info(
            f"Running Code Build to build the Docker image. Cloud Build logs: `{logs_url}`",
        )

        # Wait for the build to complete
        code_build_id = response["build"]["id"]
        while True:
            build_status = self.code_build_client.batch_get_builds(
                ids=[code_build_id]
            )
            build = build_status["builds"][0]
            status = build["buildStatus"]
            if status in [
                "SUCCEEDED",
                "FAILED",
                "FAULT",
                "TIMED_OUT",
                "STOPPED",
            ]:
                break
            time.sleep(10)

        if status != "SUCCEEDED":
            raise RuntimeError(
                f"The Code Build run to build the Docker image has failed. More "
                f"information can be found in the Cloud Build logs: {logs_url}."
            )

        logger.info(
            f"The Docker image has been built successfully. More information can "
            f"be found in the Cloud Build logs: `{logs_url}`."
        )

        return alt_image_name
