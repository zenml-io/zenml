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
"""Status source site identifiers and composition."""

from contextvars import ContextVar
from typing import Optional, Tuple

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.enums import ExecutionStatus

UNKNOWN_STATUS_SOURCE = "unknown"

# Pipeline run sites
CLIENT_PLACEHOLDER_RUN_CREATED = "client.placeholder_run_created"
CLIENT_SUBMISSION_FAILED = "client.submission_failed"
CLIENT_STEP_SKIPPED = "client.step_skipped"
STEP_LAUNCHER_RUN_CREATED = "step_launcher.run_created"
ORCHESTRATOR_PROVISIONING = "orchestrator.provisioning"
USER_STOP_REQUESTED = "user.stop_requested"
DYNAMIC_RUNNER_RUN_RESUMED = "dynamic_runner.run_resumed"
DYNAMIC_RUNNER_RUN_STARTED = "dynamic_runner.run_started"
DYNAMIC_RUNNER_RUN_FAILED = "dynamic_runner.run_failed"
DYNAMIC_RUNNER_RUN_PAUSED = "dynamic_runner.run_paused"
DYNAMIC_RUNNER_RUN_COMPLETED = "dynamic_runner.run_completed"
DYNAMIC_RUNNER_CHILD_RUN_FAILED = "dynamic_runner.child_run_failed"
CLI_RESUME = "cli.resume"
CLI_RESUME_ROLLBACK = "cli.resume_rollback"
CLI_RETRY = "cli.retry"
CLI_RETRY_ROLLBACK = "cli.retry_rollback"
REFRESH_ORCHESTRATOR_STATUS = "refresh.orchestrator_status"
KUBERNETES_ORCHESTRATOR_RUN_FAILED = "kubernetes_orchestrator.run_failed"
MODAL_ORCHESTRATOR_RUN_STOPPED = "modal_orchestrator.run_stopped"
MODAL_ORCHESTRATOR_RUN_STOPPED_AFTER_DRAIN = (
    "modal_orchestrator.run_stopped_after_drain"
)
MODAL_ORCHESTRATOR_RUN_COMPLETED = "modal_orchestrator.run_completed"
MODAL_ORCHESTRATOR_RUN_FAILED = "modal_orchestrator.run_failed"
SKYPILOT_ORCHESTRATOR_RUN_FAILED = "skypilot_orchestrator.run_failed"
SERVER_QUEUE_FAILED = "server.queue_failed"
SERVER_START_FAILED = "server.start_failed"
SERVER_WAIT_CONDITION_ABORTED = "server.wait_condition_aborted"
SERVER_WAIT_CONDITION_PAUSED = "server.wait_condition_paused"
SERVER_AUTO_RESUME = "server.auto_resume"
SERVER_AUTO_RESUME_FAILED = "server.auto_resume_failed"
SERVER_RETRY_SUPERSEDED = "server.retry_superseded"

# Step run sites
STEP_RUN_FACTORY_CREATED = "step_run_factory.created"
STEP_RUN_FACTORY_CACHE_HIT = "step_run_factory.cache_hit"
STEP_LAUNCHER_INITIAL_STATUS = "step_launcher.initial_status"
STEP_LAUNCHER_REQUEST_POPULATION_FAILED = (
    "step_launcher.request_population_failed"
)
STEP_LAUNCHER_CANCELLED_BEFORE_START = "step_launcher.cancelled_before_start"
STEP_LAUNCHER_STOPPED_ON_TERMINATION = "step_launcher.stopped_on_termination"
STEP_LAUNCHER_RUNNER_DIED_FALLBACK = "step_launcher.runner_died_fallback"
STEP_LAUNCHER_REMOTE_STEP_FINISHED = "step_launcher.remote_step_finished"
STEP_LAUNCHER_RESOURCES_ACQUIRED = "step_launcher.resources_acquired"
STEP_RUNNER_SUCCESS = "step_runner.success"
STEP_RUNNER_USER_CODE_FAILED = "step_runner.user_code_failed"
STEP_RUNNER_REMOTE_STOP = "step_runner.remote_stop"
SIGNAL_HANDLER_RUN_STOPPING = "signal_handler.run_stopping"
SIGNAL_HANDLER_FAIL_FAST = "signal_handler.fail_fast"
SIGNAL_HANDLER_STEP_STOPPING = "signal_handler.step_stopping"
DYNAMIC_RUNNER_STEP_STOPPED = "dynamic_runner.step_stopped"
DYNAMIC_RUNNER_STEP_CANCELLED = "dynamic_runner.step_cancelled"
DYNAMIC_RUNNER_INFRA_DIED = "dynamic_runner.infra_died"
DYNAMIC_RUNNER_STEP_COMPLETED = "dynamic_runner.step_completed"
DYNAMIC_RUNNER_STUCK_STEP_FAILED = "dynamic_runner.stuck_step_failed"
STEP_OPERATOR_STARTED = "step_operator.started"
KUBERNETES_ORCHESTRATOR_JOB_FAILED = "kubernetes_orchestrator.job_failed"
KUBERNETES_ORCHESTRATOR_NODE_FAILED = "kubernetes_orchestrator.node_failed"
MODAL_ORCHESTRATOR_SANDBOX_FAILED = "modal_orchestrator.sandbox_failed"
MODAL_ORCHESTRATOR_STEPS_UNFINISHED = "modal_orchestrator.steps_unfinished"

# Set only by the server middleware. First element is the source context
# channel value, second is the parsed client version or None.
request_source_info: ContextVar[Optional[Tuple[str, Optional[str]]]] = (
    ContextVar("request_source_info", default=None)
)


def compose_status_source(
    declared: Optional[str],
    requested: Optional[ExecutionStatus],
    stored: ExecutionStatus,
) -> str:
    """Compose the `status_source` string stored alongside a status write.

    Args:
        declared: Site slug declared by the writer.
        requested: Status the writer originally requested.
        stored: Status that was actually stored.

    Returns:
        Composed status source string.
    """
    parts = [declared or UNKNOWN_STATUS_SOURCE]

    if requested is not None and requested != stored:
        parts.append(f"requested:{requested.value}")

    info = request_source_info.get()
    if info is not None:
        channel, client_version = info
        parts.append(f"channel:{channel}")
        if client_version is not None:
            parts.append(f"client:{client_version}")

    return ",".join(parts)[:STR_FIELD_MAX_LENGTH]
