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
"""Models representing pipeline builds."""

from typing import TYPE_CHECKING, Dict, Optional, Tuple, Union
from uuid import UUID

from pydantic import Field

from zenml.models.base_models import (
    WorkspaceScopedRequestModel,
    WorkspaceScopedResponseModel,
)
from zenml.models.filter_models import WorkspaceScopedFilterModel
from zenml.utils import pydantic_utils

if TYPE_CHECKING:
    from zenml.models.pipeline_models import PipelineResponseModel
    from zenml.models.stack_models import StackResponseModel

# ---- #
# BASE #
# ---- #


class PipelineBuildBaseModel(pydantic_utils.YAMLSerializationMixin):
    """Base model for pipeline builds.

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


# -------- #
# RESPONSE #
# -------- #


class PipelineBuildResponseModel(
    PipelineBuildBaseModel, WorkspaceScopedResponseModel
):
    """Response model for pipeline builds."""

    pipeline: Optional["PipelineResponseModel"] = Field(
        title="The pipeline this build belongs to."
    )
    stack: Optional["StackResponseModel"] = Field(
        title="The stack that was used for this build."
    )


# ------ #
# FILTER #
# ------ #


class PipelineBuildFilterModel(WorkspaceScopedFilterModel):
    """Model to enable advanced filtering of all pipeline builds."""

    workspace_id: Union[UUID, str] = Field(
        default=None, description="Workspace for this pipeline build."
    )
    user_id: Union[UUID, str] = Field(
        default=None, description="User that produced this pipeline build."
    )
    pipeline_id: Union[UUID, str] = Field(
        default=None,
        description="Pipeline associated with the pipeline build.",
    )
    stack_id: Union[UUID, str] = Field(
        default=None, description="Stack used for the Pipeline Run"
    )


# ------- #
# REQUEST #
# ------- #


class PipelineBuildRequestModel(
    PipelineBuildBaseModel, WorkspaceScopedRequestModel
):
    """Request model for pipelines builds."""

    stack: Optional[UUID] = None
    pipeline: Optional[UUID] = None
