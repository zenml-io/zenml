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
"""Unit tests for the DigitalOcean integration flavors.

These tests exercise the config/flavor surface the DigitalOcean integration
adds on top of the inherited S3 implementation: the Spaces region validation
and runtime endpoint derivation on both the s3fs and boto3 code paths, and the
DOCR URI validation. ``boto3.resource`` is mocked so no real S3/Spaces client
is constructed during instantiation.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType
from zenml.integrations.digitalocean.artifact_stores import (
    DigitalOceanSpacesArtifactStore,
)
from zenml.integrations.digitalocean.flavors import (
    DigitalOceanContainerRegistryConfig,
    DigitalOceanContainerRegistryFlavor,
    DigitalOceanSpacesArtifactStoreConfig,
    DigitalOceanSpacesArtifactStoreFlavor,
)

FRA1_ENDPOINT = "https://fra1.digitaloceanspaces.com"


def _build_store(
    config: DigitalOceanSpacesArtifactStoreConfig,
) -> DigitalOceanSpacesArtifactStore:
    """Construct a Spaces artifact store with boto3.resource mocked.

    Args:
        config: The config for the artifact store.

    Returns:
        A DigitalOceanSpacesArtifactStore instance.
    """
    with patch("boto3.resource", MagicMock()):
        return DigitalOceanSpacesArtifactStore(
            name="",
            id=uuid4(),
            config=config,
            flavor="digitalocean_spaces",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )


# --- artifact store flavor ---------------------------------------------------


def test_artifact_store_flavor_identity():
    """The Spaces flavor identifier, display name and config class are DO's."""
    flavor = DigitalOceanSpacesArtifactStoreFlavor()
    assert flavor.name == "digitalocean_spaces"
    assert flavor.display_name == "DigitalOcean Spaces"
    assert flavor.config_class is DigitalOceanSpacesArtifactStoreConfig
    assert flavor.implementation_class is DigitalOceanSpacesArtifactStore
    assert flavor.service_connector_requirements is None


def test_region_format_validation():
    """Well-formed region slugs pass (including unknown ones); junk fails."""
    for region in ["fra1", "nyc3", "lon1", "tor1", "atl1"]:
        config = DigitalOceanSpacesArtifactStoreConfig(
            path="s3://s", region=region
        )
        assert config.region == region

    for region in ["FRA1", "fra1.evil.com", "not a region", "fra-1", ""]:
        with pytest.raises(ValueError):
            DigitalOceanSpacesArtifactStoreConfig(path="s3://s", region=region)


def test_requires_region_or_endpoint():
    """Neither region nor endpoint is an error; either one is accepted."""
    with pytest.raises(ValueError):
        DigitalOceanSpacesArtifactStoreConfig(path="s3://s")

    # explicit endpoint, no region -> ok
    DigitalOceanSpacesArtifactStoreConfig(
        path="s3://s",
        client_kwargs={"endpoint_url": "https://custom.example.com"},
    )


def test_config_does_not_persist_derived_endpoint():
    """The region-derived endpoint is not persisted in the config."""
    config = DigitalOceanSpacesArtifactStoreConfig(
        path="s3://s", region="fra1"
    )
    assert config.client_kwargs is None
    assert config.region == "fra1"


def test_filesystem_wires_derived_endpoint_into_s3fs():
    """The filesystem property passes the derived endpoint to the s3fs client."""
    store = _build_store(
        DigitalOceanSpacesArtifactStoreConfig(path="s3://s", region="fra1")
    )
    fs_cls = MagicMock()
    with patch(
        "zenml.integrations.digitalocean.artifact_stores"
        ".digitalocean_artifact_store.ZenMLS3Filesystem",
        fs_cls,
    ):
        _ = store.filesystem

    client_kwargs = fs_cls.call_args.kwargs["client_kwargs"]
    assert client_kwargs["endpoint_url"] == FRA1_ENDPOINT


def test_boto3_kwargs_carry_endpoint_and_config_kwargs():
    """The boto3 path sees the derived endpoint and a botocore Config."""
    store = _build_store(
        DigitalOceanSpacesArtifactStoreConfig(
            path="s3://s",
            region="fra1",
            config_kwargs={"signature_version": "s3v4"},
        )
    )
    kwargs = store._build_boto3_kwargs()
    assert kwargs["endpoint_url"] == FRA1_ENDPOINT
    assert kwargs["config"].signature_version == "s3v4"


def test_explicit_endpoint_overrides_region():
    """An explicit endpoint_url is preserved over the region-derived one."""
    store = _build_store(
        DigitalOceanSpacesArtifactStoreConfig(
            path="s3://s",
            region="fra1",
            client_kwargs={"endpoint_url": "https://custom.example.com"},
        )
    )
    kwargs = store._build_boto3_kwargs()
    assert kwargs["endpoint_url"] == "https://custom.example.com"


# --- container registry flavor -----------------------------------------------


def test_container_registry_flavor_identity():
    """The DOCR flavor identifier, display name and config class are DO's."""
    flavor = DigitalOceanContainerRegistryFlavor()
    assert flavor.name == "digitalocean"
    assert flavor.display_name == "DigitalOcean"
    assert flavor.config_class is DigitalOceanContainerRegistryConfig


def test_docr_uri_validation():
    """DOCR URIs are validated and normalized."""
    ok = DigitalOceanContainerRegistryConfig(
        uri="registry.digitalocean.com/my-registry"
    )
    assert ok.uri == "registry.digitalocean.com/my-registry"

    # trailing slash stripped
    stripped = DigitalOceanContainerRegistryConfig(
        uri="registry.digitalocean.com/my-registry/"
    )
    assert stripped.uri == "registry.digitalocean.com/my-registry"

    for bad_uri in [
        "docker.io/my-registry",
        # lookalike hosts that merely start with the DOCR host string
        "registry.digitalocean.community/my-registry",
        "registry.digitalocean.com.evil.example/my-registry",
        # bare host without a registry name
        "registry.digitalocean.com",
        "registry.digitalocean.com/",
    ]:
        with pytest.raises(ValueError):
            DigitalOceanContainerRegistryConfig(uri=bad_uri)


# --- integration registration ------------------------------------------------


def test_integration_registered():
    """The DigitalOcean integration is discoverable in the registry."""
    from zenml.integrations.digitalocean import DigitalOceanIntegration
    from zenml.integrations.registry import integration_registry

    integration_registry._initialize()
    assert (
        integration_registry.integrations["digitalocean"]
        is DigitalOceanIntegration
    )
    flavors = {f().name for f in DigitalOceanIntegration.flavors()}
    assert flavors == {"digitalocean_spaces", "digitalocean"}
