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
"""Unit tests for the boto3 client configuration of the S3 artifact store."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from botocore.config import Config

from zenml.enums import StackComponentType
from zenml.integrations.s3.artifact_stores.s3_artifact_store import (
    S3ArtifactStore,
)
from zenml.integrations.s3.flavors.s3_artifact_store_flavor import (
    S3ArtifactStoreConfig,
)


def _build_s3_artifact_store(config: S3ArtifactStoreConfig) -> S3ArtifactStore:
    """Construct an S3ArtifactStore with boto3.resource mocked.

    Args:
        config: The artifact store config.

    Returns:
        The artifact store.
    """
    with patch("boto3.resource", MagicMock()):
        return S3ArtifactStore(
            name="",
            id=uuid4(),
            config=config,
            flavor="s3",
            type=StackComponentType.ARTIFACT_STORE,
            user=uuid4(),
            created=datetime.now(),
            updated=datetime.now(),
        )


def test_boto3_kwargs_apply_config_kwargs_as_boto3_config():
    """`config_kwargs` such as retries also reach the boto3.resource path."""
    store = _build_s3_artifact_store(
        S3ArtifactStoreConfig(
            path="s3://my-bucket",
            config_kwargs={"retries": {"max_attempts": 1}},
        )
    )

    kwargs = store._build_boto3_kwargs()

    assert isinstance(kwargs["config"], Config)
    assert kwargs["config"].retries == {"max_attempts": 1}


def test_boto3_kwargs_without_config_kwargs_have_no_config():
    """Without `config_kwargs` the boto3 defaults are left untouched."""
    store = _build_s3_artifact_store(
        S3ArtifactStoreConfig(path="s3://my-bucket")
    )

    assert "config" not in store._build_boto3_kwargs()


def test_boto3_kwargs_keep_explicit_client_config():
    """A `config` passed via `client_kwargs` wins over `config_kwargs`."""
    explicit = Config(retries={"max_attempts": 7})
    store = _build_s3_artifact_store(
        S3ArtifactStoreConfig(
            path="s3://my-bucket",
            client_kwargs={"config": explicit},
            config_kwargs={"retries": {"max_attempts": 1}},
        )
    )

    assert store._build_boto3_kwargs()["config"] is explicit
