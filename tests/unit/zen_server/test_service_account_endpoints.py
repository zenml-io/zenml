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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Regression tests for cleanup of deprecated workspace credentials."""

from types import SimpleNamespace
from typing import Tuple
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.enums import AuthScheme
from zenml.exceptions import CredentialsNotValid, IllegalOperationError
from zenml.models import (
    APIKeyInternalResponse,
    APIKeyRequest,
    APIKeyRotateRequest,
    APIKeyUpdate,
    ServiceAccountRequest,
    ServiceAccountUpdate,
    UserResponse,
)
from zenml.models.v2.core.api_key import APIKey
from zenml.zen_server import auth
from zenml.zen_server.rbac.models import Action
from zenml.zen_server.routers import service_accounts_endpoints as endpoints


@pytest.fixture
def cleanup_server(
    monkeypatch: pytest.MonkeyPatch,
) -> Tuple[MagicMock, MagicMock]:
    """Provide an external-auth server with mocked persistence and RBAC.

    Args:
        monkeypatch: Pytest patch manager.

    Returns:
        The store and model permission check.
    """
    store = MagicMock()
    store.get_service_account.return_value.external_user_id = None
    permission_check = MagicMock()
    monkeypatch.setattr(endpoints, "zen_store", lambda: store)
    monkeypatch.setattr(
        endpoints,
        "server_config",
        lambda: MagicMock(auth_scheme=AuthScheme.EXTERNAL),
    )
    monkeypatch.setattr(
        endpoints, "verify_permission_for_model", permission_check
    )
    monkeypatch.setattr(
        endpoints, "verify_admin_status_if_no_rbac", MagicMock()
    )
    monkeypatch.setattr(endpoints, "delete_model_resource", MagicMock())
    return store, permission_check


@pytest.mark.parametrize("active", [False, True])
def test_update_workspace_account_active_status(
    cleanup_server: Tuple[MagicMock, MagicMock],
    active: bool,
) -> None:
    """A workspace account can change active status without removing resources.

    Args:
        cleanup_server: Mocked server dependencies.
        active: The requested account status.
    """
    store, permission_check = cleanup_server
    account_id = uuid4()
    update = ServiceAccountUpdate(active=active, name=None, description=None)

    result = endpoints.update_service_account.__wrapped__(
        account_id, update, auth_context=MagicMock()
    )

    assert result is store.update_service_account.return_value
    permission_check.assert_called_once_with(
        store.get_service_account.return_value, action=Action.UPDATE
    )
    store.update_service_account.assert_called_once_with(account_id, update)
    store.delete_service_account.assert_not_called()


@pytest.mark.parametrize("adopted", [False, True])
@pytest.mark.parametrize("active", [False, True])
def test_update_legacy_key_active_status(
    cleanup_server: Tuple[MagicMock, MagicMock], adopted: bool, active: bool
) -> None:
    """Legacy keys can change active status before or after account adoption.

    Args:
        cleanup_server: Mocked server dependencies.
        adopted: Whether the key belongs to an adopted service account.
        active: The requested key status.
    """
    store, permission_check = cleanup_server
    if adopted:
        store.get_service_account.return_value.external_user_id = uuid4()
    account_id, key_id = uuid4(), uuid4()
    update = APIKeyUpdate(active=active, name=None, description=None)

    result = endpoints.update_api_key.__wrapped__(
        account_id, key_id, update, auth_context=MagicMock()
    )

    assert result is store.update_api_key.return_value
    permission_check.assert_called_once_with(
        store.get_service_account.return_value, action=Action.UPDATE
    )
    store.update_api_key.assert_called_once_with(
        service_account_id=account_id,
        api_key_name_or_id=key_id,
        api_key_update=update,
    )


@pytest.mark.parametrize(
    ("operation", "adopted"),
    [("account", False), ("key", False), ("key", True)],
)
def test_status_changes_allow_migration_rollback(
    cleanup_server: Tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    adopted: bool,
) -> None:
    """Deactivation rejects the old key, and reactivation restores access.

    Args:
        cleanup_server: Mocked server dependencies.
        monkeypatch: Pytest patch manager.
        operation: The resource to deactivate.
        adopted: Whether the service account has been adopted.
    """
    store, _ = cleanup_server
    account = store.get_service_account.return_value
    account.active = True
    if adopted:
        account.external_user_id = uuid4()
    user = UserResponse.model_construct(id=uuid4(), name="legacy")
    account.to_user_model.return_value = user
    key_body = SimpleNamespace(active=True, service_account=account)
    key = APIKeyInternalResponse.model_construct(
        id=uuid4(), name="legacy-key", body=key_body
    )
    store.get_internal_api_key.return_value = key
    monkeypatch.setattr(
        APIKeyInternalResponse,
        "verify_key",
        lambda self, secret: secret == "valid",
    )
    monkeypatch.setattr(auth, "zen_store", lambda: store)
    monkeypatch.setattr(auth, "server_config", endpoints.server_config)
    encoded_key = APIKey(id=key.id, key="valid").encode()
    assert auth.authenticate_api_key(encoded_key).user is user
    if operation == "account":
        store.update_service_account.side_effect = lambda _, update: setattr(
            account, "active", update.active
        )
        endpoints.update_service_account.__wrapped__(
            uuid4(),
            ServiceAccountUpdate(active=False),
            auth_context=MagicMock(),
        )
    else:
        store.update_api_key.side_effect = lambda **kwargs: setattr(
            key_body, "active", kwargs["api_key_update"].active
        )
        endpoints.update_api_key.__wrapped__(
            uuid4(),
            uuid4(),
            APIKeyUpdate(active=False),
            auth_context=MagicMock(),
        )
    with pytest.raises(CredentialsNotValid, match="not active"):
        auth.authenticate_api_key(encoded_key)

    if operation == "account":
        endpoints.update_service_account.__wrapped__(
            uuid4(),
            ServiceAccountUpdate(active=True),
            auth_context=MagicMock(),
        )
    else:
        endpoints.update_api_key.__wrapped__(
            uuid4(),
            key.id,
            APIKeyUpdate(active=True),
            auth_context=MagicMock(),
        )
    restored_context = auth.authenticate_api_key(encoded_key)
    assert restored_context.user is user
    assert restored_context.api_key is key


@pytest.mark.parametrize(
    "update",
    [
        ServiceAccountUpdate(),
        ServiceAccountUpdate(name="renamed"),
        ServiceAccountUpdate(active=False, name="renamed"),
        ServiceAccountUpdate(active=True, name="renamed"),
        ServiceAccountUpdate(active=False, description=""),
        ServiceAccountUpdate(active=False, full_name=""),
        ServiceAccountUpdate(active=False, avatar_url="avatar"),
    ],
)
def test_pro_account_updates_remain_blocked(
    cleanup_server: Tuple[MagicMock, MagicMock], update: ServiceAccountUpdate
) -> None:
    """Status changes cannot be combined with another account modification.

    Args:
        cleanup_server: Mocked server dependencies.
        update: A prohibited account update.
    """
    store, _ = cleanup_server
    with pytest.raises(IllegalOperationError, match="deprecated"):
        endpoints.update_service_account.__wrapped__(
            uuid4(), update, auth_context=MagicMock()
        )
    store.update_service_account.assert_not_called()


@pytest.mark.parametrize("adopted", [False, True])
@pytest.mark.parametrize(
    "update",
    [
        APIKeyUpdate(),
        APIKeyUpdate(name="renamed"),
        APIKeyUpdate(active=False, name="renamed"),
        APIKeyUpdate(active=True, name="renamed"),
        APIKeyUpdate(active=False, description=""),
    ],
)
def test_pro_key_updates_remain_blocked(
    cleanup_server: Tuple[MagicMock, MagicMock],
    update: APIKeyUpdate,
    adopted: bool,
) -> None:
    """Key status changes do not allow general modifications.

    Args:
        cleanup_server: Mocked server dependencies.
        update: A prohibited API key update.
        adopted: Whether the service account has been adopted.
    """
    store, _ = cleanup_server
    if adopted:
        store.get_service_account.return_value.external_user_id = uuid4()
    with pytest.raises(IllegalOperationError, match="deprecated"):
        endpoints.update_api_key.__wrapped__(
            uuid4(), uuid4(), update, auth_context=MagicMock()
        )
    store.update_api_key.assert_not_called()


@pytest.mark.parametrize(
    "operation", ["create_account", "create_key", "rotate"]
)
def test_pro_credential_creation_remains_blocked(
    cleanup_server: Tuple[MagicMock, MagicMock], operation: str
) -> None:
    """Cleanup does not reopen creation or rotation of workspace credentials.

    Args:
        cleanup_server: Mocked server dependencies.
        operation: The prohibited credential operation.
    """
    store, _ = cleanup_server
    with pytest.raises(IllegalOperationError, match="deprecated"):
        if operation == "create_account":
            endpoints.create_service_account.__wrapped__(
                ServiceAccountRequest(name="legacy", active=True),
                auth_context=MagicMock(),
            )
        elif operation == "create_key":
            endpoints.create_api_key.__wrapped__(
                uuid4(), APIKeyRequest(name="key"), auth_context=MagicMock()
            )
        else:
            endpoints.rotate_api_key.__wrapped__(
                uuid4(),
                uuid4(),
                APIKeyRotateRequest(),
                auth_context=MagicMock(),
            )
    store.create_service_account.assert_not_called()
    store.create_api_key.assert_not_called()
    store.rotate_api_key.assert_not_called()


@pytest.mark.parametrize("operation", ["deactivate", "reactivate", "delete"])
def test_adopted_accounts_remain_org_managed(
    cleanup_server: Tuple[MagicMock, MagicMock], operation: str
) -> None:
    """Account adoption does not allow local lifecycle changes.

    Args:
        cleanup_server: Mocked server dependencies.
        operation: The attempted account operation.
    """
    store, _ = cleanup_server
    store.get_service_account.return_value.external_user_id = uuid4()
    with pytest.raises(IllegalOperationError, match="external authentication"):
        if operation != "delete":
            endpoints.update_service_account.__wrapped__(
                uuid4(),
                ServiceAccountUpdate(active=operation == "reactivate"),
                auth_context=MagicMock(),
            )
        else:
            endpoints.delete_service_account.__wrapped__(
                uuid4(), auth_context=MagicMock()
            )
    store.update_service_account.assert_not_called()
    store.delete_service_account.assert_not_called()


@pytest.mark.parametrize("operation", ["account", "key"])
@pytest.mark.parametrize("permission_gate", ["rbac", "admin"])
@pytest.mark.parametrize("active", [False, True])
def test_status_changes_preserve_authorization(
    cleanup_server: Tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    permission_gate: str,
    active: bool,
) -> None:
    """Activation and deactivation require the existing authorization checks.

    Args:
        cleanup_server: Mocked server dependencies.
        monkeypatch: Pytest patch manager.
        operation: The resource to update.
        permission_gate: The authorization check that denies the request.
        active: The requested active status.
    """
    store, permission_check = cleanup_server
    if permission_gate == "admin":
        monkeypatch.setattr(
            endpoints,
            "verify_admin_status_if_no_rbac",
            MagicMock(side_effect=IllegalOperationError("forbidden")),
        )
    else:
        permission_check.side_effect = IllegalOperationError("forbidden")
    with pytest.raises(IllegalOperationError, match="forbidden"):
        if operation == "account":
            endpoints.update_service_account.__wrapped__(
                uuid4(),
                ServiceAccountUpdate(active=active),
                auth_context=MagicMock(),
            )
        else:
            endpoints.update_api_key.__wrapped__(
                uuid4(),
                uuid4(),
                APIKeyUpdate(active=active),
                auth_context=MagicMock(),
            )
    store.update_service_account.assert_not_called()
    store.update_api_key.assert_not_called()


@pytest.mark.parametrize("owns_resources", [False, True])
def test_legacy_account_deletion_preserves_store_guard(
    cleanup_server: Tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    owns_resources: bool,
) -> None:
    """Deletion remains available but must honor the store's ownership check.

    Args:
        cleanup_server: Mocked server dependencies.
        monkeypatch: Pytest patch manager.
        owns_resources: Whether the store rejects deletion due to ownership.
    """
    store, permission_check = cleanup_server
    delete_resource = MagicMock()
    monkeypatch.setattr(endpoints, "delete_model_resource", delete_resource)
    account_id = uuid4()
    if owns_resources:
        store.delete_service_account.side_effect = IllegalOperationError(
            "owns resources"
        )
        with pytest.raises(IllegalOperationError, match="owns resources"):
            endpoints.delete_service_account.__wrapped__(
                account_id, auth_context=MagicMock()
            )
        delete_resource.assert_not_called()
    else:
        endpoints.delete_service_account.__wrapped__(
            account_id, auth_context=MagicMock()
        )
        delete_resource.assert_called_once_with(
            store.get_service_account.return_value
        )
    permission_check.assert_called_once_with(
        store.get_service_account.return_value, action=Action.DELETE
    )
    store.delete_service_account.assert_called_once_with(account_id)


@pytest.mark.parametrize("adopted", [False, True])
def test_legacy_key_deletion_remains_available(
    cleanup_server: Tuple[MagicMock, MagicMock], adopted: bool
) -> None:
    """Existing legacy keys can be deleted even after account adoption.

    Args:
        cleanup_server: Mocked server dependencies.
        adopted: Whether the service account has been adopted.
    """
    store, permission_check = cleanup_server
    if adopted:
        store.get_service_account.return_value.external_user_id = uuid4()
    account_id, key_id = uuid4(), uuid4()
    endpoints.delete_api_key.__wrapped__(
        account_id, key_id, auth_context=MagicMock()
    )
    permission_check.assert_called_once_with(
        store.get_service_account.return_value, action=Action.UPDATE
    )
    store.delete_api_key.assert_called_once_with(
        service_account_id=account_id, api_key_name_or_id=key_id
    )


def test_oss_account_and_key_updates_are_unchanged(
    cleanup_server: Tuple[MagicMock, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """OSS deployments retain ordinary account and key updates.

    Args:
        cleanup_server: Mocked server dependencies.
        monkeypatch: Pytest patch manager.
    """
    store, _ = cleanup_server
    monkeypatch.setattr(
        endpoints,
        "server_config",
        lambda: MagicMock(auth_scheme=AuthScheme.OAUTH2_PASSWORD_BEARER),
    )
    account_id, key_id = uuid4(), uuid4()
    account_update = ServiceAccountUpdate(active=True, name="renamed")
    key_update = APIKeyUpdate(active=True, description="new description")
    endpoints.update_service_account.__wrapped__(
        account_id, account_update, auth_context=MagicMock()
    )
    endpoints.update_api_key.__wrapped__(
        account_id, key_id, key_update, auth_context=MagicMock()
    )
    store.update_service_account.assert_called_once_with(
        account_id, account_update
    )
    store.update_api_key.assert_called_once_with(
        service_account_id=account_id,
        api_key_name_or_id=key_id,
        api_key_update=key_update,
    )
