#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Pigeon annotator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.annotators.base_annotator import (
    BaseAnnotatorConfig,
    BaseAnnotatorFlavor,
)
from zenml.config.base_settings import BaseSettings
from zenml.integrations.pigeon import PIGEON_ANNOTATOR_FLAVOR
from zenml.stack.authentication_mixin import AuthenticationConfigMixin

if TYPE_CHECKING:
    from zenml.integrations.pigeon.annotators import PigeonAnnotator


class PigeonAnnotatorSettings(BaseSettings):
    """Settings for the Pigeon annotator."""


class PigeonAnnotatorConfig(
    BaseAnnotatorConfig, PigeonAnnotatorSettings, AuthenticationConfigMixin
):
    """Config for the Pigeon annotator.

    Attributes:
        output_dir: The directory to store the annotations.
        notebook_only: Whether the annotator only works within a notebook.
    """

    output_dir: str = "annotations"


class PigeonAnnotatorFlavor(BaseAnnotatorFlavor):
    """Pigeon annotator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return PIGEON_ANNOTATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/annotator/pigeon.png"

    @property
    def config_class(self) -> Type[PigeonAnnotatorConfig]:
        """Returns `PigeonAnnotatorConfig` config class.

        Returns:
            The config class.
        """
        return PigeonAnnotatorConfig

    @property
    def implementation_class(self) -> Type["PigeonAnnotator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.pigeon.annotators import PigeonAnnotator

        return PigeonAnnotator
