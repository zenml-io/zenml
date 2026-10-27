"""Tests for workload credentials while shutdown is in progress."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from zenml.enums import AuthScheme
from zenml.exceptions import CredentialsNotValid
from zenml.models import UserResponse
from zenml.models.v2.core.user import UserResponseMetadata
from zenml.zen_server import auth


@pytest.mark.parametrize(
    "in_progress,seconds_since_end,accepted",
    [
        (True, 3600, True),
        (False, 3600, False),
        (False, 10, True),
        (False, None, False),
    ],
)
def test_workload_token_uses_activity_until_shutdown_finishes(
    monkeypatch: pytest.MonkeyPatch,
    in_progress: bool,
    seconds_since_end: int | None,
    accepted: bool,
) -> None:
    """A failed execution's old end time cannot expire an active workload."""
    now = datetime.now(timezone.utc)
    user = UserResponse.model_construct(
        id=uuid4(),
        name="test-service-account",
        body=SimpleNamespace(active=True, is_service_account=True),
        metadata=UserResponseMetadata(),
    )
    run_id = uuid4()
    token = auth.JWTToken(
        user_id=user.id, issued_at=now, pipeline_run_id=run_id
    )
    end_time = (
        now - timedelta(seconds=seconds_since_end)
        if seconds_since_end is not None
        else None
    )
    store = Mock()
    store.get_user.return_value = user
    store._check_if_run_in_progress.return_value = (in_progress, end_time)
    monkeypatch.setattr(auth, "zen_store", lambda: store)
    monkeypatch.setattr(
        auth,
        "server_config",
        lambda: SimpleNamespace(
            auth_scheme=AuthScheme.OAUTH2_PASSWORD_BEARER,
            memcache_max_capacity=100,
            memcache_default_expiry=60,
        ),
    )
    monkeypatch.setattr(
        auth.JWTToken, "decode_token", Mock(return_value=token)
    )
    monkeypatch.setenv("ZENML_WORKLOAD_TOKEN_EXPIRATION_LEEWAY", "60")

    if accepted:
        assert (
            auth.authenticate_credentials(
                access_token="synthetic"
            ).access_token
            is token
        )
    else:
        with pytest.raises(CredentialsNotValid, match="no longer valid"):
            auth.authenticate_credentials(access_token="synthetic")
    store._check_if_run_in_progress.assert_called_once_with(run_id)
