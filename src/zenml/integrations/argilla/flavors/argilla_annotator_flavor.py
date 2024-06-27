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
"""Argilla annotator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from pydantic import validator

from zenml.annotators.base_annotator import (
    BaseAnnotatorConfig,
    BaseAnnotatorFlavor,
)
from zenml.config.base_settings import BaseSettings
from zenml.integrations.argilla import ARGILLA_ANNOTATOR_FLAVOR
from zenml.stack.authentication_mixin import AuthenticationConfigMixin
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.argilla.annotators import ArgillaAnnotator


DEFAULT_LOCAL_INSTANCE_URL = "http://localhost"
DEFAULT_LOCAL_ARGILLA_PORT = 6900


class ArgillaAnnotatorSettings(BaseSettings):
    """Argilla annotator settings.

    If you are using a private Hugging Face Spaces instance of Argilla you
        must pass in https_extra_kwargs.

    Attributes:
        instance_url: URL of the Argilla instance.
        api_key: The api_key for Argilla
        workspace: The workspace to use for the annotation interface.
        port: The port to use for the annotation interface.
        extra_headers: Extra headers to include in the request.
        httpx_extra_kwargs: Extra kwargs to pass to the client.
    """

    instance_url: str = DEFAULT_LOCAL_INSTANCE_URL
    api_key: Optional[str] = SecretField()
    workspace: Optional[str] = "admin"
    port: Optional[int]
    extra_headers: Optional[str] = None
    httpx_extra_kwargs: Optional[str] = None

    @validator("instance_url")
    def ensure_instance_url_ends_without_slash(cls, instance_url: str) -> str:
        """Pydantic validator to ensure instance URL ends without a slash.

        Args:
            instance_url: The instance URL to validate.

        Returns:
            The validated instance URL.
        """
        return instance_url.rstrip("/")


class ArgillaAnnotatorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseAnnotatorConfig,
    ArgillaAnnotatorSettings,
    AuthenticationConfigMixin,
):
    """Config for the Argilla annotator.

    This class combines settings and authentication configurations for
    Argilla into a single, usable configuration object without adding
    additional functionality.
    """


class ArgillaAnnotatorFlavor(BaseAnnotatorFlavor):
    """Argilla annotator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return ARGILLA_ANNOTATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/annotator/argilla.png"

    @property
    def config_class(self) -> Type[ArgillaAnnotatorConfig]:
        """Returns `ArgillaAnnotatorConfig` config class.

        Returns:
                The config class.
        """
        return ArgillaAnnotatorConfig

    @property
    def implementation_class(self) -> Type["ArgillaAnnotator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.argilla.annotators import (
            ArgillaAnnotator,
        )

        return ArgillaAnnotator
