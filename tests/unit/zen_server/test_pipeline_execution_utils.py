"""Behavior tests for server-side snapshot execution."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus
from zenml.model.model import Model
from zenml.zen_server.pipeline_execution import utils
from zenml.zen_server.pipeline_execution.snapshot_run_dispatcher import (
    SnapshotRunDispatchError,
    SnapshotRunExecutionRequest,
    SnapshotRunQueueFullError,
)
from zenml.zen_server.rbac.models import Action, ResourceType


def test_invalid_snapshot_does_not_create_or_report_usage(monkeypatch) -> None:
    """Validation failures happen before preparation becomes billable."""
    create_placeholder_run = MagicMock()
    report_usage = MagicMock()
    monkeypatch.setattr(
        utils,
        "validate_snapshot_for_server_execution",
        MagicMock(side_effect=ValueError("invalid snapshot")),
    )
    monkeypatch.setattr(
        utils, "create_placeholder_run", create_placeholder_run
    )
    monkeypatch.setattr(utils, "report_usage", report_usage)
    monkeypatch.setattr(utils, "get_auth_context", MagicMock())

    with pytest.raises(ValueError, match="invalid snapshot"):
        utils.run_snapshot(
            snapshot=MagicMock(),
            auth_context=MagicMock(),
        )

    create_placeholder_run.assert_not_called()
    report_usage.assert_not_called()


def test_async_snapshot_run_returns_placeholder_after_dispatch_acceptance(
    monkeypatch,
) -> None:
    """Async snapshot runs dispatch durable IDs and return the placeholder."""
    source_snapshot = SimpleNamespace(id=uuid4())
    target_snapshot = SimpleNamespace(id=uuid4())
    placeholder_run = SimpleNamespace(id=uuid4())
    stack = MagicMock()
    dispatcher = MagicMock()
    store = MagicMock()
    usage = MagicMock()
    queued_run = SimpleNamespace(
        id=placeholder_run.id,
        status=ExecutionStatus.INITIALIZING,
        status_reason=utils.SNAPSHOT_RUN_QUEUED_STATUS_REASON,
    )
    store.update_run.return_value = queued_run

    monkeypatch.setattr(
        utils,
        "validate_snapshot_for_server_execution",
        lambda **_: (MagicMock(), stack, "1.0.0"),
    )
    monkeypatch.setattr(
        utils, "create_snapshot_from_source", lambda **_: target_snapshot
    )
    monkeypatch.setattr(
        utils, "create_placeholder_run", lambda **_: placeholder_run
    )
    monkeypatch.setattr(utils, "snapshot_run_dispatcher", lambda: dispatcher)
    monkeypatch.setattr(utils, "zen_store", lambda: store)
    monkeypatch.setattr(utils, "report_usage", usage)
    monkeypatch.setattr(utils, "get_auth_context", MagicMock())
    monkeypatch.setattr(utils, "build_runner_environment", MagicMock())
    monkeypatch.setattr(utils, "build_runner_dockerfile", MagicMock())
    monkeypatch.setattr(utils, "snapshot_executor", MagicMock())

    result = utils.run_snapshot(
        snapshot=source_snapshot,
        auth_context=MagicMock(),
        wait_runner_pod=False,
    )

    assert result is queued_run
    dispatcher.submit.assert_called_once_with(
        SnapshotRunExecutionRequest(
            run_id=placeholder_run.id,
            snapshot_id=target_snapshot.id,
        )
    )
    usage.assert_called_once_with(
        feature=utils.RUN_TEMPLATE_TRIGGERS_FEATURE_NAME,
        resource_id=placeholder_run.id,
    )


def test_synchronous_snapshot_run_executes_without_redispatch(
    monkeypatch,
) -> None:
    """Synchronous runs report usage and expose submission outcomes."""
    snapshot = SimpleNamespace(id=uuid4(), source_snapshot_id=None)
    placeholder_run = SimpleNamespace(
        id=uuid4(),
        snapshot=snapshot,
        status=ExecutionStatus.INITIALIZING,
        trigger=None,
        original_run=None,
    )
    build = MagicMock()
    stack = MagicMock()
    auth_context = MagicMock()
    dispatcher = MagicMock()
    store = MagicMock()
    store.get_run.return_value = placeholder_run
    store.get_snapshot.return_value = snapshot
    usage = MagicMock()
    validate = MagicMock(return_value=(build, stack, "1.0.0"))
    build_and_run = MagicMock()
    analytics_handler = MagicMock(metadata={})
    analytics_context = MagicMock()
    analytics_context.__enter__.return_value = analytics_handler

    monkeypatch.setattr(
        utils, "validate_snapshot_for_server_execution", validate
    )
    monkeypatch.setattr(
        utils, "create_placeholder_run", lambda **_: placeholder_run
    )
    monkeypatch.setattr(utils, "snapshot_run_dispatcher", lambda: dispatcher)
    monkeypatch.setattr(utils, "zen_store", lambda: store)
    monkeypatch.setattr(utils, "get_auth_context", MagicMock())
    monkeypatch.setattr(utils, "report_usage", usage)
    monkeypatch.setattr(utils, "set_auth_context", MagicMock())
    monkeypatch.setattr(utils, "build_runner_environment", MagicMock())
    monkeypatch.setattr(utils, "build_runner_dockerfile", MagicMock())
    monkeypatch.setattr(
        utils,
        "get_pipeline_run_analytics_metadata",
        MagicMock(return_value={}),
    )
    monkeypatch.setattr(utils, "track_handler", lambda **_: analytics_context)
    monkeypatch.setattr(utils, "_build_and_run", build_and_run)

    result = utils.run_snapshot(
        snapshot=snapshot,
        auth_context=auth_context,
        create_new_snapshot=False,
        sync=True,
    )

    assert result is placeholder_run
    usage.assert_called_once_with(
        feature=utils.RUN_TEMPLATE_TRIGGERS_FEATURE_NAME,
        resource_id=placeholder_run.id,
    )
    assert validate.call_count == 2
    assert store.get_run.call_count == 2
    store.get_snapshot.assert_called_once_with(
        snapshot_id=snapshot.id, hydrate=True
    )
    build_and_run.assert_called_once()
    dispatcher.submit.assert_not_called()

    build_and_run.side_effect = RuntimeError("infrastructure failure")
    store.get_run_status.return_value = ExecutionStatus.INITIALIZING
    with pytest.raises(RuntimeError, match="Failed to start pipeline run"):
        utils.run_snapshot(
            snapshot=snapshot,
            auth_context=auth_context,
            create_new_snapshot=False,
            sync=True,
        )

    assert usage.call_count == 2
    failed_update = store.update_run.call_args.kwargs["run_update"]
    assert failed_update.status == ExecutionStatus.FAILED


@pytest.mark.parametrize("create_new_snapshot", [True, False])
def test_queue_rejection_removes_prepared_state(
    monkeypatch, create_new_snapshot: bool
) -> None:
    """Queue backpressure only removes state created by the request."""
    source_snapshot = SimpleNamespace(id=uuid4())
    target_snapshot = SimpleNamespace(id=uuid4())
    placeholder_run = SimpleNamespace(id=uuid4())
    store = MagicMock()
    dispatcher = MagicMock()
    dispatcher.submit.side_effect = SnapshotRunQueueFullError("full")
    usage = MagicMock()

    monkeypatch.setattr(
        utils,
        "validate_snapshot_for_server_execution",
        lambda **_: (MagicMock(), MagicMock(), "1.0.0"),
    )
    monkeypatch.setattr(
        utils, "create_snapshot_from_source", lambda **_: target_snapshot
    )
    monkeypatch.setattr(
        utils, "create_placeholder_run", lambda **_: placeholder_run
    )
    monkeypatch.setattr(utils, "snapshot_run_dispatcher", lambda: dispatcher)
    monkeypatch.setattr(utils, "zen_store", lambda: store)
    monkeypatch.setattr(utils, "get_auth_context", MagicMock())
    monkeypatch.setattr(utils, "report_usage", usage)

    with pytest.raises(SnapshotRunQueueFullError, match="full"):
        utils.run_snapshot(
            snapshot=source_snapshot,
            auth_context=MagicMock(),
            create_new_snapshot=create_new_snapshot,
        )

    store.delete_run.assert_called_once_with(run_id=placeholder_run.id)
    if create_new_snapshot:
        store.delete_snapshot.assert_called_once_with(
            snapshot_id=target_snapshot.id
        )
    else:
        store.delete_snapshot.assert_not_called()
    store.update_run.assert_called_once()
    usage.assert_called_once_with(
        feature=utils.RUN_TEMPLATE_TRIGGERS_FEATURE_NAME,
        resource_id=placeholder_run.id,
    )


def test_unexpected_dispatch_failure_marks_prepared_run_failed(
    monkeypatch,
) -> None:
    """Unexpected dispatch failures retain a diagnosable failed run."""
    source_snapshot = SimpleNamespace(id=uuid4())
    target_snapshot = SimpleNamespace(id=uuid4())
    placeholder_run = SimpleNamespace(id=uuid4())
    store = MagicMock()
    dispatcher = MagicMock()
    dispatcher.submit.side_effect = RuntimeError("redis unavailable")

    monkeypatch.setattr(
        utils,
        "validate_snapshot_for_server_execution",
        lambda **_: (MagicMock(), MagicMock(), "1.0.0"),
    )
    monkeypatch.setattr(
        utils, "create_snapshot_from_source", lambda **_: target_snapshot
    )
    monkeypatch.setattr(
        utils, "create_placeholder_run", lambda **_: placeholder_run
    )
    monkeypatch.setattr(utils, "snapshot_run_dispatcher", lambda: dispatcher)
    monkeypatch.setattr(utils, "zen_store", lambda: store)
    monkeypatch.setattr(utils, "get_auth_context", MagicMock())
    monkeypatch.setattr(utils, "report_usage", MagicMock())

    with pytest.raises(
        SnapshotRunDispatchError,
        match="Failed to queue snapshot execution request",
    ):
        utils.run_snapshot(
            snapshot=source_snapshot,
            auth_context=MagicMock(),
        )

    failed_update = store.update_run.call_args_list[-1].kwargs["run_update"]
    assert failed_update.status == ExecutionStatus.FAILED
    assert failed_update.status_reason == "Failed to queue run."
    store.delete_run.assert_not_called()
    store.delete_snapshot.assert_not_called()


def test_prepared_execution_uses_persisted_run_owner(monkeypatch) -> None:
    """Remote execution reconstructs identity from the placeholder owner."""
    source_snapshot_id = uuid4()
    target_snapshot = SimpleNamespace(
        id=uuid4(), source_snapshot_id=source_snapshot_id
    )
    owner = object()
    run = SimpleNamespace(
        id=uuid4(),
        status=ExecutionStatus.INITIALIZING,
        snapshot=target_snapshot,
        user=owner,
        trigger=None,
        original_run=None,
    )
    store = MagicMock()
    store.get_run.return_value = run
    store.get_snapshot.return_value = target_snapshot
    set_auth_context = MagicMock()
    build_and_run = MagicMock()
    execution_auth = SimpleNamespace(user=owner)
    analytics_handler = MagicMock(metadata={})
    analytics_context = MagicMock()
    analytics_context.__enter__.return_value = analytics_handler

    monkeypatch.setattr(utils, "zen_store", lambda: store)
    monkeypatch.setattr(utils, "AuthContext", lambda user: execution_auth)
    monkeypatch.setattr(utils, "set_auth_context", set_auth_context)
    monkeypatch.setattr(
        utils,
        "validate_snapshot_for_server_execution",
        lambda **_: (MagicMock(), MagicMock(), "1.0.0"),
    )
    monkeypatch.setattr(utils, "build_runner_environment", MagicMock())
    monkeypatch.setattr(utils, "build_runner_dockerfile", MagicMock())
    monkeypatch.setattr(
        utils.RunnerEntrypointConfiguration,
        "get_entrypoint_command",
        MagicMock(return_value=["run"]),
    )
    monkeypatch.setattr(
        utils.RunnerEntrypointConfiguration,
        "get_entrypoint_arguments",
        MagicMock(return_value=["args"]),
    )
    monkeypatch.setattr(
        utils,
        "get_pipeline_run_analytics_metadata",
        MagicMock(return_value={}),
    )
    monkeypatch.setattr(utils, "track_handler", lambda **_: analytics_context)
    monkeypatch.setattr(utils, "_build_and_run", build_and_run)

    executed = utils.execute_snapshot_run(
        SnapshotRunExecutionRequest(
            run_id=run.id,
            snapshot_id=target_snapshot.id,
        )
    )

    assert executed is True
    set_auth_context.assert_called_once_with(execution_auth)
    build_and_run.assert_called_once()
    assert build_and_run.call_args.kwargs["wait_for_completion"] is True


def test_prepared_execution_skips_stale_or_missing_state(monkeypatch) -> None:
    """Stale and missing queued state is acknowledged without execution."""
    stale_run = SimpleNamespace(id=uuid4(), status=ExecutionStatus.CANCELLED)
    store = MagicMock()
    store.get_run.return_value = stale_run
    build_and_run = MagicMock()
    monkeypatch.setattr(utils, "zen_store", lambda: store)
    monkeypatch.setattr(utils, "_build_and_run", build_and_run)

    executed = utils.execute_snapshot_run(
        SnapshotRunExecutionRequest(
            run_id=stale_run.id,
            snapshot_id=uuid4(),
        )
    )

    assert executed is False
    store.get_snapshot.assert_not_called()
    build_and_run.assert_not_called()

    initializing_run = SimpleNamespace(
        id=uuid4(), status=ExecutionStatus.INITIALIZING
    )
    store.reset_mock()
    store.get_run.return_value = initializing_run
    store.get_snapshot.side_effect = KeyError("missing")

    executed = utils.execute_snapshot_run(
        SnapshotRunExecutionRequest(
            run_id=initializing_run.id,
            snapshot_id=uuid4(),
        )
    )

    assert executed is False
    store.update_run.assert_not_called()
    build_and_run.assert_not_called()


def test_generate_dockerfile_pins_zenml_in_image():
    """Tests that the runner image install pins the image's ZenML version."""
    from zenml.utils import requirements_utils

    dockerfile = utils.generate_dockerfile(
        pypi_requirements=["sagemaker"],
        apt_packages=[],
        zenml_version="0.98.1",
        python_version="3.12",
    )

    assert dockerfile.endswith(
        f"'sagemaker' {requirements_utils.INSTALLED_ZENML_SHELL_REQUIREMENT}"
    )


def _snapshot_with_models(pipeline_model=None, step_model=None):
    """Builds a minimal snapshot exposing only the model configuration."""
    return SimpleNamespace(
        project_id=uuid4(),
        pipeline_configuration=SimpleNamespace(model=pipeline_model),
        step_configurations={
            "step": SimpleNamespace(
                step_config_overrides=SimpleNamespace(model=step_model)
            )
        },
    )


@pytest.mark.parametrize(
    "version",
    [None, "my-new-version", "1.2.3"],
)
def test_model_version_create_permission_required_for_new_versions(
    monkeypatch, version
) -> None:
    """Runs that create a model version require `ModelVersion::CREATE`."""
    verify_permission = MagicMock()
    monkeypatch.setattr(utils, "verify_permission", verify_permission)
    snapshot = _snapshot_with_models(
        pipeline_model=Model(name="model", version=version)
    )

    utils.verify_model_version_permissions_for_snapshot_run(snapshot)

    verify_permission.assert_called_once_with(
        resource_type=ResourceType.MODEL_VERSION,
        action=Action.CREATE,
        project_id=snapshot.project_id,
    )


@pytest.mark.parametrize("version", ["3", 3, "production", "latest"])
def test_model_version_create_permission_not_required_for_existing_versions(
    monkeypatch, version
) -> None:
    """Numeric versions and stages are only fetched, never created."""
    verify_permission = MagicMock()
    monkeypatch.setattr(utils, "verify_permission", verify_permission)
    snapshot = _snapshot_with_models(
        pipeline_model=Model(name="model", version=version)
    )

    utils.verify_model_version_permissions_for_snapshot_run(snapshot)

    verify_permission.assert_not_called()


def test_model_version_create_permission_not_required_without_model(
    monkeypatch,
) -> None:
    """Snapshots without any configured model need no extra permission."""
    verify_permission = MagicMock()
    monkeypatch.setattr(utils, "verify_permission", verify_permission)

    utils.verify_model_version_permissions_for_snapshot_run(
        _snapshot_with_models()
    )

    verify_permission.assert_not_called()


def test_model_version_create_permission_checked_for_step_models(
    monkeypatch,
) -> None:
    """A step-level model that creates a version is checked exactly once."""
    verify_permission = MagicMock()
    monkeypatch.setattr(utils, "verify_permission", verify_permission)
    snapshot = _snapshot_with_models(
        pipeline_model=Model(name="model", version="1"),
        step_model=Model(name="step-model"),
    )

    utils.verify_model_version_permissions_for_snapshot_run(snapshot)

    verify_permission.assert_called_once()


def test_run_configuration_model_overrides_snapshot_model(
    monkeypatch,
) -> None:
    """The run configuration model replaces the snapshot's model."""
    verify_permission = MagicMock()
    monkeypatch.setattr(utils, "verify_permission", verify_permission)
    snapshot = _snapshot_with_models(
        pipeline_model=Model(name="model", version=None)
    )
    run_configuration = SimpleNamespace(
        model=Model(name="model", version="production"), steps=None
    )

    utils.verify_model_version_permissions_for_snapshot_run(
        snapshot, run_configuration
    )

    verify_permission.assert_not_called()
