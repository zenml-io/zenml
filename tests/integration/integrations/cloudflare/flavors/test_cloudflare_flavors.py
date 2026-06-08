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

import pytest
from pydantic import ValidationError

from zenml.integrations.cloudflare import (
    CLOUDFLARE_CONTAINER_REGISTRY_FLAVOR,
    CLOUDFLARE_R2_ARTIFACT_STORE_FLAVOR,
)
from zenml.integrations.cloudflare.flavors import (
    CloudflareContainerRegistryFlavor,
    R2ArtifactStoreConfig,
    R2ArtifactStoreFlavor,
)


def test_r2_config_derives_endpoint_from_account_id():
    """The R2 endpoint is built from the account ID when not given."""
    config = R2ArtifactStoreConfig(
        path="r2://my-bucket/artifacts", account_id="abc123"
    )
    assert (
        config.client_kwargs["endpoint_url"]
        == "https://abc123.r2.cloudflarestorage.com"
    )
    # botocore's SigV4 signer requires a region even though R2 ignores it.
    assert config.config_kwargs["region_name"] == "auto"


def test_r2_config_preserves_explicit_endpoint():
    """An explicitly provided endpoint takes precedence over the account ID."""
    config = R2ArtifactStoreConfig(
        path="r2://my-bucket",
        account_id="abc123",
        client_kwargs={"endpoint_url": "https://custom.example.com"},
    )
    assert config.client_kwargs["endpoint_url"] == "https://custom.example.com"


def test_r2_config_requires_account_or_endpoint():
    """Either an account ID or an explicit endpoint must be supplied."""
    with pytest.raises(ValidationError):
        R2ArtifactStoreConfig(path="r2://my-bucket")


def test_r2_config_supported_scheme_and_bucket():
    """The R2 config only supports `r2://` and parses the bucket name."""
    config = R2ArtifactStoreConfig(
        path="r2://my-bucket/some/prefix", account_id="abc123"
    )
    assert config.SUPPORTED_SCHEMES == {"r2://"}
    assert config.bucket == "my-bucket"


def test_r2_flavor_metadata():
    """The R2 artifact store flavor exposes the expected metadata."""
    flavor = R2ArtifactStoreFlavor()
    assert flavor.name == CLOUDFLARE_R2_ARTIFACT_STORE_FLAVOR == "r2"
    assert flavor.config_class is R2ArtifactStoreConfig
    # Implementation class is imported lazily; resolving it must not raise.
    assert flavor.implementation_class.__name__ == "R2ArtifactStore"


def test_container_registry_flavor_metadata():
    """The Cloudflare container registry flavor exposes expected metadata."""
    flavor = CloudflareContainerRegistryFlavor()
    assert flavor.name == CLOUDFLARE_CONTAINER_REGISTRY_FLAVOR == "cloudflare"
    assert flavor.implementation_class.__name__ == "BaseContainerRegistry"
