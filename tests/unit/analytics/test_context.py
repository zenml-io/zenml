"""Email attribution on regular pipeline analytics events."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from zenml.analytics import context as context_module
from zenml.analytics.context import AnalyticsContext
from zenml.analytics.enums import AnalyticsEvent


@pytest.mark.parametrize("hosted", [False, True])
@pytest.mark.parametrize("email", [None, "person@example.com"])
@pytest.mark.parametrize(
    "event", [AnalyticsEvent.RUN_PIPELINE, AnalyticsEvent.RUN_PIPELINE_ENDED]
)
def test_pipeline_event_uses_actual_email_and_preserves_ids(
    monkeypatch: pytest.MonkeyPatch,
    hosted: bool,
    email: str | None,
    event: AnalyticsEvent,
) -> None:
    """Set only a known actor email and preserve existing event identity."""
    local_id = uuid4()
    cloud_id = uuid4() if hosted else None
    analytics = AnalyticsContext()
    analytics.analytics_opt_in = True
    analytics.user_id = local_id
    analytics.external_user_id = cloud_id
    analytics.email = email
    analytics.project_id = uuid4()
    analytics.server_metadata = {"email": "another-person@example.com"}
    track = Mock(return_value=(True, ""))
    monkeypatch.setattr(context_module.default_client, "track", track)
    assert analytics.track(
        event, {"pipeline_run_id": uuid4(), "email": "stale@example.com"}
    )
    track.assert_called_once()
    assert track.call_args.kwargs["user_id"] == local_id
    assert track.call_args.kwargs["event"] is event
    properties = track.call_args.kwargs["properties"]
    assert properties["user_id"] == str(local_id)
    if email is None:
        assert "email" not in properties
    else:
        assert properties["email"] == email
    assert "cloud_user_id" not in properties
    if cloud_id is not None:
        assert properties["external_user_id"] == str(cloud_id)
    else:
        assert "external_user_id" not in properties


@pytest.mark.parametrize("server", [False, True])
@pytest.mark.parametrize("email", [None, "actor@example.com"])
def test_context_loads_email_from_current_user(
    monkeypatch: pytest.MonkeyPatch, server: bool, email: str | None
) -> None:
    """Both server and client events use the current actor's contact email."""
    from zenml import client as client_module
    from zenml.config import global_config
    from zenml.zen_server import utils as server_utils

    user = SimpleNamespace(
        id=uuid4(),
        external_user_id=uuid4(),
        is_service_account=False,
        email=email,
    )
    store_info = SimpleNamespace(
        analytics_enabled=True,
        id=uuid4(),
        deployment_type="cloud",
        database_type="sqlite",
        metadata={},
        is_local=lambda: not server,
    )
    gc = SimpleNamespace(
        is_initialized=True,
        analytics_opt_in=True,
        user_id=uuid4(),
        zen_store=SimpleNamespace(
            get_store_info=lambda: store_info, get_user=lambda: user
        ),
    )
    monkeypatch.setattr(global_config, "GlobalConfiguration", lambda: gc)
    monkeypatch.setattr(
        AnalyticsContext, "in_server", property(lambda self: server)
    )
    monkeypatch.setattr(
        server_utils, "get_auth_context", lambda: SimpleNamespace(user=user)
    )
    monkeypatch.setattr(
        server_utils,
        "server_config",
        lambda: SimpleNamespace(external_server_id=uuid4()),
    )
    monkeypatch.setattr(
        client_module,
        "Client",
        lambda: SimpleNamespace(active_project=SimpleNamespace(id=uuid4())),
    )
    monkeypatch.setattr(
        context_module, "is_analytics_disabled_internally", lambda: False
    )
    track = Mock(return_value=(True, ""))
    monkeypatch.setattr(context_module.default_client, "track", track)
    with AnalyticsContext() as analytics:
        assert analytics.track(AnalyticsEvent.RUN_PIPELINE_ENDED)
    assert track.call_args.kwargs["user_id"] == user.id
    properties = track.call_args.kwargs["properties"]
    if email is None:
        assert "email" not in properties
    else:
        assert properties["email"] == email
    assert properties["external_user_id"] == str(user.external_user_id)


def test_unrelated_event_keeps_existing_email_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not change profile or opt-in event recipient semantics."""
    analytics = AnalyticsContext()
    analytics.analytics_opt_in = True
    analytics.user_id = uuid4()
    analytics.email = "actor@example.com"
    analytics.project_id = None
    track = Mock(return_value=(True, ""))
    monkeypatch.setattr(context_module.default_client, "track", track)
    assert analytics.track(
        AnalyticsEvent.USER_ENRICHED, {"email": "profile@example.com"}
    )
    assert (
        track.call_args.kwargs["properties"]["email"] == "profile@example.com"
    )


def test_pipeline_tracking_still_requires_analytics_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Adding email does not bypass the existing analytics opt-in guard."""
    analytics = AnalyticsContext()
    analytics.user_id = uuid4()
    analytics.email = "actor@example.com"
    track = Mock()
    monkeypatch.setattr(context_module.default_client, "track", track)
    assert not analytics.track(AnalyticsEvent.RUN_PIPELINE_ENDED)
    track.assert_not_called()
