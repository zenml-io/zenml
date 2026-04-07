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

import os
from typing import Any, List, Optional, Sequence, Tuple, Union, cast

from docker.utils import build as docker_build_utils

from zenml.container_engines import (
    ContainerEngine,
    DockerContainerEngine,
    get_container_engine,
)
from zenml.enums import ContainerEngineType
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import io_utils, string_utils

logger = get_logger(__name__)


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
            exclude_patterns = ContainerEngine.parse_dockerignore(dockerignore)
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

    docker_engine = get_container_engine(ContainerEngineType.DOCKER)
    docker_client = cast(DockerContainerEngine, docker_engine).client

    output_stream = docker_client.images.client.api.build(
        fileobj=build_context,
        custom_context=True,
        tag=image_name,
        **build_options,
    )
    DockerContainerEngine.process_docker_stream(output_stream)

    logger.info("Finished building Docker image `%s`.", image_name)


__all__ = [
    "build_image",
]
