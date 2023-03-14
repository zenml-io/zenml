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
"""Implementation of Docker image builds to run ZenML pipelines."""
import itertools
import os
import subprocess
import sys
import tempfile
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple

import zenml
from zenml.config import DockerSettings
from zenml.config.docker_settings import PythonEnvironmentExportMethod
from zenml.config.global_config import GlobalConfiguration
from zenml.constants import (
    ENV_ZENML_CONFIG_PATH,
    ENV_ZENML_ENABLE_REPO_INIT_WARNINGS,
)
from zenml.enums import OperatingSystemType
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.utils import docker_utils, io_utils, source_utils

if TYPE_CHECKING:
    from zenml.container_registries import BaseContainerRegistry
    from zenml.image_builders import BuildContext
    from zenml.stack import Stack

logger = get_logger(__name__)

DOCKER_IMAGE_WORKDIR = "/app"
DOCKER_IMAGE_ZENML_CONFIG_DIR = ".zenconfig"
DOCKER_IMAGE_ZENML_CONFIG_PATH = (
    f"{DOCKER_IMAGE_WORKDIR}/{DOCKER_IMAGE_ZENML_CONFIG_DIR}"
)

DEFAULT_DOCKER_PARENT_IMAGE = (
    f"zenmldocker/zenml:{zenml.__version__}-"
    f"py{sys.version_info.major}.{sys.version_info.minor}"
)


class PipelineDockerImageBuilder:
    """Builds Docker images to run a ZenML pipeline."""

    def build_docker_image(
        self,
        docker_settings: "DockerSettings",
        tag: str,
        stack: "Stack",
        entrypoint: Optional[str] = None,
        extra_files: Optional[Dict[str, str]] = None,
    ) -> str:
        """Builds (and optionally pushes) a Docker image to run a pipeline.

        Use the image name returned by this method whenever you need to uniquely
        reference the pushed image in order to pull or run it.

        Args:
            docker_settings: The settings for the image build.
            tag: The tag to use for the image.
            stack: The stack on which the pipeline will be deployed.
            entrypoint: Entrypoint to use for the final image. If left empty,
                no entrypoint will be included in the image.
            extra_files: Extra files to add to the build context. Keys are the
                path inside the build context, values are either the file
                content or a file path.

        Returns:
            The Docker image repo digest or local name, depending on whether
            the image was pushed or is just stored locally.

        Raises:
            RuntimeError: If the stack does not contain an image builder.
            ValueError: If no Dockerfile and/or custom parent image is
                specified and the Docker configuration doesn't require an
                image build.
        """
        if docker_settings.skip_build:
            assert (
                docker_settings.parent_image
            )  # checked via validator already

            # Should we tag this here and push it to the container registry of
            # the stack to make sure it's always accessible when running the
            # pipeline?
            return docker_settings.parent_image

        image_builder = stack.image_builder
        if not image_builder:
            raise RuntimeError(
                "Unable to build Docker images without an image builder in the "
                f"stack `{stack.name}`."
            )

        container_registry = stack.container_registry

        build_context_class = image_builder.build_context_class
        target_image_name = self._get_target_image_name(
            docker_settings=docker_settings,
            tag=tag,
            container_registry=container_registry,
        )

        requires_zenml_build = any(
            [
                docker_settings.requirements,
                docker_settings.required_integrations,
                docker_settings.replicate_local_python_environment,
                docker_settings.install_stack_requirements,
                docker_settings.apt_packages,
                docker_settings.environment,
                docker_settings.copy_files,
                docker_settings.copy_global_config,
                entrypoint,
                extra_files,
            ]
        )

        # Fallback to the value defined on the stack component if the
        # pipeline configuration doesn't have a configured value
        parent_image = (
            docker_settings.parent_image or DEFAULT_DOCKER_PARENT_IMAGE
        )

        if docker_settings.dockerfile:
            if parent_image != DEFAULT_DOCKER_PARENT_IMAGE:
                logger.warning(
                    "You've specified both a Dockerfile and a custom parent "
                    "image, ignoring the parent image."
                )

            push = (
                not image_builder.is_building_locally
                or not requires_zenml_build
            )

            if requires_zenml_build:
                # We will build an additional image on top of this one later
                # to include user files and/or install requirements. The image
                # we build now will be used as the parent for the next build.
                user_image_name = (
                    f"{docker_settings.target_repository}:"
                    f"{tag}-intermediate-build"
                )
                if push and container_registry:
                    user_image_name = (
                        f"{container_registry.config.uri}/{user_image_name}"
                    )

                parent_image = user_image_name
            else:
                # The image we'll build from the custom Dockerfile will be
                # used directly, so we tag it with the requested target name.
                user_image_name = target_image_name

            build_context = build_context_class(
                root=docker_settings.build_context_root
            )
            build_context.add_file(
                source=docker_settings.dockerfile, destination="Dockerfile"
            )
            logger.info("Building Docker image `%s`.", user_image_name)
            image_name_or_digest = image_builder.build(
                image_name=user_image_name,
                build_context=build_context,
                docker_build_options=docker_settings.build_options,
                container_registry=container_registry if push else None,
            )

        elif not requires_zenml_build:
            if parent_image == DEFAULT_DOCKER_PARENT_IMAGE:
                raise ValueError(
                    "Unable to run a ZenML pipeline with the given Docker "
                    "settings: No Dockerfile or custom parent image "
                    "specified and no files will be copied or requirements "
                    "installed."
                )
            else:
                # The parent image will be used directly to run the pipeline and
                # needs to be tagged/pushed
                docker_utils.tag_image(parent_image, target=target_image_name)
                if container_registry:
                    image_name_or_digest = container_registry.push_image(
                        target_image_name
                    )
                else:
                    image_name_or_digest = target_image_name

        if requires_zenml_build:
            logger.info("Building Docker image `%s`.", target_image_name)
            # Leave the build context empty if we don't want to copy any files
            build_context_root = (
                source_utils.get_source_root_path()
                if docker_settings.copy_files
                else None
            )
            build_context = build_context_class(
                root=build_context_root,
                dockerignore_file=docker_settings.dockerignore,
            )

            requirements_file_names = self._add_requirements_files(
                docker_settings=docker_settings,
                build_context=build_context,
                stack=stack,
            )

            apt_packages = docker_settings.apt_packages
            if docker_settings.install_stack_requirements:
                apt_packages += stack.apt_packages

            if apt_packages:
                logger.info(
                    "Including apt packages: %s",
                    ", ".join(f"`{p}`" for p in apt_packages),
                )

            if parent_image == DEFAULT_DOCKER_PARENT_IMAGE:
                # The default parent image is static and doesn't require a pull
                # each time
                pull_parent_image = False
            elif docker_settings.dockerfile and not container_registry:
                # We built a custom parent image and there was no container
                # registry in the stack to push to, this is a local image
                pull_parent_image = False
            elif not image_builder.is_building_locally:
                # Remote image builders always need to pull the image
                pull_parent_image = True
            else:
                # If the image is local, we don't need to pull it. Otherwise
                # we play it safe and always pull in case the user pushed a new
                # image for the given name and tag
                pull_parent_image = not docker_utils.is_local_image(
                    parent_image
                )

            build_options = {"pull": pull_parent_image, "rm": False}

            dockerfile = self._generate_zenml_pipeline_dockerfile(
                parent_image=parent_image,
                docker_settings=docker_settings,
                requirements_files=requirements_file_names,
                apt_packages=apt_packages,
                entrypoint=entrypoint,
            )
            build_context.add_file(destination="Dockerfile", source=dockerfile)

            if docker_settings.copy_global_config:
                with tempfile.TemporaryDirectory() as tmpdir:
                    GlobalConfiguration().copy_configuration(
                        tmpdir,
                        load_config_path=PurePosixPath(
                            DOCKER_IMAGE_ZENML_CONFIG_PATH
                        ),
                    )
                    build_context.add_directory(
                        source=tmpdir,
                        destination=DOCKER_IMAGE_ZENML_CONFIG_DIR,
                    )

            if extra_files:
                for destination, source in extra_files.items():
                    build_context.add_file(
                        destination=destination, source=source
                    )

            image_name_or_digest = image_builder.build(
                image_name=target_image_name,
                build_context=build_context,
                docker_build_options=build_options,
                container_registry=container_registry,
            )

        return image_name_or_digest

    @staticmethod
    def _get_target_image_name(
        docker_settings: "DockerSettings",
        tag: str,
        container_registry: Optional["BaseContainerRegistry"] = None,
    ) -> str:
        """Returns the target image name.

        If a container registry is given, the image name will include the
        registry URI

        Args:
            docker_settings: The settings for the image build.
            tag: The tag to use for the image.
            container_registry: Optional container registry to which this
                image will be pushed.

        Returns:
            The docker image name.
        """
        target_image_name = f"{docker_settings.target_repository}:{tag}"
        if container_registry:
            target_image_name = (
                f"{container_registry.config.uri}/{target_image_name}"
            )

        return target_image_name

    @classmethod
    def _add_requirements_files(
        cls,
        docker_settings: DockerSettings,
        build_context: "BuildContext",
        stack: "Stack",
    ) -> List[str]:
        """Adds requirements files to the build context.

        Args:
            docker_settings: Docker settings that specifies which
                requirements to install.
            build_context: Build context to add the requirements files to.
            stack: The stack on which the pipeline will run.

        Returns:
            Name of the requirements files in the build context.
            The files will be in the following order:
            - Packages installed in the local Python environment
            - User-defined requirements
            - Requirements defined by user-defined and/or stack integrations
        """
        requirements_file_names = []
        requirements_files = cls._gather_requirements_files(
            docker_settings=docker_settings, stack=stack
        )
        for filename, file_content in requirements_files:
            build_context.add_file(source=file_content, destination=filename)
            requirements_file_names.append(filename)

        return requirements_file_names

    @staticmethod
    def _gather_requirements_files(
        docker_settings: DockerSettings, stack: "Stack", log: bool = True
    ) -> List[Tuple[str, str]]:
        """Gathers and/or generates pip requirements files.

        Args:
            docker_settings: Docker settings that specifies which
                requirements to install.
            stack: The stack on which the pipeline will run.
            log: If `True`, will log the requirements.

        Raises:
            RuntimeError: If the command to export the local python packages
                failed.

        Returns:
            List of tuples (filename, file_content) of all requirements files.
            The files will be in the following order:
            - Packages installed in the local Python environment
            - User-defined requirements
            - Requirements defined by user-defined and/or stack integrations
        """
        requirements_files = []

        # Generate requirements file for the local environment if configured
        if docker_settings.replicate_local_python_environment:
            if isinstance(
                docker_settings.replicate_local_python_environment,
                PythonEnvironmentExportMethod,
            ):
                command = (
                    docker_settings.replicate_local_python_environment.command
                )
            else:
                command = " ".join(
                    docker_settings.replicate_local_python_environment
                )

            try:
                local_requirements = subprocess.check_output(
                    command, shell=True
                ).decode()
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    "Unable to export local python packages."
                ) from e

            requirements_files.append(
                (".zenml_local_requirements", local_requirements)
            )
            if log:
                logger.info(
                    "- Including python packages from local environment"
                )

        # Generate/Read requirements file for user-defined requirements
        if isinstance(docker_settings.requirements, str):
            user_requirements = io_utils.read_file_contents_as_string(
                docker_settings.requirements
            )
            if log:
                logger.info(
                    "- Including user-defined requirements from file `%s`",
                    os.path.abspath(docker_settings.requirements),
                )
        elif isinstance(docker_settings.requirements, List):
            user_requirements = "\n".join(docker_settings.requirements)
            if log:
                logger.info(
                    "- Including user-defined requirements: %s",
                    ", ".join(f"`{r}`" for r in docker_settings.requirements),
                )
        else:
            user_requirements = None

        if user_requirements:
            requirements_files.append(
                (".zenml_user_requirements", user_requirements)
            )

        # Generate requirements file for all required integrations
        integration_requirements = set(
            itertools.chain.from_iterable(
                integration_registry.select_integration_requirements(
                    integration_name=integration,
                    target_os=OperatingSystemType.LINUX,
                )
                for integration in docker_settings.required_integrations
            )
        )

        if docker_settings.install_stack_requirements:
            integration_requirements.update(stack.requirements())

        if integration_requirements:
            integration_requirements_list = sorted(integration_requirements)
            integration_requirements_file = "\n".join(
                integration_requirements_list
            )
            requirements_files.append(
                (
                    ".zenml_integration_requirements",
                    integration_requirements_file,
                )
            )
            if log:
                logger.info(
                    "- Including integration requirements: %s",
                    ", ".join(f"`{r}`" for r in integration_requirements_list),
                )

        return requirements_files

    @staticmethod
    def _generate_zenml_pipeline_dockerfile(
        parent_image: str,
        docker_settings: DockerSettings,
        requirements_files: Sequence[str] = (),
        apt_packages: Sequence[str] = (),
        entrypoint: Optional[str] = None,
    ) -> str:
        """Generates a Dockerfile.

        Args:
            parent_image: The image to use as parent for the Dockerfile.
            docker_settings: Docker settings for this image build.
            requirements_files: Paths of requirements files to install.
            apt_packages: APT packages to install.
            entrypoint: The default entrypoint command that gets executed when
                running a container of an image created by this Dockerfile.

        Returns:
            The generated Dockerfile.
        """
        lines = [f"FROM {parent_image}", f"WORKDIR {DOCKER_IMAGE_WORKDIR}"]

        if apt_packages:
            apt_packages = " ".join(f"'{p}'" for p in apt_packages)

            lines.append(
                "RUN apt-get update && apt-get install -y "
                f"--no-install-recommends {apt_packages}"
            )

        for file in requirements_files:
            lines.append(f"COPY {file} .")
            lines.append(
                f"RUN pip install --default-timeout=60 --no-cache-dir -r {file}"
            )

        lines.append(f"ENV {ENV_ZENML_ENABLE_REPO_INIT_WARNINGS}=False")
        if docker_settings.copy_global_config:
            lines.append(
                f"ENV {ENV_ZENML_CONFIG_PATH}={DOCKER_IMAGE_ZENML_CONFIG_PATH}"
            )

        for key, value in docker_settings.environment.items():
            lines.append(f"ENV {key.upper()}={value}")

        if docker_settings.copy_files:
            lines.append("COPY . .")
        elif docker_settings.copy_global_config:
            lines.append(f"COPY {DOCKER_IMAGE_ZENML_CONFIG_DIR} .")

        lines.append("RUN chmod -R a+rw .")

        if docker_settings.user:
            lines.append(f"USER {docker_settings.user}")
            lines.append(f"RUN chown -R {docker_settings.user} .")

        if entrypoint:
            lines.append(f"ENTRYPOINT {entrypoint}")

        return "\n".join(lines)
