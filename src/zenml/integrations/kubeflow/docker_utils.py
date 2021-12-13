#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import json
import os
import tempfile
from typing import Dict, Iterable, List, Optional, cast

import pkg_resources
from docker.client import DockerClient

import zenml
from zenml.logger import get_logger

DEFAULT_BASE_IMAGE = f"zenmldocker/zenml:{zenml.__version__}"

logger = get_logger(__name__)


def create_dockerfile(
    base_image: str,
    command: Optional[str] = None,
    requirements: Optional[List[str]] = None,
    output_path: Optional[str] = None,
) -> str:
    """Creates a dockerfile.

    Args:
        base_image: The image to use as base for the dockerfile.
        command: The default command that gets executed when running a
            container of an image created by this dockerfile.
        requirements: Optional list of pip requirements to install.
        output_path: Path where the dockerfile should be written to.
            If this is not set, a filepath inside the temp directory will be
            used instead. **IMPORTANT**: Whoever uses this function is
            responsible for removing the created dockerfile.

    Returns:
        A path to the dockerfile.
    """
    lines = [f"FROM {base_image}", "WORKDIR /app"]

    if requirements:
        lines.extend(
            [
                f"RUN pip install --no-cache {' '.join(requirements)}",
            ]
        )

    lines.append("COPY . .")

    if command:
        lines.append(f"CMD {command}")

    if not output_path:
        _, output_path = tempfile.mkstemp()

    logger.debug("Writing dockerfile to path '%s'", output_path)
    with open(output_path, "w") as output_file:
        output_file.write("\n".join(lines))

    return output_path


def get_current_environment_requirements() -> Dict[str, str]:
    """Returns a dict of package requirements for the environment that
    the current python process is running in."""
    return {
        distribution.key: distribution.version
        for distribution in pkg_resources.working_set
    }


def build_docker_image(
    build_context_path: str,
    image_name: str,
    dockerfile_path: Optional[str] = None,
    requirements: Optional[List[str]] = None,
    use_local_requirements: bool = False,
    base_image: Optional[str] = None,
) -> None:
    """Builds a docker image.

    Args:
        build_context_path: Path to a directory that will be sent to the
            docker daemon as build context.
        image_name: The name to use for the created docker image.
        dockerfile_path: Optional path to a dockerfile. If no value is given,
            a temporary dockerfile will be created.
        requirements: Optional list of pip requirements to install. This
            will only be used if no value is given for `dockerfile_path`.
        use_local_requirements: If `True` and no values are given for
            `dockerfile_path` and `requirements`, then the packages installed
            in the environment of the current python processed will be
            installed in the docker image.
        base_image: The image to use as base for the docker image.
    """
    if not requirements and use_local_requirements:
        local_requirements = get_current_environment_requirements()
        requirements = [
            f"{package}=={version}"
            for package, version in local_requirements.items()
            if package != "zenml"  # exclude ZenML
        ]
        logger.info(
            "Using requirements from local environment to build "
            "docker image: %s",
            requirements,
        )

    temporary_dockerfile = not dockerfile_path
    if not dockerfile_path:
        dockerfile_path = create_dockerfile(
            requirements=requirements,
            base_image=base_image or DEFAULT_BASE_IMAGE,
        )

    logger.info(
        "Building docker image '%s', this might take a while...", image_name
    )
    try:
        docker_client = DockerClient.from_env()
        # We use the client api directly here so we can stream the logs
        output_stream = docker_client.images.client.api.build(
            path=build_context_path,
            dockerfile=dockerfile_path,
            tag=image_name,
            pull=True,  # pull changes to base image
            rm=True,  # remove intermediate containers
        )
        _process_stream(output_stream)
        logger.info("Finished building docker image.")
    finally:
        if temporary_dockerfile:
            logger.debug("Removing temporary dockerfile '%s'", dockerfile_path)
            os.remove(dockerfile_path)


def push_docker_image(image_name: str) -> None:
    """Pushes a docker image to a container registry.

    Args:
        image_name: The full name (including a tag) of the image to push.
    """
    logger.info("Pushing docker image '%s'.", image_name)
    docker_client = DockerClient.from_env()
    output_stream = docker_client.images.push(image_name, stream=True)
    _process_stream(output_stream)
    logger.info("Finished pushing docker image.")


def get_image_digest(image_name: str) -> Optional[str]:
    """Gets the digest of a docker image.

    Args:
        image_name: Name of the image to get the digest for.

    Returns:
        Returns the repo digest for the given image if there exists exactly one.
        If there are zero or multiple repo digests, returns `None`.
    """
    docker_client = DockerClient.from_env()
    image = docker_client.images.get(image_name)
    repo_digests = image.attrs["RepoDigests"]
    if len(repo_digests) == 1:
        return cast(str, repo_digests[0])
    else:
        logger.debug(
            "Found zero or more repo digests for docker image '%s': %s",
            image_name,
            repo_digests,
        )
        return None


def _process_stream(stream: Iterable[bytes]) -> None:
    """Processes the output stream of a docker command call.

    Raises:
        JSONDecodeError: If a line in the stream is not json decodable.
        RuntimeError: If there was an error while running the docker command.
    """

    for element in stream:
        lines = element.decode("utf-8").strip().split("\n")

        for line in lines:
            try:
                line_json = json.loads(line)
                if "error" in line_json:
                    raise RuntimeError(
                        f"Failed to build docker image: {line_json['error']}."
                    )
                elif "stream" in line_json:
                    logger.info(line_json["stream"].strip())
                else:
                    pass
            except json.JSONDecodeError as error:
                logger.warning(
                    "Failed to decode json for line '%s': %s", line, error
                )
