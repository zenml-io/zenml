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
"""Utility functions relating to Docker."""

import json
import os
import re
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    cast,
)

from docker.client import DockerClient
from docker.utils import build as docker_build_utils

from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils, string_utils

logger = get_logger(__name__)


def check_docker() -> bool:
    """Checks if Docker is installed and running.

    Returns:
        `True` if Docker is installed, `False` otherwise.
    """
    # Try to ping Docker, to see if it's running
    try:
        docker_client = DockerClient.from_env()
        docker_client.ping()
        return True
    except Exception:
        logger.debug("Docker is not running.", exc_info=True)

    return False


def _parse_dockerignore(dockerignore_path: str) -> List[str]:
    """Parses a dockerignore file and returns a list of patterns to ignore.

    Args:
        dockerignore_path: Path to the dockerignore file.

    Returns:
        List of patterns to ignore.
    """
    try:
        file_content = io_utils.read_file_contents_as_string(dockerignore_path)
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


def _create_custom_build_context(
    dockerfile_contents: str,
    build_context_root: Optional[str] = None,
    dockerignore: Optional[str] = None,
    extra_files: Sequence[Tuple[str, str]] = (),
) -> Any:
    """Creates a docker build context.

    Args:
        build_context_root: Path to a directory that will be sent to the
            docker daemon as build context.
        dockerfile_contents: File contents of the Dockerfile to use for the
            build.
        dockerignore: Optional path to a dockerignore file. If no value is
            given, the .dockerignore in the root of the build context will be
            used if it exists. Otherwise, all files inside `build_context_root`
            are included in the build context.
        extra_files: Additional files to include in the build context. The
            files should be passed as a tuple
            (filepath_inside_build_context, file_content) and will overwrite
            existing files in the build context if they share the same path.

    Returns:
        Docker build context that can be passed when building a docker image.
    """
    if build_context_root:
        logger.info(
            "Creating Docker build context from directory `%s`.",
            os.path.abspath(build_context_root),
        )
        exclude_patterns = []
        default_dockerignore_path = os.path.join(
            build_context_root, ".dockerignore"
        )
        if dockerignore or fileio.exists(default_dockerignore_path):
            if not dockerignore:
                dockerignore = default_dockerignore_path
            logger.info(
                "Using dockerignore file `%s` to create docker build context.",
                dockerignore,
            )
            exclude_patterns = _parse_dockerignore(dockerignore)
        else:
            logger.info(
                "No `.dockerignore` found, including all files inside build "
                "context.",
            )

        logger.debug(
            "Exclude patterns for creating docker build context: %s",
            exclude_patterns,
        )
        no_ignores_found = not exclude_patterns

        files = docker_build_utils.exclude_paths(
            build_context_root, patterns=exclude_patterns
        )
    else:
        # No build context path given, we create a build context with only
        # the Dockerfile included
        logger.info(
            "No build context root specified, not including any files in the "
            "Docker build context."
        )
        no_ignores_found = False
        files = []

    extra_files = [*extra_files, ("Dockerfile", dockerfile_contents)]
    context = docker_build_utils.create_archive(
        root=build_context_root,
        files=sorted(files),
        gzip=False,
        extra_files=extra_files,
    )

    build_context_size = os.path.getsize(context.name)
    if build_context_size > 50 * 1024 * 1024 and no_ignores_found:
        # The build context exceeds 50MiB and we didn't find any excludes
        # in dockerignore files -> remind to specify a .dockerignore file
        logger.warning(
            "Build context size for docker image: `%s`. If you believe this is "
            "unreasonably large, make sure to include a `.dockerignore` file "
            "at the root of your build context `%s` or specify a custom file "
            "in the Docker configuration when defining your pipeline.",
            string_utils.get_human_readable_filesize(build_context_size),
            default_dockerignore_path,
        )

    return context


def build_image(
    image_name: str,
    dockerfile: Union[str, List[str]],
    build_context_root: Optional[str] = None,
    dockerignore: Optional[str] = None,
    extra_files: Sequence[Tuple[str, str]] = (),
    **custom_build_options: Any,
) -> None:
    """Builds a docker image.

    Args:
        image_name: The name to use for the built docker image.
        dockerfile: Path to a dockerfile or a list of strings representing the
            Dockerfile lines/commands.
        build_context_root: Optional path to a directory that will be sent to
            the Docker daemon as build context. If left empty, the Docker build
            context will be empty.
        dockerignore: Optional path to a dockerignore file. If no value is
            given, the .dockerignore in the root of the build context will be
            used if it exists. Otherwise, all files inside `build_context_root`
            are included in the build context.
        extra_files: Additional files to include in the build context. The
            files should be passed as a tuple
            (filepath_inside_build_context, file_content) and will overwrite
            existing files in the build context if they share the same path.
        **custom_build_options: Additional options that will be passed
            unmodified to the Docker build call when building the image. You
            can use this to for example specify build args or a target stage.
            See https://docker-py.readthedocs.io/en/stable/images.html#docker.models.images.ImageCollection.build
            for a full list of available options.
    """
    if isinstance(dockerfile, str):
        dockerfile_contents = io_utils.read_file_contents_as_string(dockerfile)
        logger.info("Using Dockerfile `%s`.", os.path.abspath(dockerfile))
    else:
        dockerfile_contents = "\n".join(dockerfile)

    build_context = _create_custom_build_context(
        dockerfile_contents=dockerfile_contents,
        build_context_root=build_context_root,
        dockerignore=dockerignore,
        extra_files=extra_files,
    )

    build_options = {
        "rm": False,  # don't remove intermediate containers to improve caching
        "pull": True,  # always pull parent images
        **custom_build_options,
    }

    logger.info("Building Docker image `%s`.", image_name)
    logger.debug("Docker build options: %s", build_options)

    logger.info("Building the image might take a while...")

    docker_client = DockerClient.from_env()
    # We use the client api directly here, so we can stream the logs
    output_stream = docker_client.images.client.api.build(
        fileobj=build_context,
        custom_context=True,
        tag=image_name,
        **build_options,
    )
    _process_stream(output_stream)

    logger.info("Finished building Docker image `%s`.", image_name)


def push_image(
    image_name: str, docker_client: Optional[DockerClient] = None
) -> str:
    """Pushes an image to a container registry.

    Args:
        image_name: The full name (including a tag) of the image to push.
        docker_client: Optional Docker client to use for pushing the image. If
            no client is given, a new client will be created using the default
            Docker environment.

    Returns:
        The Docker repository digest of the pushed image.

    Raises:
        RuntimeError: If fetching the repository digest of the image failed.
    """
    logger.info("Pushing Docker image `%s`.", image_name)
    docker_client = docker_client or DockerClient.from_env()
    output_stream = docker_client.images.push(image_name, stream=True)
    aux_info = _process_stream(output_stream)
    logger.info("Finished pushing Docker image.")

    image_name_without_tag, _ = image_name.rsplit(":", maxsplit=1)
    for info in reversed(aux_info):
        try:
            repo_digest = info["Digest"]
            return f"{image_name_without_tag}@{repo_digest}"
        except KeyError:
            pass
    else:
        raise RuntimeError(
            f"Unable to find repo digest after pushing image {image_name}."
        )


def tag_image(image_name: str, target: str) -> None:
    """Tags an image.

    Args:
        image_name: The name of the image to tag.
        target: The full target name including a tag.
    """
    docker_client = DockerClient.from_env()
    image = docker_client.images.get(image_name)
    image.tag(target)


def get_image_digest(image_name: str) -> Optional[str]:
    """Gets the digest of an image.

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
    """Returns whether an image was pulled from a registry or not.

    Args:
        image_name: Name of the image to check.

    Returns:
        `True` if the image was pulled from a registry, `False` otherwise.
    """
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


def _process_stream(stream: Iterable[bytes]) -> List[Dict[str, Any]]:
    """Processes the output stream of a docker command call.

    Args:
        stream: The output stream of a docker command call.

    Raises:
        RuntimeError: If there was an error while running the docker command.

    Returns:
        Auxiliary information which was part of the stream.
    """
    auxiliary_info = []

    for element in stream:
        lines = element.decode("utf-8").strip().split("\n")

        for line in lines:
            try:
                line_json = json.loads(line)
                if "error" in line_json:
                    raise RuntimeError(f"Docker error: {line_json['error']}.")
                elif "stream" in line_json:
                    text = line_json["stream"].strip()
                    if "ERROR" in text:
                        logger.error(text)
                    elif re.match(r"^Step [0-9]+/[0-9]+", text):
                        logger.info(text)
                    else:
                        logger.debug(text)
                elif "aux" in line_json:
                    auxiliary_info.append(line_json["aux"])
                else:
                    pass
            except json.JSONDecodeError as error:
                logger.warning(
                    "Failed to decode json for line '%s': %s", line, error
                )

    return auxiliary_info
