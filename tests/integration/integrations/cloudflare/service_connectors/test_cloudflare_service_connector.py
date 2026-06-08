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

from unittest.mock import MagicMock, patch

import pytest

from zenml.exceptions import AuthorizationException
from zenml.integrations.cloudflare import (
    CLOUDFLARE_GENERIC_RESOURCE_TYPE,
    CLOUDFLARE_R2_RESOURCE_TYPE,
)
from zenml.integrations.cloudflare.service_connectors.cloudflare_service_connector import (
    CloudflareApiTokenConfig,
    CloudflareAuthenticationMethods,
    CloudflareR2Config,
    CloudflareServiceConnector,
)

ACCOUNT_ID = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
MODULE = (
    "zenml.integrations.cloudflare.service_connectors."
    "cloudflare_service_connector"
)


def _r2_connector(resource_id=None):
    return CloudflareServiceConnector(
        auth_method=CloudflareAuthenticationMethods.R2_CREDENTIALS,
        resource_type=CLOUDFLARE_R2_RESOURCE_TYPE,
        resource_id=resource_id,
        config=CloudflareR2Config(
            account_id=ACCOUNT_ID,
            aws_access_key_id="key",
            aws_secret_access_key="secret",
        ),
    )


def _token_connector(resource_id=None):
    return CloudflareServiceConnector(
        auth_method=CloudflareAuthenticationMethods.API_TOKEN,
        resource_type=CLOUDFLARE_GENERIC_RESOURCE_TYPE,
        resource_id=resource_id,
        config=CloudflareApiTokenConfig(
            account_id=ACCOUNT_ID, api_token="cf-token"
        ),
    )


def test_connector_type_spec():
    """The connector declares the expected resource types and auth methods."""
    spec = CloudflareServiceConnector._get_connector_type()
    assert spec.connector_type == "cloudflare"
    assert {a.auth_method for a in spec.auth_methods} == {
        "api-token",
        "r2-credentials",
    }
    resource_types = {r.resource_type: r for r in spec.resource_types}
    assert (
        resource_types[CLOUDFLARE_R2_RESOURCE_TYPE].supports_instances is True
    )
    assert (
        resource_types[CLOUDFLARE_GENERIC_RESOURCE_TYPE].supports_instances
        is False
    )
    # Each resource type is tied to exactly the auth method that can serve it.
    assert resource_types[CLOUDFLARE_R2_RESOURCE_TYPE].auth_methods == [
        "r2-credentials"
    ]
    assert resource_types[CLOUDFLARE_GENERIC_RESOURCE_TYPE].auth_methods == [
        "api-token"
    ]


def test_r2_endpoint_url_derived_from_account():
    """The R2 endpoint is built from the account ID."""
    connector = _r2_connector(resource_id="r2://bucket")
    assert (
        connector.r2_endpoint_url
        == f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"
    )


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("r2://my-bucket", "my-bucket"),
        ("s3://my-bucket", "my-bucket"),
        ("my-bucket", "my-bucket"),
    ],
)
def test_parse_r2_resource_id(raw, expected):
    """Bucket references are normalized to a bare bucket name."""
    assert CloudflareServiceConnector._parse_r2_resource_id(raw) == expected


def test_parse_r2_resource_id_rejects_nested_paths():
    """A path with a key component is not a valid bucket reference."""
    with pytest.raises(ValueError):
        CloudflareServiceConnector._parse_r2_resource_id("r2://bucket/key")


def test_canonical_resource_id():
    """R2 resource IDs canonicalize to the r2:// form."""
    connector = _r2_connector(resource_id="my-bucket")
    assert (
        connector._canonical_resource_id(
            CLOUDFLARE_R2_RESOURCE_TYPE, "s3://my-bucket"
        )
        == "r2://my-bucket"
    )


def test_default_resource_id_for_generic():
    """The generic resource type defaults to the account ID."""
    connector = _token_connector()
    assert (
        connector._get_default_resource_id(CLOUDFLARE_GENERIC_RESOURCE_TYPE)
        == ACCOUNT_ID
    )


def test_connect_to_r2_returns_client_with_credentials():
    """Connecting to r2-bucket returns a boto3 client with attached creds."""
    connector = _r2_connector(resource_id="r2://bucket")
    fake_client = MagicMock()
    fake_session = MagicMock()
    fake_session.client.return_value = fake_client
    with patch(f"{MODULE}.boto3.Session", return_value=fake_session):
        client = connector._connect_to_resource()
    fake_session.client.assert_called_once_with(
        "s3", endpoint_url=f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com"
    )
    assert client is fake_client
    assert client.credentials is fake_session.get_credentials.return_value


def test_connect_to_generic_returns_token_and_account():
    """Connecting to cloudflare-generic hands back token + account ID."""
    connector = _token_connector(resource_id=ACCOUNT_ID)
    result = connector._connect_to_resource()
    assert result == {"account_id": ACCOUNT_ID, "api_token": "cf-token"}


def test_verify_r2_lists_buckets():
    """Verifying r2-bucket with no resource ID lists buckets."""
    connector = _r2_connector()
    fake_client = MagicMock()
    fake_client.list_buckets.return_value = {
        "Buckets": [{"Name": "alpha"}, {"Name": "beta"}]
    }
    with patch.object(connector, "_r2_client", return_value=fake_client):
        resources = connector._verify(
            resource_type=CLOUDFLARE_R2_RESOURCE_TYPE
        )
    assert resources == ["r2://alpha", "r2://beta"]


def test_verify_r2_specific_bucket():
    """Verifying a specific bucket calls head_bucket and returns it."""
    connector = _r2_connector(resource_id="r2://alpha")
    fake_client = MagicMock()
    with patch.object(connector, "_r2_client", return_value=fake_client):
        resources = connector._verify(
            resource_type=CLOUDFLARE_R2_RESOURCE_TYPE,
            resource_id="r2://alpha",
        )
    fake_client.head_bucket.assert_called_once_with(Bucket="alpha")
    assert resources == ["r2://alpha"]


def test_verify_r2_raises_on_bad_credentials():
    """A client error during discovery surfaces as AuthorizationException."""
    from botocore.exceptions import ClientError

    connector = _r2_connector()
    fake_client = MagicMock()
    fake_client.list_buckets.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "no"}}, "ListBuckets"
    )
    with patch.object(connector, "_r2_client", return_value=fake_client):
        with pytest.raises(AuthorizationException):
            connector._verify(resource_type=CLOUDFLARE_R2_RESOURCE_TYPE)


def test_verify_api_token_success():
    """A successful token verification returns the account ID."""
    connector = _token_connector()
    response = MagicMock(ok=True)
    response.json.return_value = {"success": True}
    with patch(f"{MODULE}.requests.get", return_value=response) as get:
        resources = connector._verify(
            resource_type=CLOUDFLARE_GENERIC_RESOURCE_TYPE
        )
    assert resources == [ACCOUNT_ID]
    # Token is sent as a bearer header.
    _, kwargs = get.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer cf-token"


def test_verify_api_token_failure_raises():
    """An unsuccessful token verification raises AuthorizationException."""
    connector = _token_connector()
    response = MagicMock(ok=True)
    response.json.return_value = {"success": False}
    with patch(f"{MODULE}.requests.get", return_value=response):
        with pytest.raises(AuthorizationException):
            connector._verify(resource_type=CLOUDFLARE_GENERIC_RESOURCE_TYPE)


def test_local_client_and_autoconfigure_not_supported():
    """Local client config and auto-configuration are intentionally absent."""
    connector = _r2_connector(resource_id="r2://bucket")
    with pytest.raises(NotImplementedError):
        connector._configure_local_client()
    with pytest.raises(NotImplementedError):
        CloudflareServiceConnector._auto_configure()
