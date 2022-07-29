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
"""Docker build configuration."""

from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from pydantic import BaseModel, Extra

from zenml.logger import get_logger

if TYPE_CHECKING:

    pass

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


class DockerConfiguration(BaseModel):
    """Class for configuring Docker build options.

    Attributes:
        parent_image: Full name of the Docker image that should be
            used as the parent for the image that will be built. Defaults to
            a ZenML image built for the active Python and ZenML version.

            Additional information to consider:
            * If you specify a custom image here, you need to make sure it has
            ZenML installed.
            * If this is a non-local image, the environment which is running
            the pipeline needs to be able to pull this image.
            * If a custom `dockerfile` is specified for this configuration
            object, this parent image will be ignored.

        docker_target_repository: Name of the Docker Repository



        requirements: Path to a requirements file or a list of required pip
            packages. During the image build, these requirements will be
            installed using pip. If you need to use a different tool to
            resolve and/or install your packages, please use a custom parent
            image or specify a custom `dockerfile`.
        required_integrations: List of ZenML integrations that should be
            installed.
            Each ZenML integration specifies a list of python
            packages that are required for it to work. `zenml integration requirements <INTEGRATION_NAME>`

        replicate_local_python_environment: If `True`, all packages installed
            in the currently running python environment will be installed.

        install_stack_requirements: If `True`, ZenML will automatically detect
            if components of your active stack are part of a ZenML integration
            and install the corresponding requirements. If you set this to
            `False` or use custom components in your stack, you need to make
            sure these get installed by specifying them in the `requirements`
            attribute.
        dockerignore: Path to a dockerignore file to use when building Docker
            images.

        environment: Dictionary of environment variables to set inside the
            Docker image.

        dockerfile:
        build_options: Additional options that will be passed unmodified to the
            Docker build call when building an image using the specified
            `dockerfile`. You can use this to for example specify build
            args or a target stage. See https://docker-py.readthedocs.io/en/stable/images.html#docker.models.images.ImageCollection.build
            for a full list of available options.
        build_context_root: Build context root for the Docker build, only used
            when the `dockerfile` attribute is set. If this is left empty, the
            build context will only contain the Dockerfile.
    """

    parent_image: Optional[str] = None
    dockerfile: Optional[str] = None
    build_context_root: Optional[str] = None
    build_options: Dict[str, Any] = {}

    target_repository: str = "zenml"

    replicate_local_python_environment: Optional[
        PythonEnvironmentExportMethod
    ] = None
    requirements: Union[None, str, List[str]] = None
    required_integrations: List[str] = []
    install_stack_requirements: bool = True

    environment: Dict[str, Any] = {}
    dockerignore: Optional[str] = None
    copy_source_files: bool = True
    copy_profile: bool = True

    class Config:
        """Pydantic configuration class."""

        # public attributes are immutable
        allow_mutation = False
        # prevent extra attributes during model initialization
        extra = Extra.forbid
