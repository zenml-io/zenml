# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Container build settings for remote demonstration pipelines."""

from zenml.config import DockerSettings
from zenml.config.docker_settings import DockerBuildConfig, DockerBuildOptions


def create_docker_settings() -> DockerSettings:
    """Configure the remote execution image and its dependencies.

    Returns:
        Docker settings for a ZenML 0.96.4 Python 3.11 Linux AMD64 image.
    """
    return DockerSettings(
        parent_image="zenmldocker/zenml:0.96.4-py3.11",
        requirements="requirements.txt",
        install_stack_requirements=False,
        disable_automatic_requirements_detection=True,
        build_config=DockerBuildConfig(
            build_options=DockerBuildOptions(platform="linux/amd64")
        ),
    )
