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
import re
from typing import ClassVar, List, Optional

import boto3
from botocore.exceptions import ClientError
from pydantic import validator

from zenml.container_registries.base_container_registry import (
    BaseContainerRegistry,
)
from zenml.integrations.aws import AWS_CONTAINER_REGISTRY_FLAVOR
from zenml.logger import get_logger

logger = get_logger(__name__)


class AWSContainerRegistry(BaseContainerRegistry):
    """Class for AWS Container Registry."""

    # Class Configuration
    FLAVOR: ClassVar[str] = AWS_CONTAINER_REGISTRY_FLAVOR

    @validator("uri")
    def validate_aws_uri(cls, uri: str) -> str:
        """Validates that the URI is in the correct format."""
        if "/" in uri:
            raise ValueError(
                "Property `uri` can not contain a `/`. An example of a valid "
                "URI is: `715803424592.dkr.ecr.us-east-1.amazonaws.com`"
            )

        return uri

    def prepare_image_push(self, image_name: str) -> None:
        """Logs a warning message if trying to push an image for which no
        repository exists.

        Args:
            image_name: Name of the docker image that will be pushed.

        Raises:
            ValueError: If the docker image name is invalid.
        """
        response = boto3.client("ecr").describe_repositories()
        try:
            repo_uris: List[str] = [
                repository["repositoryUri"]
                for repository in response["repositories"]
            ]
        except (KeyError, ClientError) as e:
            # invalid boto response, let's hope for the best and just push
            logger.debug("Error while trying to fetch ECR repositories: %s", e)
            return

        repo_exists = any(image_name.startswith(f"{uri}:") for uri in repo_uris)
        if not repo_exists:
            match = re.search(f"{self.uri}/(.*):.*", image_name)
            if not match:
                raise ValueError(f"Invalid docker image name '{image_name}'.")

            repo_name = match.group(1)
            logger.warning(
                "Amazon ECR requires you to create a repository before you can "
                f"push an image to it. ZenML is trying to push the image "
                f"{image_name} but could only detect the following "
                f"repositories: {repo_uris}. We will try to push anyway, but "
                f"in case it fails you need to create a repository named "
                f"`{repo_name}`."
            )

    @property
    def post_registration_message(self) -> Optional[str]:
        """Optional message that will be printed after the stack component is
        registered."""
        return (
            "Amazon ECR requires you to create a repository before you can "
            "push an image to it. If you want to for example run a pipeline "
            "using our Kubeflow orchestrator, ZenML will automatically build a "
            f"docker image called `{self.uri}/zenml-kubeflow:<PIPELINE_NAME>` "
            f"and try to push it. This will fail unless you create the "
            f"repository `zenml-kubeflow` inside your amazon registry."
        )
