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
"""Artifact Config classes to support Model Control Plane feature."""

from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field, PrivateAttr, model_validator

from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.utils.pydantic_utils import before_validator_handler
from zenml.utils.string_utils import format_name_template

logger = get_logger(__name__)


class ArtifactConfig(BaseModel):
    """Artifact configuration class.

    Can be used in step definitions to define various artifact properties.

    Example:
    ```python
    @step
    def my_step() -> Annotated[
        int, ArtifactConfig(
            name="my_artifact",  # override the default artifact name
            version=42,  # set a custom version
            tags=["tag1", "tag2"],  # set custom tags
        )
    ]:
        return ...
    ```

    Attributes:
        name: The name of the artifact:
            - static string e.g. "name"
            - dynamic callable e.g. lambda: "name"+str(42)
            - dynamic string e.g. "name_{date}_{time}"
        version: The version of the artifact.
        tags: The tags of the artifact.
        run_metadata: Metadata to add to the artifact.
        is_model_artifact: Whether the artifact is a model artifact.
        is_deployment_artifact: Whether the artifact is a deployment artifact.
    """

    name: Optional[Union[str, Callable[[], str]]] = Field(
        default=None, union_mode="smart"
    )
    version: Optional[Union[str, int]] = Field(
        default=None, union_mode="smart"
    )
    tags: Optional[List[str]] = None
    run_metadata: Optional[Dict[str, MetadataType]] = None

    is_model_artifact: bool = False
    is_deployment_artifact: bool = False

    _is_dynamic: bool = PrivateAttr(False)

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _remove_old_attributes(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove old attributes that are not used anymore.

        Args:
            data: The model data.

        Returns:
            Model data without the removed attributes.
        """
        model_name = data.pop("model_name", None)
        model_version = data.pop("model_version", None)

        if model_name or model_version:
            logger.warning(
                "Specifying a model name or version for a step output "
                "artifact is not supported anymore."
            )

        return data

    @model_validator(mode="after")
    def artifact_config_after_validator(self) -> "ArtifactConfig":
        """Artifact config after validator.

        Returns:
            The artifact config.
        """
        if isinstance(self.name, str):
            _name = format_name_template(self.name)
            self._is_dynamic = _name != self.name
            self.name = _name
        elif callable(self.name):
            self.name = self.name()
            self._is_dynamic = True
        return self

    @property
    def _evaluated_name(self) -> Optional[str]:
        """Evaluated name of the artifact.

        Returns:
            The evaluated name of the artifact.

        Raises:
            RuntimeError: If the name is still a callable.
        """
        if callable(self.name):
            raise RuntimeError(
                "Artifact name is still a callable, evaluation error happened. Contact ZenML team to follow-up."
            )
        return self.name
