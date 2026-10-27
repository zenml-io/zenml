"""Cancellation unwinds through the actual step runner without failure writes."""

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from zenml.enums import ExecutionStatus, HookType
from zenml.exceptions import RunStoppedException
from zenml.orchestrators import step_runner
from zenml.orchestrators.step_runner import StepRunner
from zenml.steps.heartbeat import StepHeartBeatTerminationException


@pytest.mark.parametrize(
    "error_type,status,heartbeat_terminated,expected_type,publish_failure,clean_stop,publish_fails",
    [
        (
            RunStoppedException,
            ExecutionStatus.STOPPED,
            False,
            RunStoppedException,
            False,
            True,
            False,
        ),
        (
            KeyboardInterrupt,
            ExecutionStatus.STOPPED,
            True,
            StepHeartBeatTerminationException,
            False,
            True,
            False,
        ),
    ],
)
def test_step_exception_preserves_terminal_state_and_classification(
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[BaseException],
    status: ExecutionStatus,
    heartbeat_terminated: bool,
    expected_type: type[BaseException],
    publish_failure: bool,
    clean_stop: bool,
    publish_fails: bool,
) -> None:
    """Signal and heartbeat cancellation never repeat a terminal status write.

    Args:
        monkeypatch: Fixture for replacing external collaborators.
        error_type: Exception raised by the step.
        status: Stored execution status.
        heartbeat_terminated: Whether the heartbeat observed cancellation.
        expected_type: Expected exception propagated by the runner.
        publish_failure: Whether failure should be published.
        clean_stop: Whether the end hook receives a cancellation.
        publish_fails: Whether failure publication raises.
    """
    config = SimpleNamespace(
        start_hook_source=None, end_hook_source=None, failure_hook_source=None
    )
    step = SimpleNamespace(
        config=config, spec=SimpleNamespace(enable_heartbeat=True)
    )
    stack = Mock()
    stack.orchestrator.run_init_cleanup_at_step_level = False
    runner = StepRunner(step=step, stack=stack)
    error = error_type("original step exception")
    step_instance = SimpleNamespace(
        entrypoint=lambda: None, call_entrypoint=Mock(side_effect=error)
    )
    attempt = SimpleNamespace(
        id=uuid4(),
        name="step",
        config=config,
        status=status,
        is_retriable=False,
    )
    heartbeat = Mock(is_terminated=heartbeat_terminated)
    client = Mock(get_run_step=Mock(return_value=attempt))
    publish = Mock(return_value=attempt)
    if publish_fails:
        publish.side_effect = RuntimeError("Failure publication unavailable")
    hooks = Mock()

    monkeypatch.setattr(runner, "_load_step", lambda: step_instance)
    monkeypatch.setattr(runner, "_load_output_materializers", lambda: {})
    monkeypatch.setattr(
        runner, "_evaluate_artifact_names_in_collections", Mock()
    )
    monkeypatch.setattr(runner, "_parse_inputs", lambda **kwargs: {})
    monkeypatch.setattr(runner, "_fire_step_hook", hooks)
    monkeypatch.setattr(
        step_runner, "is_step_logging_enabled", lambda **kwargs: False
    )
    monkeypatch.setattr(
        step_runner, "parse_return_type_annotations", lambda **kwargs: {}
    )
    monkeypatch.setattr(
        step_runner, "StepContext", lambda **kwargs: nullcontext()
    )
    monkeypatch.setattr(
        step_runner, "StepHeartbeatWorker", lambda **kwargs: heartbeat
    )
    monkeypatch.setattr(step_runner, "Client", lambda: client)
    monkeypatch.setattr(step_runner, "publish_failed_step_run", publish)
    monkeypatch.setattr(step_runner, "publish_step_run_metadata", Mock())
    monkeypatch.setattr(
        step_runner.env_utils, "get_runtime_environment", lambda **kwargs: {}
    )
    monkeypatch.setattr(
        step_runner.env_utils,
        "get_runtime_secret_environment",
        lambda **kwargs: {},
    )

    with pytest.raises(expected_type) as caught:
        runner.run(
            pipeline_run=SimpleNamespace(config=config),
            step_run=attempt,
            input_artifacts={},
            output_artifact_uris={},
            step_run_info=SimpleNamespace(step_run_id=attempt.id),
        )

    if expected_type is error_type:
        assert caught.value is error
    assert publish.call_count == int(publish_failure)
    client.zen_store.update_run_step.assert_not_called()
    end_hook = next(
        call
        for call in hooks.call_args_list
        if call.args[1] == HookType.STEP_END
    )
    assert end_hook.kwargs["optional_args"] == (
        (None,) if clean_stop else (error,)
    )
    heartbeat.stop.assert_called_once()
    stack.cleanup_step_run.assert_called_once()
