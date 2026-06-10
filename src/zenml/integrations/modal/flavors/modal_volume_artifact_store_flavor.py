#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Modal Volume artifact store flavor."""

import posixpath
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Set, Type
from urllib.parse import unquote, urlparse

from pydantic import Field, field_validator, model_validator

from zenml.artifact_stores import (
    BaseArtifactStoreConfig,
    BaseArtifactStoreFlavor,
)
from zenml.integrations.modal import MODAL_VOLUME_ARTIFACT_STORE_FLAVOR

if TYPE_CHECKING:
    from zenml.integrations.modal.artifact_stores import (
        ModalVolumeArtifactStore,
    )


MODAL_VOLUME_URI_SCHEME_NAME = "modal-volume"
MODAL_VOLUME_URI_SCHEME = f"{MODAL_VOLUME_URI_SCHEME_NAME}://"
ENV_ZENML_MODAL_ARTIFACT_STORE_FAST_PATH = (
    "ZENML_MODAL_ARTIFACT_STORE_FAST_PATH"
)
ENV_ZENML_MODAL_ARTIFACT_STORE_MOUNT_PATH = (
    "ZENML_MODAL_ARTIFACT_STORE_MOUNT_PATH"
)
ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_NAME = (
    "ZENML_MODAL_ARTIFACT_STORE_VOLUME_NAME"
)
ENV_ZENML_MODAL_ARTIFACT_STORE_VOLUME_PREFIX = (
    "ZENML_MODAL_ARTIFACT_STORE_VOLUME_PREFIX"
)


@dataclass(frozen=True)
class ModalVolumePath:
    """Parsed parts of a Modal Volume artifact-store URI."""

    volume_name: str
    volume_prefix: str


def parse_modal_volume_uri(uri: str) -> ModalVolumePath:
    """Parse and validate a Modal Volume artifact-store URI.

    Args:
        uri: The URI to parse.

    Returns:
        The parsed Modal Volume name and prefix.

    Raises:
        ValueError: If the URI is not a valid Modal Volume artifact-store URI.
    """
    parsed = urlparse(uri)
    if parsed.scheme != MODAL_VOLUME_URI_SCHEME_NAME:
        raise ValueError(
            "Modal Volume artifact store paths must start with "
            f"'{MODAL_VOLUME_URI_SCHEME}'."
        )
    if not parsed.netloc:
        raise ValueError(
            "Modal Volume artifact store paths must include a volume name, "
            "for example 'modal-volume://my-volume/artifacts'."
        )
    if parsed.query:
        raise ValueError(
            "Modal Volume artifact store paths must not include a query string."
        )
    if parsed.fragment:
        raise ValueError(
            "Modal Volume artifact store paths must not include a fragment."
        )
    try:
        has_port = parsed.port is not None
    except ValueError as exc:
        raise ValueError(
            "Modal Volume artifact store paths must not include a port."
        ) from exc
    if parsed.username or parsed.password or has_port:
        raise ValueError(
            "Modal Volume artifact store paths must only include the Modal "
            "Volume name as the URI authority."
        )

    raw_segments = unquote(parsed.path).split("/")
    segments = [
        segment for segment in raw_segments if segment not in ("", ".")
    ]
    if any(segment == ".." for segment in segments):
        raise ValueError(
            "Modal Volume artifact store paths must not contain path traversal "
            "segments ('..')."
        )

    return ModalVolumePath(
        volume_name=parsed.netloc,
        volume_prefix="/".join(segments),
    )


class ModalVolumeArtifactStoreConfig(BaseArtifactStoreConfig):
    """Configuration for the Modal Volume artifact store."""

    SUPPORTED_SCHEMES: ClassVar[Set[str]] = {MODAL_VOLUME_URI_SCHEME}

    mount_path: str = Field(
        default="/zenml-artifacts",
        description="Absolute path where the Modal Volume is mounted inside "
        "Modal execution environments.",
    )
    create_if_missing: bool = Field(
        default=False,
        description="Whether Modal runtime wiring may create the Volume if it "
        "does not already exist.",
    )

    @model_validator(mode="after")
    def _validate_modal_volume_config(
        self,
    ) -> "ModalVolumeArtifactStoreConfig":
        """Validate the Modal Volume URI and mount path.

        Returns:
            The validated config.

        Raises:
            ValueError: If the URI or mount path is invalid.
        """
        parse_modal_volume_uri(self.path)

        return self

    @field_validator("mount_path")
    @classmethod
    def _validate_mount_path(cls, mount_path: str) -> str:
        """Validate and normalize the Modal Volume mount path.

        Args:
            mount_path: The configured mount path.

        Returns:
            The normalized absolute mount path.

        Raises:
            ValueError: If the mount path is invalid.
        """
        if not posixpath.isabs(mount_path):
            raise ValueError("Modal Volume mount_path must be absolute.")

        normalized_mount_path = posixpath.normpath(mount_path)
        if normalized_mount_path == posixpath.sep:
            raise ValueError("Modal Volume mount_path must not be '/'.")

        return normalized_mount_path

    @property
    def volume_name(self) -> str:
        """The Modal Volume name derived from `path`.

        Returns:
            The Modal Volume name.
        """
        return parse_modal_volume_uri(self.path).volume_name

    @property
    def volume_prefix(self) -> str:
        """The Modal Volume prefix derived from `path`.

        Returns:
            The prefix inside the Modal Volume, without a leading slash.
        """
        return parse_modal_volume_uri(self.path).volume_prefix


class ModalVolumeArtifactStoreFlavor(BaseArtifactStoreFlavor):
    """Flavor for the Modal Volume artifact store."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return MODAL_VOLUME_ARTIFACT_STORE_FLAVOR

    @property
    def display_name(self) -> str:
        """Display name of the flavor.

        Returns:
            The display name of the flavor.
        """
        return "Modal Volume"

    @property
    def docs_url(self) -> str:
        """A URL to point at docs explaining this flavor.

        Returns:
            A flavor docs URL.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> str:
        """A URL to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs URL.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A URL to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/artifact_store/modal.png"

    @property
    def config_class(self) -> Type[ModalVolumeArtifactStoreConfig]:
        """The config class of the flavor.

        Returns:
            The config class of the flavor.
        """
        return ModalVolumeArtifactStoreConfig

    @property
    def implementation_class(self) -> Type["ModalVolumeArtifactStore"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class for this flavor.
        """
        from zenml.integrations.modal.artifact_stores import (
            ModalVolumeArtifactStore,
        )

        return ModalVolumeArtifactStore
