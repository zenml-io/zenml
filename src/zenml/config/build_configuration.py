#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from typing import Dict, Optional, Tuple

from pydantic import BaseModel

from zenml.config import DockerSettings
from zenml.utils import pydantic_utils


class BuildConfiguration(BaseModel):
    key: str
    settings: DockerSettings
    tag: str
    step_name: Optional[str] = None
    entrypoint: Optional[str] = None

    @property
    def settings_hash(self) -> str:
        import hashlib

        build_settings_hash = hashlib.md5()
        build_settings_hash.update(self.settings.json().encode())
        if self.entrypoint:
            build_settings_hash.update(self.entrypoint.encode())

        return build_settings_hash.hexdigest()


class PipelineBuild(pydantic_utils.YAMLSerializationMixin):
    """Output of Docker builds to run a pipeline.

    Attributes:
        pipeline_images: General Docker images built for the entire pipeline.
        step_images: Docker images built for specific steps of the pipeline.
    """

    pipeline_images: Dict[str, Tuple[str, str]] = {}
    step_images: Dict[str, Dict[str, Tuple[str, str]]] = {}
    is_local: bool

    def get_image(self, key: str, step: Optional[str] = None) -> str:
        """Get the image built for a specific key.

        Args:
            key: The key for which to get the image.
            step: The name of the step for which to get the image. If no image
                exists for this step, will fallback to the pipeline image for
                the same key.

        Raises:
            KeyError: If no image exists for the given key.

        Returns:
            The image name or digest.
        """
        images = self.pipeline_images.copy()

        if step:
            images.update(self.step_images.get(step, {}))

        try:
            image = images[key]
            return image[0]
        except KeyError:
            raise KeyError(
                f"Unable to find image for key {key}. Available keys: "
                f"{set(images)}."
            )

    def get_settings_hash(self, key: str, step: Optional[str] = None) -> str:
        images = self.pipeline_images.copy()

        if step:
            images.update(self.step_images.get(step, {}))

        try:
            image = images[key]
            return image[1]
        except KeyError:
            raise KeyError(
                f"Unable to find settings hash for key {key}. Available keys: "
                f"{set(images)}."
            )
