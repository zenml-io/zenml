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
"""Static Modal orchestration entrypoint."""

import os
import time
from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from zenml.client import Client
from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.enums import ExecutionMode, ExecutionStatus
from zenml.exceptions import AuthorizationException
from zenml.integrations.modal import sandbox_utils
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalOrchestratorSettings,
)
from zenml.integrations.modal.orchestrators.modal_orchestrator import (
    ENV_ZENML_MODAL_APP_NAME,
    ENV_ZENML_MODAL_RUN_ID,
    MODAL_SANDBOX_ID_METADATA_KEY,
    ModalOrchestrator,
    get_static_step_sandbox_metadata_key,
)
from zenml.logger import get_logger
from zenml.models import PipelineRunUpdate, StepRunResponse
from zenml.orchestrators import publish_utils
from zenml.orchestrators.dag_runner import (
    DagRunner,
    InterruptMode,
    Node,
    NodeStatus,
)
from zenml.orchestrators.step_run_utils import (
    StepRunRequestFactory,
    fetch_step_runs_by_names,
    publish_cached_step_run,
)
from zenml.orchestrators.utils import get_config_environment_vars
from zenml.pipelines.run_utils import create_placeholder_run
from zenml.utils import env_utils
from zenml.utils.time_utils import utc_now

logger = get_logger(__name__)

RUN_ID_OPTION = "run_id"
NODE_METADATA_PUBLISHED_KEY = "metadata_published"
NODE_METADATA_PUBLISH_ATTEMPTED_AT_KEY = "metadata_publish_attempted_at"

# Step-level sandbox metadata is best-effort bookkeeping: every reader of
# sandbox IDs falls back to the run-level metadata published at sandbox
# creation, and the step run row only exists once the step entrypoint starts
# inside the sandbox, which can take a minute of cold start. Retrying on a
# slow interval instead of every monitoring tick keeps a parallel cold start
# from hammering the ZenML server.
STEP_METADATA_PUBLISH_RETRY_INTERVAL_SECONDS = 10.0


class _StaticModalPipelineController:
    """Control Modal child sandboxes for one static pipeline run."""

    def __init__(
        self,
        *,
        snapshot: Any,
        pipeline_run: Any,
        active_stack: Any,
        orchestrator: ModalOrchestrator,
        client: Client,
        shared_env: Dict[str, str],
        step_run_request_factory: StepRunRequestFactory,
    ) -> None:
        """Initialize the controller with explicit runtime state."""
        self.snapshot = snapshot
        self.pipeline_run = pipeline_run
        self.active_stack = active_stack
        self.orchestrator = orchestrator
        self.client = client
        self.shared_env = shared_env
        self.step_run_request_factory = step_run_request_factory
        self.step_runs: Dict[str, StepRunResponse] = {}

    def build_nodes(self) -> List[Node]:
        """Build DAG runner nodes from the static pipeline snapshot."""
        return [
            Node(id=step_name, upstream_nodes=step.spec.upstream_steps)
            for step_name, step in self.snapshot.step_configurations.items()
        ]

    def start_step_sandbox(self, node: Node) -> NodeStatus:
        """Start a Modal sandbox for one step unless it can be cached."""
        step_name = node.id
        if self._cache_step_run_if_possible(step_name):
            return NodeStatus.COMPLETED

        sandbox = self.orchestrator.create_static_step_sandbox(
            snapshot=self.snapshot,
            step_name=step_name,
            environment=self._step_environment(step_name),
        )
        node.metadata[MODAL_SANDBOX_ID_METADATA_KEY] = sandbox.object_id
        try:
            publish_utils.publish_pipeline_run_metadata(
                self.pipeline_run.id,
                {
                    self.orchestrator.id: {
                        get_static_step_sandbox_metadata_key(
                            step_name
                        ): sandbox.object_id
                    }
                },
            )
        except Exception as e:
            logger.warning(
                "Failed to publish Modal sandbox metadata for step `%s`: %s",
                step_name,
                e,
            )

        self._maybe_publish_step_sandbox_metadata(node)

        logger.info(
            "Started Modal sandbox `%s` for step `%s`.",
            sandbox.object_id,
            step_name,
        )
        return NodeStatus.RUNNING

    def check_step_sandbox(self, node: Node) -> NodeStatus:
        """Return the current DAG status for one Modal step sandbox."""
        sandbox_id = node.metadata.get(MODAL_SANDBOX_ID_METADATA_KEY)
        if not sandbox_id:
            logger.error("Missing Modal sandbox ID for step `%s`.", node.id)
            return NodeStatus.FAILED

        self._maybe_publish_step_sandbox_metadata(node)
        status = sandbox_utils.get_sandbox_status(
            str(sandbox_id),
            modal_client=self.orchestrator.get_modal_client(),
        )
        if status == ExecutionStatus.COMPLETED:
            return NodeStatus.COMPLETED
        if status == ExecutionStatus.FAILED:
            logger.error("Modal sandbox for step `%s` failed.", node.id)
            return self._handle_failed_sandbox(node.id)
        return NodeStatus.RUNNING

    def stop_step_sandbox(self, node: Node) -> None:
        """Terminate a step sandbox when the DAG runner stops the node."""
        sandbox_id = node.metadata.get(MODAL_SANDBOX_ID_METADATA_KEY)
        if not sandbox_id:
            return
        self.orchestrator.terminate_sandbox_if_running(
            sandbox_id=str(sandbox_id),
            description=f"static step `{node.id}`",
        )

    def should_interrupt_execution(self) -> Optional[InterruptMode]:
        """Tell the DAG runner whether the ZenML run has requested a stop."""
        try:
            run = self.client.get_pipeline_run(
                name_id_or_prefix=self.pipeline_run.id,
                project=self.pipeline_run.project_id,
                hydrate=False,
            )
        except Exception as e:
            logger.warning(
                "Failed to check Modal pipeline run stop status: %s", e
            )
            return None

        if run.status == ExecutionStatus.STOPPING:
            logger.info(
                "Gracefully stopping Modal DAG because pipeline run `%s` "
                "is `%s`.",
                self.pipeline_run.id,
                run.status,
            )
            return InterruptMode.GRACEFUL

        if run.status == ExecutionStatus.STOPPED:
            logger.info(
                "Force-stopping Modal DAG because pipeline run `%s` is `%s`.",
                self.pipeline_run.id,
                run.status,
            )
            return InterruptMode.FORCE

        if run.status == ExecutionStatus.FAILED:
            execution_mode = (
                self.snapshot.pipeline_configuration.execution_mode
            )
            if execution_mode == ExecutionMode.STOP_ON_FAILURE:
                logger.info(
                    "Gracefully stopping Modal DAG because pipeline run `%s` "
                    "is `%s`.",
                    self.pipeline_run.id,
                    run.status,
                )
                return InterruptMode.GRACEFUL
            if execution_mode == ExecutionMode.FAIL_FAST:
                logger.info(
                    "Force-stopping Modal DAG because pipeline run `%s` "
                    "is `%s`.",
                    self.pipeline_run.id,
                    run.status,
                )
                return InterruptMode.FORCE

        return None

    def _cache_step_run_if_possible(self, step_name: str) -> bool:
        if not self.step_run_request_factory.has_caching_enabled(step_name):
            return False

        request = self.step_run_request_factory.create_request(step_name)
        try:
            self.step_run_request_factory.populate_request(
                request, step_runs=self.step_runs
            )
        except Exception as e:
            logger.error(
                "Failed to populate step run request for step `%s`: %s",
                step_name,
                e,
            )
            return False

        if request.status != ExecutionStatus.CACHED:
            return False

        step_run = publish_cached_step_run(request, self.pipeline_run)
        self.step_runs[step_name] = step_run
        logger.info("Using cached version of step `%s`.", step_name)
        return True

    def _step_environment(self, step_name: str) -> Dict[str, str]:
        step = self.snapshot.step_configurations[step_name]
        environment = self.shared_env.copy()
        environment.update(
            env_utils.get_runtime_environment(
                config=step.config, stack=self.active_stack
            )
        )
        return environment

    def _maybe_publish_step_sandbox_metadata(self, node: Node) -> None:
        """Publish step sandbox metadata without risking the node.

        Step-level metadata is convenience bookkeeping, so a transient
        publish failure must not mark a healthy sandbox as failed, and
        retries are throttled to avoid polling the server on every
        monitoring tick.
        """
        if node.metadata.get(NODE_METADATA_PUBLISHED_KEY):
            return

        now = time.monotonic()
        last_attempt = node.metadata.get(
            NODE_METADATA_PUBLISH_ATTEMPTED_AT_KEY
        )
        if (
            last_attempt is not None
            and now - last_attempt
            < STEP_METADATA_PUBLISH_RETRY_INTERVAL_SECONDS
        ):
            return

        node.metadata[NODE_METADATA_PUBLISH_ATTEMPTED_AT_KEY] = now
        try:
            self._publish_step_sandbox_metadata(node)
        except Exception as e:
            logger.warning(
                "Failed to publish Modal sandbox metadata for step `%s`: %s",
                node.id,
                e,
            )

    def _publish_step_sandbox_metadata(self, node: Node) -> bool:
        sandbox_id = node.metadata.get(MODAL_SANDBOX_ID_METADATA_KEY)
        if not sandbox_id:
            return False

        if node.metadata.get(NODE_METADATA_PUBLISHED_KEY):
            return True

        step_runs_page = self.client.list_run_steps(
            name=node.id,
            pipeline_run_id=self.pipeline_run.id,
            hydrate=False,
            exclude_retried=True,
            size=1,
        )
        step_runs = step_runs_page.items
        if not step_runs:
            return False

        step_run = step_runs[0]
        metadata = self.orchestrator.get_step_sandbox_metadata(
            cast(
                ModalOrchestratorSettings,
                self.orchestrator.get_settings(
                    self.snapshot.step_configurations[node.id]
                ),
            ),
            str(sandbox_id),
        )
        publish_utils.publish_step_run_metadata(
            step_run.id,
            {self.orchestrator.id: metadata},
        )
        node.metadata[NODE_METADATA_PUBLISHED_KEY] = True
        return True

    def _handle_failed_sandbox(self, step_name: str) -> NodeStatus:
        step_runs_page = self.client.list_run_steps(
            name=step_name,
            pipeline_run_id=self.pipeline_run.id,
            hydrate=False,
            exclude_retried=True,
            size=1,
        )
        steps = step_runs_page.items
        if steps:
            step_run = steps[0]
            if step_run.status.is_successful:
                logger.info(
                    "Step `%s` is successful in ZenML even though its "
                    "Modal sandbox returned a non-zero exit code.",
                    step_name,
                )
                return NodeStatus.COMPLETED
            return NodeStatus.FAILED

        request = self.step_run_request_factory.create_request(step_name)
        try:
            self.step_run_request_factory.populate_request(
                request, step_runs=self.step_runs
            )
        except Exception as e:
            logger.error(
                "Failed to populate failed step run request for `%s`: %s",
                step_name,
                e,
            )
            return NodeStatus.FAILED

        request.status = ExecutionStatus.FAILED
        request.end_time = utc_now()
        try:
            self.client.zen_store.create_run_step(request)
        except Exception as e:
            logger.error(
                "Failed to publish failed step run `%s`: %s", step_name, e
            )
        return NodeStatus.FAILED


class ModalOrchestratorEntrypointConfiguration(BaseEntrypointConfiguration):
    """Entrypoint configuration for the static Modal controller sandbox."""

    @classmethod
    def get_entrypoint_options(cls) -> Dict[str, bool]:
        """Get options required by the static Modal controller."""
        return super().get_entrypoint_options() | {RUN_ID_OPTION: False}

    @classmethod
    def get_entrypoint_arguments(cls, **kwargs: Any) -> List[str]:
        """Get command arguments for the static Modal controller."""
        args = super().get_entrypoint_arguments(**kwargs)
        if run_id := kwargs.get(RUN_ID_OPTION):
            args.extend([f"--{RUN_ID_OPTION}", str(run_id)])
        return args

    def run(self) -> None:
        """Start child Modal sandboxes for all steps in a static pipeline."""
        snapshot = self.snapshot

        client = Client()
        active_stack = client.active_stack
        orchestrator = active_stack.orchestrator
        if not isinstance(orchestrator, ModalOrchestrator):
            raise RuntimeError(
                "The active stack orchestrator is not a ModalOrchestrator."
            )

        modal_run_id = orchestrator.get_orchestrator_run_id()
        pipeline_run = self._get_or_create_pipeline_run(
            snapshot_id=snapshot.id,
            modal_run_id=modal_run_id,
        )

        shared_env, secrets = get_config_environment_vars(
            pipeline_run_id=pipeline_run.id
        )
        shared_env.update(secrets)
        shared_env[ENV_ZENML_MODAL_RUN_ID] = modal_run_id
        if app_name := os.environ.get(ENV_ZENML_MODAL_APP_NAME):
            shared_env[ENV_ZENML_MODAL_APP_NAME] = app_name

        controller = _StaticModalPipelineController(
            snapshot=snapshot,
            pipeline_run=pipeline_run,
            active_stack=active_stack,
            orchestrator=orchestrator,
            client=client,
            shared_env=shared_env,
            step_run_request_factory=StepRunRequestFactory(
                snapshot=snapshot,
                pipeline_run=pipeline_run,
                stack=active_stack,
            ),
        )
        node_statuses = DagRunner(
            nodes=controller.build_nodes(),
            node_startup_function=controller.start_step_sandbox,
            node_monitoring_function=controller.check_step_sandbox,
            node_stop_function=controller.stop_step_sandbox,
            interrupt_function=controller.should_interrupt_execution,
        ).run()

        self._finalize_pipeline_run(pipeline_run.id, node_statuses)
        logger.info("Modal orchestration sandbox finished.")

    def _get_or_create_pipeline_run(
        self, *, snapshot_id: UUID, modal_run_id: str
    ) -> Any:
        """Create or update the ZenML pipeline run controlled by Modal."""
        snapshot = self.snapshot
        client = Client()
        run_id = self.entrypoint_args.get(RUN_ID_OPTION)

        if run_id:
            run = client.get_pipeline_run(UUID(run_id))
            if run.orchestrator_run_id:
                if run.orchestrator_run_id != modal_run_id:
                    raise RuntimeError(
                        "Modal controller received run ID "
                        f"`{run_id}` with orchestrator run ID "
                        f"`{run.orchestrator_run_id}`, but the active "
                        f"Modal run ID is `{modal_run_id}`."
                    )
                return run

            return client.zen_store.update_run(
                run_id=run.id,
                run_update=PipelineRunUpdate(orchestrator_run_id=modal_run_id),
            )

        return create_placeholder_run(
            snapshot=snapshot,
            orchestrator_run_id=modal_run_id,
        )

    @staticmethod
    def _finalize_pipeline_run(
        pipeline_run_id: UUID,
        node_statuses: Dict[str, NodeStatus],
    ) -> None:
        """Publish a final pipeline status when the run is still active."""
        failed_step_names = [
            step_name
            for step_name, node_status in node_statuses.items()
            if node_status == NodeStatus.FAILED
        ]
        skipped_step_names = [
            step_name
            for step_name, node_status in node_statuses.items()
            if node_status == NodeStatus.SKIPPED
        ]
        active_statuses = {
            ExecutionStatus.INITIALIZING,
            ExecutionStatus.PROVISIONING,
            ExecutionStatus.RUNNING,
        }

        try:
            client = Client()
            run = client.get_pipeline_run(pipeline_run_id)

            # A graceful local stop only marks the run as STOPPING. Once the
            # controller has drained the DAG, it publishes the terminal status.
            if run.status == ExecutionStatus.STOPPING:
                publish_utils.publish_pipeline_run_status_update(
                    pipeline_run_id,
                    ExecutionStatus.STOPPED,
                )
                return
            if run.status == ExecutionStatus.STOPPED:
                return

            if skipped_step_names:
                logger.warning(
                    "The following Modal steps were skipped: %s",
                    ", ".join(skipped_step_names),
                )

            if not failed_step_names:
                if run.status in active_statuses:
                    publish_utils.publish_successful_pipeline_run(
                        pipeline_run_id
                    )
                return

            logger.error(
                "The following Modal steps did not complete successfully: %s",
                ", ".join(failed_step_names),
            )
            step_runs = fetch_step_runs_by_names(
                step_run_names=failed_step_names,
                pipeline_run=run,
            )
            for step_run in step_runs.values():
                if not step_run.status.is_finished:
                    publish_utils.publish_failed_step_run(step_run.id)

            refreshed_run = client.get_pipeline_run(pipeline_run_id)
            if refreshed_run.status == ExecutionStatus.STOPPING:
                publish_utils.publish_pipeline_run_status_update(
                    pipeline_run_id,
                    ExecutionStatus.STOPPED,
                )
                return
            if refreshed_run.status == ExecutionStatus.STOPPED:
                return
            if refreshed_run.status in active_statuses:
                publish_utils.publish_failed_pipeline_run(pipeline_run_id)
            raise RuntimeError(
                "Modal steps did not complete successfully: "
                + ", ".join(failed_step_names)
            )
        except AuthorizationException:
            if failed_step_names:
                raise RuntimeError(
                    "Modal steps did not complete successfully: "
                    + ", ".join(failed_step_names)
                )
