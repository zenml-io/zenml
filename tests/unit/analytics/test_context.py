"""Cloud identity on regular analytics events."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from zenml.analytics import context as context_module
from zenml.analytics.context import AnalyticsContext
from zenml.analytics.enums import AnalyticsEvent


@pytest.mark.parametrize("hosted", [False, True])
@pytest.mark.parametrize(
    "event", [AnalyticsEvent.RUN_PIPELINE, AnalyticsEvent.RUN_PIPELINE_ENDED]
)
def test_regular_pipeline_event_preserves_local_id_and_adds_cloud_id(
    monkeypatch: pytest.MonkeyPatch, hosted: bool, event: AnalyticsEvent
) -> None:
    """Expose a hosted actor's Cloud API ID without changing event identity."""
    local_id = uuid4()
    cloud_id = uuid4() if hosted else None
    analytics = AnalyticsContext()
    analytics.analytics_opt_in = True
    analytics.user_id = local_id
    analytics.external_user_id = cloud_id
    analytics.project_id = uuid4()
    track = Mock(return_value=(True, ""))
    monkeypatch.setattr(context_module.default_client, "track", track)
    assert analytics.track(
        event, {"pipeline_run_id": uuid4(), "cloud_user_id": str(uuid4())}
    )
    track.assert_called_once()
    assert track.call_args.kwargs["user_id"] == local_id
    assert track.call_args.kwargs["event"] is event
    properties = track.call_args.kwargs["properties"]
    assert properties["user_id"] == str(local_id)
    if cloud_id is not None:
        assert properties["cloud_user_id"] == str(cloud_id)
        assert properties["external_user_id"] == str(cloud_id)
    else:
        assert "cloud_user_id" not in properties
        assert "external_user_id" not in properties


def test_cloud_id_comes_from_event_actor_not_other_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Resource/server metadata cannot replace the authenticated actor's ID."""
    analytics = AnalyticsContext()
    analytics.analytics_opt_in = True
    analytics.user_id = uuid4()
    analytics.external_user_id = uuid4()
    analytics.project_id = None
    analytics.server_metadata = {"cloud_user_id": str(uuid4())}
    track = Mock(return_value=(True, ""))
    monkeypatch.setattr(context_module.default_client, "track", track)
    assert analytics.track(
        AnalyticsEvent.RUN_PIPELINE_ENDED, {"cloud_user_id": str(uuid4())}
    )
    assert track.call_args.kwargs["properties"]["cloud_user_id"] == str(
        analytics.external_user_id
    )


def test_server_context_uses_authenticated_actor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cloud identity follows the reporting actor, including service accounts."""
    from zenml.config import global_config
    from zenml.zen_server import utils as server_utils

    user = SimpleNamespace(
        id=uuid4(), external_user_id=uuid4(), is_service_account=True
    )
    store_info = SimpleNamespace(
        analytics_enabled=True,
        id=uuid4(),
        deployment_type="cloud",
        database_type="sqlite",
        metadata={},
        is_local=lambda: False,
    )
    gc = SimpleNamespace(
        is_initialized=True,
        zen_store=SimpleNamespace(get_store_info=lambda: store_info),
    )
    monkeypatch.setattr(global_config, "GlobalConfiguration", lambda: gc)
    monkeypatch.setattr(
        AnalyticsContext, "in_server", property(lambda self: True)
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
        context_module, "is_analytics_disabled_internally", lambda: False
    )
    track = Mock(return_value=(True, ""))
    monkeypatch.setattr(context_module.default_client, "track", track)
    with AnalyticsContext() as analytics:
        assert analytics.track(AnalyticsEvent.RUN_PIPELINE_ENDED)
    assert track.call_args.kwargs["user_id"] == user.id
    assert track.call_args.kwargs["properties"]["cloud_user_id"] == str(
        user.external_user_id
    )
    assert (
        track.call_args.kwargs["properties"]["executed_by_service_account"]
        is True
    )
