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
"""Tests for the REST ZenML store."""

from uuid import uuid4

from pytest_mock import MockerFixture

from zenml.zen_stores.rest_zen_store import (
    ARTIFACT_VERSIONS,
    RestZenStore,
    RestZenStoreConfiguration,
)

SERVER_URL = "https://server.example"
SERVER_URL_WITH_SLASH = f"{SERVER_URL}/"


def test_rest_store_url_is_normalized_before_moving_credentials(
    mocker: MockerFixture,
) -> None:
    """Tests that REST store API tokens use the normalized server URL."""
    credentials_store = mocker.Mock()
    mocker.patch(
        "zenml.zen_stores.rest_zen_store.get_credentials_store",
        return_value=credentials_store,
    )

    config = RestZenStoreConfiguration(
        url=SERVER_URL_WITH_SLASH,
        api_token="test-api-token",
    )

    assert config.url == SERVER_URL
    credentials_store.set_bare_token.assert_called_once_with(
        SERVER_URL, "test-api-token"
    )


def test_delete_artifact_version_can_request_server_side_data_deletion(
    mocker: MockerFixture,
) -> None:
    """Tests forwarding artifact data deletion to the server."""
    store = mocker.Mock()
    artifact_version_id = uuid4()

    RestZenStore.delete_artifact_version(
        store,
        artifact_version_id=artifact_version_id,
        delete_from_artifact_store=True,
    )

    store._delete_resource.assert_called_once_with(
        resource_id=artifact_version_id,
        route=ARTIFACT_VERSIONS,
        params={
            "delete_metadata": True,
            "delete_from_artifact_store": True,
        },
    )


def test_delete_artifact_version_can_preserve_metadata(
    mocker: MockerFixture,
) -> None:
    """Tests requesting data deletion without metadata deletion."""
    store = mocker.Mock()
    artifact_version_id = uuid4()

    RestZenStore.delete_artifact_version(
        store,
        artifact_version_id=artifact_version_id,
        delete_metadata=False,
        delete_from_artifact_store=True,
    )

    store._delete_resource.assert_called_once_with(
        resource_id=artifact_version_id,
        route=ARTIFACT_VERSIONS,
        params={
            "delete_metadata": False,
            "delete_from_artifact_store": True,
        },
    )
