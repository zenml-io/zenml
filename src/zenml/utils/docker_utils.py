#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import json
import os
from typing import AbstractSet, Any, Dict, Iterable, List, Optional, cast

import pkg_resources
from docker.client import DockerClient
from docker.utils import build as docker_build_utils

import zenml
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import ENV_ZENML_CONFIG_PATH
from zenml.io import fileio
from zenml.io.utils import read_file_contents_as_string
from zenml.logger import get_logger
from zenml.utils import string_utils

DEFAULT_BASE_IMAGE = f"zenmldocker/zenml:{zenml.__version__}"
CONTAINER_ZENML_CONFIG_DIR = ".zenconfig"

logger = get_logger(__name__)


def _parse_dockerignore(dockerignore_path: str) -> List[str]:
    """Parses a dockerignore file and returns a list of patterns to ignore."""
    try:
        file_content = read_file_contents_as_string(dockerignore_path)
    except FileNotFoundError:
        logger.warning(
            "Unable to find dockerignore file at path '%s'.", dockerignore_path
        )
        return []

    exclude_patterns = []
    for line in file_content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            exclude_patterns.append(line)

    return exclude_patterns


def generate_dockerfile_contents(
    base_image: str,
    entrypoint: Optional[str] = None,
    requirements: Optional[AbstractSet[str]] = None,
    environment_vars: Optional[Dict[str, str]] = None,
) -> str:
    """Generates a Dockerfile.

    Args:
        base_image: The image to use as base for the dockerfile.
        entrypoint: The default entrypoint command that gets executed when
            running a container of an image created by this dockerfile.
        requirements: Optional list of pip requirements to install.
        environment_vars: Optional dict of environment variables to set.

    Returns:
        Content of a dockerfile.
    """
    lines = [f"FROM {base_image}", "WORKDIR /app"]

    # TODO [ENG-781]: Make secrets invisible in the Dockerfile or use a different approach.
    if environment_vars:
        for key, value in environment_vars.items():
            lines.append(f"ENV {key.upper()}={value}")

    if requirements:
        lines.append(
            f"RUN pip install --no-cache {' '.join(sorted(requirements))}"
        )

    lines.append("COPY . .")
    lines.append("RUN chmod -R a+rw .")
    lines.append(
        f"ENV {ENV_ZENML_CONFIG_PATH}=/app/{CONTAINER_ZENML_CONFIG_DIR}"
    )

    if entrypoint:
        lines.append(f"ENTRYPOINT {entrypoint}")

    return "\n".join(lines)


def create_custom_build_context(
    build_context_path: str,
    dockerfile_contents: str,
    dockerignore_path: Optional[str] = None,
) -> Any:
    """Creates a docker build context.

    Args:
        build_context_path: Path to a directory that will be sent to the
            docker daemon as build context.
        dockerfile_contents: File contents of the Dockerfile to use for the
            build.
        dockerignore_path: Optional path to a dockerignore file. If no value is
            given, the .dockerignore in the root of the build context will be
            used if it exists. Otherwise, all files inside `build_context_path`
            are included in the build context.

    Returns:
        Docker build context that can be passed when building a docker image.
    """
    exclude_patterns = []
    default_dockerignore_path = os.path.join(
        build_context_path, ".dockerignore"
    )
    if dockerignore_path:
        exclude_patterns = _parse_dockerignore(dockerignore_path)
    elif fileio.exists(default_dockerignore_path):
        logger.info(
            "Using dockerignore found at path '%s' to create docker "
            "build context.",
            default_dockerignore_path,
        )
        exclude_patterns = _parse_dockerignore(default_dockerignore_path)
    else:
        logger.info(
            "No explicit dockerignore specified and no file called "
            ".dockerignore exists at the build context root (%s). "
            "Creating docker build context with all files inside the build "
            "context root directory.",
            build_context_path,
        )

    logger.debug(
        "Exclude patterns for creating docker build context: %s",
        exclude_patterns,
    )
    no_ignores_found = not exclude_patterns

    files = docker_build_utils.exclude_paths(
        build_context_path, patterns=exclude_patterns
    )
    extra_files = [("Dockerfile", dockerfile_contents)]
    context = docker_build_utils.create_archive(
        root=build_context_path,
        files=sorted(files),
        gzip=False,
        extra_files=extra_files,
    )

    build_context_size = os.path.getsize(context.name)
    if build_context_size > 50 * 1024 * 1024 and no_ignores_found:
        # The build context exceeds 50MiB and we didn't find any excludes
        # in dockerignore files -> remind to specify a .dockerignore file
        logger.warning(
            "Build context size for docker image: %s. If you believe this is "
            "unreasonably large, make sure to include a .dockerignore file at "
            "the root of your build context (%s) or specify a custom file "
            "when defining your pipeline.",
            string_utils.get_human_readable_filesize(build_context_size),
            default_dockerignore_path,
        )

    return context


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
    entrypoint: Optional[str] = None,
    dockerfile_path: Optional[str] = None,
    dockerignore_path: Optional[str] = None,
    requirements: Optional[AbstractSet[str]] = None,
    environment_vars: Optional[Dict[str, str]] = None,
    use_local_requirements: bool = False,
    base_image: Optional[str] = None,
) -> None:
    """Builds a docker image.

    Args:
        build_context_path: Path to a directory that will be sent to the
            docker daemon as build context.
        image_name: The name to use for the created docker image.
        entrypoint: Optional entrypoint command that gets executed when running
            a container of the built image.
        dockerfile_path: Optional path to a dockerfile. If no value is given,
            a temporary dockerfile will be created.
        dockerignore_path: Optional path to a dockerignore file. If no value is
            given, the .dockerignore in the root of the build context will be
            used if it exists. Otherwise, all files inside `build_context_path`
            are included in the build context.
        requirements: Optional list of pip requirements to install. This
            will only be used if no value is given for `dockerfile_path`.
        environment_vars: Optional dict of key value pairs that need to be
            embedded as environment variables in the image.
        use_local_requirements: If `True` and no values are given for
            `dockerfile_path` and `requirements`, then the packages installed
            in the environment of the current python processed will be
            installed in the docker image.
        base_image: The image to use as base for the docker image.
    """
    config_path = os.path.join(build_context_path, CONTAINER_ZENML_CONFIG_DIR)
    try:

        # Save a copy of the current global configuration with the
        # active profile and the active stack configuration into the build
        # context, to have the active profile and active stack accessible from
        # within the container.
        GlobalConfiguration().copy_active_configuration(
            config_path,
            load_config_path=f"/app/{CONTAINER_ZENML_CONFIG_DIR}",
        )

        if not requirements and use_local_requirements:
            local_requirements = get_current_environment_requirements()
            requirements = {
                f"{package}=={version}"
                for package, version in local_requirements.items()
                if package != "zenml"  # exclude ZenML
            }
            logger.info(
                "Using requirements from local environment to build "
                "docker image: %s",
                requirements,
            )

        if dockerfile_path:
            dockerfile_contents = read_file_contents_as_string(dockerfile_path)
        else:
            dockerfile_contents = generate_dockerfile_contents(
                base_image=base_image or DEFAULT_BASE_IMAGE,
                entrypoint=entrypoint,
                requirements=requirements,
                environment_vars=environment_vars,
            )

        build_context = create_custom_build_context(
            build_context_path=build_context_path,
            dockerfile_contents=dockerfile_contents,
            dockerignore_path=dockerignore_path,
        )
        # If a custom base image is provided, make sure to always pull the
        # latest version of that image (if it isn't a locally built image).
        # If no base image is provided, we use the static default ZenML image so
        # there is no need to constantly pull
        pull_base_image = False
        if base_image:
            pull_base_image = not is_local_image(base_image)

        logger.info(
            "Building docker image '%s', this might take a while...",
            image_name,
        )

        docker_client = DockerClient.from_env()
        # We use the client api directly here, so we can stream the logs
        output_stream = docker_client.images.client.api.build(
            fileobj=build_context,
            custom_context=True,
            tag=image_name,
            pull=pull_base_image,
            rm=False,  # don't remove intermediate containers
        )
        _process_stream(output_stream)
    finally:
        # Clean up the temporary build files
        fileio.rmtree(config_path)

    logger.info("Finished building docker image.")


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


def is_local_image(image_name: str) -> bool:
    """Returns whether an image was pulled from a registry or not."""
    docker_client = DockerClient.from_env()
    images = docker_client.images.list(name=image_name)
    if images:
        # An image with this name is available locally -> now check whether it
        # was pulled from a repo or built locally (in which case the repo
        # digest is empty)
        return get_image_digest(image_name) is None
    else:
        # no image with this name found locally
        return False


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
                    raise RuntimeError(f"Docker error: {line_json['error']}.")
                elif "stream" in line_json:
                    logger.info(line_json["stream"].strip())
                else:
                    pass
            except json.JSONDecodeError as error:
                logger.warning(
                    "Failed to decode json for line '%s': %s", line, error
                )
