"""First successful pipeline-run analytics."""

from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.analytics.enums import AnalyticsEvent
from zenml.zen_stores.sql_zen_store import SqlZenStore


@pytest.mark.parametrize("has_previous", [False, True])
def test_first_run_event(has_previous: bool) -> None:
    user = SimpleNamespace(
        id=uuid4(),
        email="user@example.com",
        external_user_id=uuid4(),
        is_service_account=False,
    )
    run = SimpleNamespace(id=uuid4(), project_id=uuid4(), user=user)
    session = MagicMock()
    session.exec.return_value.first.return_value = (
        uuid4() if has_previous else None
    )
    store = SqlZenStore.model_construct()
    with patch(
        "zenml.zen_stores.sql_zen_store.AnalyticsContext"
    ) as context_class:
        store._track_first_pipeline_run_completed(cast(Any, run), session)
        if has_previous:
            context_class.assert_not_called()
        else:
            context = context_class.return_value.__enter__.return_value
            assert context.user_id == user.id
            assert context.external_user_id == user.external_user_id
            context.track.assert_called_once_with(
                event=AnalyticsEvent.FIRST_PIPELINE_RUN_COMPLETED,
                properties={
                    "email": user.email,
                    "pipeline_run_id": run.id,
                    "project_id": run.project_id,
                    "event_success": True,
                },
            )


@pytest.mark.parametrize("service_account", [False, True])
def test_no_human_owner_no_event(service_account: bool) -> None:
    run = SimpleNamespace(
        user=SimpleNamespace(is_service_account=True)
        if service_account
        else None
    )
    session = MagicMock()
    store = SqlZenStore.model_construct()
    with patch(
        "zenml.zen_stores.sql_zen_store.AnalyticsContext"
    ) as context_class:
        store._track_first_pipeline_run_completed(cast(Any, run), session)
        session.exec.assert_not_called()
        context_class.assert_not_called()


@pytest.mark.parametrize(
    "status,previous_status,expected",
    [
        ("completed", "running", True),
        ("failed", "running", False),
        ("completed", "completed", False),
    ],
)
def test_only_successful_transition_tracks_milestone(
    status: str, previous_status: str, expected: bool
) -> None:
    from datetime import datetime

    from zenml.enums import ExecutionStatus

    run = SimpleNamespace(
        id=uuid4(),
        project_id=uuid4(),
        status=status,
        start_time=datetime(2026, 1, 1),
        end_time=datetime(2026, 1, 1, 0, 1),
        snapshot=SimpleNamespace(
            stack=SimpleNamespace(
                components=[
                    SimpleNamespace(type="orchestrator", flavor="local"),
                    SimpleNamespace(type="artifact_store", flavor="local"),
                ]
            ),
            source_snapshot_id=None,
            step_count=1,
            is_dynamic=False,
        ),
        trigger=None,
    )
    session = MagicMock()
    store = SqlZenStore.model_construct()
    with (
        patch.object(
            SqlZenStore,
            "_update_pipeline_run_status_no_commit",
            return_value=(True, run, ExecutionStatus(previous_status)),
        ),
        patch.object(
            SqlZenStore, "_track_first_pipeline_run_completed"
        ) as milestone,
        patch.object(SqlZenStore, "_update_onboarding_state"),
        patch("zenml.zen_stores.sql_zen_store.EventDispatcher") as dispatcher,
        patch("zenml.zen_stores.sql_zen_store.track_handler"),
    ):
        dispatcher.return_value.has_handlers.return_value = False
        store._update_pipeline_run_status(run.id, session)
        assert milestone.call_count == int(expected)


def test_history_query_ignores_other_users_and_failed_runs() -> None:
    from sqlmodel import Session, SQLModel, create_engine

    from zenml.zen_stores.schemas import (
        PipelineRunSchema,
        ProjectSchema,
        UserSchema,
    )

    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        user = UserSchema(name="person", full_name="Person", active=True)
        other_user = UserSchema(name="other", full_name="Other", active=True)
        project = ProjectSchema(
            name="project", display_name="Project", description=""
        )
        session.add_all([user, other_user, project])
        session.commit()

        def make_run(
            name: str, status: str, owner: UserSchema
        ) -> PipelineRunSchema:
            return PipelineRunSchema(
                name=name,
                status=status,
                user_id=owner.id,
                project_id=project.id,
                in_progress=False,
                index=1,
                enable_heartbeat=False,
            )

        run = make_run("first-success", "completed", user)
        session.add_all(
            [
                run,
                make_run("failed", "failed", user),
                make_run("other-success", "completed", other_user),
            ]
        )
        session.commit()
        store = SqlZenStore.model_construct()
        with patch(
            "zenml.zen_stores.sql_zen_store.AnalyticsContext"
        ) as context_class:
            store._track_first_pipeline_run_completed(run, session)
            context_class.return_value.__enter__.return_value.track.assert_called_once()
            context_class.reset_mock()
            later_run = make_run("second-success", "completed", user)
            session.add(later_run)
            session.commit()
            store._track_first_pipeline_run_completed(later_run, session)
            context_class.assert_not_called()
    engine.dispose()
