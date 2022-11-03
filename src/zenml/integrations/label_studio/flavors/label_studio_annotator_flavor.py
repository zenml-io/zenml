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
"""Label Studio annotator flavor."""

from typing import TYPE_CHECKING, Type

from zenml.annotators.base_annotator import (
    BaseAnnotatorConfig,
    BaseAnnotatorFlavor,
)
from zenml.integrations.label_studio import LABEL_STUDIO_ANNOTATOR_FLAVOR
from zenml.stack.authentication_mixin import AuthenticationConfigMixin

if TYPE_CHECKING:
    from zenml.integrations.label_studio.annotators import LabelStudioAnnotator


DEFAULT_LOCAL_INSTANCE_URL = "http://localhost"
DEFAULT_LOCAL_LABEL_STUDIO_PORT = 8093


class LabelStudioAnnotatorConfig(
    BaseAnnotatorConfig, AuthenticationConfigMixin
):
    """Config for the Label Studio annotator.

    Attributes:
        instance_url: URL of the Label Studio instance.
        port: The port to use for the annotation interface.
    """

    instance_url: str = DEFAULT_LOCAL_INSTANCE_URL
    port: int = DEFAULT_LOCAL_LABEL_STUDIO_PORT


class LabelStudioAnnotatorFlavor(BaseAnnotatorFlavor):
    """Label Studio annotator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return LABEL_STUDIO_ANNOTATOR_FLAVOR

    @property
    def config_class(self) -> Type[LabelStudioAnnotatorConfig]:
        """Returns `LabelStudioAnnotatorConfig` config class.

        Returns:
                The config class.
        """
        return LabelStudioAnnotatorConfig

    @property
    def implementation_class(self) -> Type["LabelStudioAnnotator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.label_studio.annotators import (
            LabelStudioAnnotator,
        )

        return LabelStudioAnnotator
