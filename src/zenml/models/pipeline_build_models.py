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

from typing import TYPE_CHECKING, Dict, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

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


class BuildItem(BaseModel):
    image: str
    settings_checksum: Optional[str] = None


class PipelineBuildBaseModel(pydantic_utils.YAMLSerializationMixin):
    """Base model for pipeline builds.

    Attributes:
        pipeline_images: General Docker images built for the entire pipeline.
        step_images: Docker images built for specific steps of the pipeline.
    """

    images: Dict[str, BuildItem] = {}
    is_local: bool

    @staticmethod
    def get_key(key: str, step: str) -> str:
        return f"{step}.{key}"

    def _get_item(self, key: str, step: Optional[str] = None) -> BuildItem:
        if step:
            try:
                k = self.get_key(key=key, step=step)
                return self.images[k]
            except KeyError:
                pass

        return self.images[key]

        # raise KeyError(
        #         f"Unable to find image for key {key}. Available keys: "
        #         f"{set(images)}."
        #     )

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
        return self._get_item(key=key, step=step).image

    def get_settings_checksum(
        self, key: str, step: Optional[str] = None
    ) -> Optional[str]:
        return self._get_item(key=key, step=step).settings_checksum


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
