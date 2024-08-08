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
"""Docker settings."""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from zenml.config.base_settings import BaseSettings
from zenml.logger import get_logger
from zenml.utils import deprecation_utils
from zenml.utils.pydantic_utils import before_validator_handler

logger = get_logger(__name__)


class PythonEnvironmentExportMethod(Enum):
    """Different methods to export the local Python environment."""

    PIP_FREEZE = "pip_freeze"
    POETRY_EXPORT = "poetry_export"

    @property
    def command(self) -> str:
        """Shell command that outputs local python packages.

        The output string must be something that can be interpreted as a
        requirements file for pip once it's written to a file.

        Returns:
            Shell command.
        """
        return {
            PythonEnvironmentExportMethod.PIP_FREEZE: "pip freeze",
            PythonEnvironmentExportMethod.POETRY_EXPORT: "poetry export --format=requirements.txt",
        }[self]


class PythonPackageInstaller(Enum):
    """Different installers for python packages."""

    PIP = "pip"
    UV = "uv"


class DockerBuildConfig(BaseModel):
    """Configuration for a Docker build.

    Attributes:
        build_options: Additional options that will be passed unmodified to the
            Docker build call when building an image. You can use this to for
            example specify build args or a target stage. See
            https://docker-py.readthedocs.io/en/stable/images.html#docker.models.images.ImageCollection.build
            for a full list of available options.
        dockerignore: Path to a dockerignore file to use when building the
            Docker image.
    """

    build_options: Dict[str, Any] = {}
    dockerignore: Optional[str] = None


class DockerSettings(BaseSettings):
    """Settings for building Docker images to run ZenML pipelines.

    Build process:
    --------------
    * No `dockerfile` specified: If any of the options regarding
    requirements, environment variables or copying files require us to build an
    image, ZenML will build this image. Otherwise, the `parent_image` will be
    used to run the pipeline.
    * `dockerfile` specified: ZenML will first build an image based on the
    specified Dockerfile. If any of the options regarding
    requirements, environment variables or copying files require an additional
    image built on top of that, ZenML will build a second image. If not, the
    image build from the specified Dockerfile will be used to run the pipeline.

    Requirements installation order:
    --------------------------------
    Depending on the configuration of this object, requirements will be
    installed in the following order (each step optional):
    - The packages installed in your local python environment
    - The packages required by the stack unless this is disabled by setting
      `install_stack_requirements=False`.
    - The packages specified via the `required_integrations`
    - The packages specified via the `requirements` attribute

    Attributes:
        parent_image: Full name of the Docker image that should be
            used as the parent for the image that will be built. Defaults to
            a ZenML image built for the active Python and ZenML version.

            Additional notes:
            * If you specify a custom image here, you need to make sure it has
            ZenML installed.
            * If this is a non-local image, the environment which is running
            the pipeline and building the Docker image needs to be able to pull
            this image.
            * If a custom `dockerfile` is specified for this settings
            object, this parent image will be ignored.
        dockerfile: Path to a custom Dockerfile that should be built. Depending
            on the other values you specify in this object, the resulting
            image will be used directly to run your pipeline or ZenML will use
            it as a parent image to build on top of. See the general docstring
            of this class for more information.

            Additional notes:
            * If you specify this, the `parent_image` attribute will be ignored.
            * If you specify this, the image built from this Dockerfile needs
            to have ZenML installed.
        build_context_root: Build context root for the Docker build, only used
            when the `dockerfile` attribute is set. If this is left empty, the
            build context will only contain the Dockerfile.
        parent_image_build_config: Configuration for the parent image build.
        skip_build: If set to `True`, the parent image will be used directly to
            run the steps of your pipeline.
        prevent_build_reuse: Prevent the reuse of an existing build.
        target_repository: Name of the Docker repository to which the
            image should be pushed. This repository will be appended to the
            registry URI of the container registry of your stack and should
            therefore **not** include any registry. If not specified, the
            default repository name configured in the container registry
            stack component settings will be used.
        python_package_installer: The package installer to use for python
            packages.
        python_package_installer_args: Arguments to pass to the python package
            installer.
        replicate_local_python_environment: If not `None`, ZenML will use the
            specified method to generate a requirements file that replicates
            the packages installed in the currently running python environment.
            This requirements file will then be installed in the Docker image.
        requirements: Path to a requirements file or a list of required pip
            packages. During the image build, these requirements will be
            installed using pip. If you need to use a different tool to
            resolve and/or install your packages, please use a custom parent
            image or specify a custom `dockerfile`.
        required_integrations: List of ZenML integrations that should be
            installed. All requirements for the specified integrations will
            be installed inside the Docker image.
        required_hub_plugins: DEPRECATED/UNUSED.
        install_stack_requirements: If `True`, ZenML will automatically detect
            if components of your active stack are part of a ZenML integration
            and install the corresponding requirements and apt packages.
            If you set this to `False` or use custom components in your stack,
            you need to make sure these get installed by specifying them in
            the `requirements` and `apt_packages` attributes.
        apt_packages: APT packages to install inside the Docker image.
        environment: Dictionary of environment variables to set inside the
            Docker image.
        build_config: Configuration for the main image build.
        user: If not `None`, will set the user, make it owner of the `/app`
            directory which contains all the user code and run the container
            entrypoint as this user.
        allow_including_files_in_images: If `True`, code can be included in the
            Docker images if code download from a code repository or artifact
            store is disabled or not possible.
        allow_download_from_code_repository: If `True`, code can be downloaded
            from a code repository if possible.
        allow_download_from_artifact_store: If `True`, code can be downloaded
            from the artifact store.
        build_options: DEPRECATED, use parent_image_build_config.build_options
            instead.
        dockerignore: DEPRECATED, use build_config.dockerignore instead.
        copy_files: DEPRECATED/UNUSED.
        copy_global_config: DEPRECATED/UNUSED.
        source_files: DEPRECATED. Use allow_including_files_in_images,
            allow_download_from_code_repository and
            allow_download_from_artifact_store instead.
    """

    parent_image: Optional[str] = None
    dockerfile: Optional[str] = None
    build_context_root: Optional[str] = None
    parent_image_build_config: Optional[DockerBuildConfig] = None
    skip_build: bool = False
    prevent_build_reuse: bool = False
    target_repository: Optional[str] = None
    python_package_installer: PythonPackageInstaller = (
        PythonPackageInstaller.PIP
    )
    python_package_installer_args: Dict[str, Any] = {}
    replicate_local_python_environment: Optional[
        Union[List[str], PythonEnvironmentExportMethod]
    ] = Field(default=None, union_mode="left_to_right")
    requirements: Union[None, str, List[str]] = Field(
        default=None, union_mode="left_to_right"
    )
    required_integrations: List[str] = []
    install_stack_requirements: bool = True
    apt_packages: List[str] = []
    environment: Dict[str, Any] = {}
    user: Optional[str] = None
    build_config: Optional[DockerBuildConfig] = None

    allow_including_files_in_images: bool = True
    allow_download_from_code_repository: bool = True
    allow_download_from_artifact_store: bool = True

    # Deprecated attributes
    build_options: Dict[str, Any] = {}
    dockerignore: Optional[str] = None
    copy_files: bool = True
    copy_global_config: bool = True
    source_files: Optional[str] = None
    required_hub_plugins: List[str] = []

    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes(
        "copy_files",
        "copy_global_config",
        "source_files",
        "required_hub_plugins",
    )

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _migrate_source_files(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate old source_files values.

        Args:
            data: The model data.

        Raises:
            ValueError: If an invalid source file mode is specified.

        Returns:
            The migrated data.
        """
        source_files = data.get("source_files", None)

        if source_files is None:
            return data

        replacement_attributes = [
            "allow_including_files_in_images",
            "allow_download_from_code_repository",
            "allow_download_from_artifact_store",
        ]
        if any(v in data for v in replacement_attributes):
            logger.warning(
                "Both `source_files` and one of %s specified for the "
                "DockerSettings, ignoring the `source_files` value.",
                replacement_attributes,
            )
            return data

        allow_including_files_in_images = False
        allow_download_from_code_repository = False
        allow_download_from_artifact_store = False

        if source_files == "download":
            allow_download_from_code_repository = True
        elif source_files == "include":
            allow_including_files_in_images = True
        elif source_files == "download_or_include":
            allow_including_files_in_images = True
            allow_download_from_code_repository = True
        elif source_files == "ignore":
            pass
        else:
            raise ValueError(f"Invalid source file mode `{source_files}`.")

        data["allow_including_files_in_images"] = (
            allow_including_files_in_images
        )
        data["allow_download_from_code_repository"] = (
            allow_download_from_code_repository
        )
        data["allow_download_from_artifact_store"] = (
            allow_download_from_artifact_store
        )

        return data

    @model_validator(mode="after")
    def _validate_skip_build(self) -> "DockerSettings":
        """Ensures that a parent image is passed when trying to skip the build.

        Returns:
            The validated settings values.

        Raises:
            ValueError: If the build should be skipped but no parent image
                was specified.
        """
        if self.skip_build and not self.parent_image:
            raise ValueError(
                "Docker settings that specify `skip_build=True` must always "
                "contain a `parent_image`. This parent image will be used "
                "to run the steps of your pipeline directly without additional "
                "Docker builds on top of it."
            )

        return self

    model_config = ConfigDict(
        # public attributes are immutable
        frozen=True,
        # prevent extra attributes during model initialization
        extra="forbid",
    )
