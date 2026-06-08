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

from typing import Any, Dict, List, Optional, cast
from uuid import UUID

from zenml.client import Client
from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.enums import ExecutionMode, ExecutionStatus
from zenml.exceptions import AuthorizationException
from zenml.integrations.modal import sandbox_utils
from zenml.integrations.modal.orchestrators.modal_orchestrator import (
    ENV_ZENML_MODAL_APP_NAME,
    ENV_ZENML_MODAL_RUN_ID,
    MODAL_SANDBOX_ID_METADATA_KEY,
    ModalOrchestrator,
    get_static_step_sandbox_metadata_key,
)
from zenml.integrations.registry import integration_registry
from zenml.logger import get_logger
from zenml.models import PipelineRunUpdate, StepRunResponse
from zenml.orchestrators import publish_utils
from zenml.orchestrators.monitored_dag_runner import (
    DagRunner as ModalDagRunner,
)
from zenml.orchestrators.monitored_dag_runner import (
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
NODE_METADATA_STEP_RUN_ID_KEY = "step_run_id"


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
        integration_registry.activate_integrations()
        self.prepare_code_environment()

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
        if app_name := self._get_modal_app_name_from_environment():
            shared_env[ENV_ZENML_MODAL_APP_NAME] = app_name

        step_run_request_factory = StepRunRequestFactory(
            snapshot=snapshot,
            pipeline_run=pipeline_run,
            stack=active_stack,
        )
        step_runs: Dict[str, StepRunResponse] = {}

        def _cache_step_run_if_possible(step_name: str) -> bool:
            if not step_run_request_factory.has_caching_enabled(step_name):
                return False

            request = step_run_request_factory.create_request(step_name)
            try:
                step_run_request_factory.populate_request(
                    request, step_runs=step_runs
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

            step_run = publish_cached_step_run(request, pipeline_run)
            step_runs[step_name] = step_run
            logger.info("Using cached version of step `%s`.", step_name)
            return True

        def _step_environment(step_name: str) -> Dict[str, str]:
            step = snapshot.step_configurations[step_name]
            environment = shared_env.copy()
            environment.update(
                env_utils.get_runtime_environment(
                    config=step.config, stack=active_stack
                )
            )
            return environment

        def _publish_step_sandbox_metadata(node: Node) -> bool:
            sandbox_id = node.metadata.get(MODAL_SANDBOX_ID_METADATA_KEY)
            if not sandbox_id:
                return False

            if node.metadata.get(NODE_METADATA_PUBLISHED_KEY):
                return True

            step_runs_page = client.list_run_steps(
                name=node.id,
                pipeline_run_id=pipeline_run.id,
                hydrate=False,
                exclude_retried=True,
                size=1,
            )
            if not step_runs_page:
                return False

            step_run = step_runs_page[0]
            metadata = orchestrator._step_sandbox_metadata(
                cast(
                    Any,
                    orchestrator.get_settings(
                        snapshot.step_configurations[node.id]
                    ),
                ),
                str(sandbox_id),
            )
            publish_utils.publish_step_run_metadata(
                step_run.id,
                {orchestrator.id: metadata},
            )
            node.metadata[NODE_METADATA_PUBLISHED_KEY] = True
            node.metadata[NODE_METADATA_STEP_RUN_ID_KEY] = str(step_run.id)
            return True

        def _handle_failed_sandbox(step_name: str) -> NodeStatus:
            steps = client.list_run_steps(
                name=step_name,
                pipeline_run_id=pipeline_run.id,
                hydrate=False,
                exclude_retried=True,
                size=1,
            )
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

            request = step_run_request_factory.create_request(step_name)
            try:
                step_run_request_factory.populate_request(
                    request, step_runs=step_runs
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
                client.zen_store.create_run_step(request)
            except Exception as e:
                logger.error(
                    "Failed to publish failed step run `%s`: %s", step_name, e
                )
            return NodeStatus.FAILED

        def start_step_sandbox(node: Node) -> NodeStatus:
            step_name = node.id
            if _cache_step_run_if_possible(step_name):
                return NodeStatus.COMPLETED

            sandbox = orchestrator.create_static_step_sandbox(
                snapshot=snapshot,
                step_name=step_name,
                environment=_step_environment(step_name),
            )
            node.metadata[MODAL_SANDBOX_ID_METADATA_KEY] = sandbox.object_id
            try:
                publish_utils.publish_pipeline_run_metadata(
                    pipeline_run.id,
                    {
                        orchestrator.id: {
                            get_static_step_sandbox_metadata_key(
                                step_name
                            ): sandbox.object_id
                        }
                    },
                )
                pipeline_run.run_metadata[
                    get_static_step_sandbox_metadata_key(step_name)
                ] = sandbox.object_id
                _publish_step_sandbox_metadata(node)
            except Exception:
                sandbox.terminate()
                raise

            logger.info(
                "Started Modal sandbox `%s` for step `%s`.",
                sandbox.object_id,
                step_name,
            )
            return NodeStatus.RUNNING

        def check_step_sandbox(node: Node) -> NodeStatus:
            sandbox_id = node.metadata.get(MODAL_SANDBOX_ID_METADATA_KEY)
            if not sandbox_id:
                logger.error(
                    "Missing Modal sandbox ID for step `%s`.", node.id
                )
                return NodeStatus.FAILED

            _publish_step_sandbox_metadata(node)
            status = sandbox_utils.get_sandbox_status(
                str(sandbox_id), modal_client=orchestrator._get_modal_client()
            )
            if status == ExecutionStatus.COMPLETED:
                return NodeStatus.COMPLETED
            if status == ExecutionStatus.FAILED:
                logger.error("Modal sandbox for step `%s` failed.", node.id)
                return _handle_failed_sandbox(node.id)
            return NodeStatus.RUNNING

        def stop_step_sandbox(node: Node) -> None:
            sandbox_id = node.metadata.get(MODAL_SANDBOX_ID_METADATA_KEY)
            if not sandbox_id:
                return
            orchestrator._terminate_sandbox_if_running(
                sandbox_id=str(sandbox_id),
                description=f"static step `{node.id}`",
            )

        def should_interrupt_execution() -> Optional[InterruptMode]:
            try:
                run = client.get_pipeline_run(
                    name_id_or_prefix=pipeline_run.id,
                    project=pipeline_run.project_id,
                    hydrate=False,
                )
            except Exception as e:
                logger.warning(
                    "Failed to check Modal pipeline run stop status: %s", e
                )
                return None

            if run.status in {
                ExecutionStatus.STOPPING,
                ExecutionStatus.STOPPED,
            }:
                logger.info(
                    "Stopping Modal DAG because pipeline run `%s` is `%s`.",
                    pipeline_run.id,
                    run.status,
                )
                return InterruptMode.FORCE

            if run.status == ExecutionStatus.FAILED:
                if (
                    snapshot.pipeline_configuration.execution_mode
                    == ExecutionMode.FAIL_FAST
                ):
                    return InterruptMode.FORCE
                if (
                    snapshot.pipeline_configuration.execution_mode
                    == ExecutionMode.STOP_ON_FAILURE
                ):
                    return InterruptMode.GRACEFUL

            return None

        nodes = [
            Node(id=step_name, upstream_nodes=step.spec.upstream_steps)
            for step_name, step in snapshot.step_configurations.items()
        ]
        node_statuses = ModalDagRunner(
            nodes=nodes,
            node_startup_function=start_step_sandbox,
            node_monitoring_function=check_step_sandbox,
            node_stop_function=stop_step_sandbox,
            interrupt_function=should_interrupt_execution,
        ).run()

        self._finalize_pipeline_run(pipeline_run.id, node_statuses)
        logger.info("Modal orchestration sandbox finished.")

    def _get_or_create_pipeline_run(
        self, *, snapshot_id: UUID, modal_run_id: str
    ):
        """Create or update the ZenML pipeline run controlled by Modal."""
        snapshot = self.snapshot
        client = Client()
        run_id = self.entrypoint_args.get(RUN_ID_OPTION)

        if run_id:
            return client.zen_store.update_run(
                run_id=UUID(run_id),
                run_update=PipelineRunUpdate(orchestrator_run_id=modal_run_id),
            )

        return create_placeholder_run(
            snapshot=snapshot,
            orchestrator_run_id=modal_run_id,
        )

    @staticmethod
    def _get_modal_app_name_from_environment() -> Optional[str]:
        """Read the Modal app name from the controller environment."""
        import os

        return os.environ.get(ENV_ZENML_MODAL_APP_NAME)

    @staticmethod
    def _finalize_pipeline_run(
        pipeline_run_id: UUID,
        node_statuses: Dict[str, NodeStatus],
    ) -> None:
        """Publish a final pipeline status when the run is still active."""
        try:
            run = Client().get_pipeline_run(pipeline_run_id)
            if run.status in {
                ExecutionStatus.STOPPING,
                ExecutionStatus.STOPPED,
            }:
                if run.status == ExecutionStatus.STOPPING:
                    publish_utils.publish_pipeline_run_status_update(
                        pipeline_run_id,
                        ExecutionStatus.STOPPED,
                    )
                return

            failed_step_names = [
                step_name
                for step_name, node_status in node_statuses.items()
                if node_status
                in {
                    NodeStatus.FAILED,
                    NodeStatus.SKIPPED,
                    NodeStatus.CANCELLED,
                }
            ]
            if failed_step_names:
                logger.error(
                    "The following Modal steps did not complete successfully: %s",
                    ", ".join(failed_step_names),
                )
                step_runs = fetch_step_runs_by_names(
                    step_run_names=failed_step_names,
                    pipeline_run=Client().get_pipeline_run(pipeline_run_id),
                )
                for step_run in step_runs.values():
                    if step_run.status in {
                        ExecutionStatus.INITIALIZING,
                        ExecutionStatus.RUNNING,
                    }:
                        publish_utils.publish_failed_step_run(step_run.id)

                run = Client().get_pipeline_run(pipeline_run_id)
                if run.status in {
                    ExecutionStatus.INITIALIZING,
                    ExecutionStatus.PROVISIONING,
                    ExecutionStatus.RUNNING,
                }:
                    publish_utils.publish_failed_pipeline_run(pipeline_run_id)
                return

            run = Client().get_pipeline_run(pipeline_run_id)
            if run.status in {
                ExecutionStatus.INITIALIZING,
                ExecutionStatus.PROVISIONING,
                ExecutionStatus.RUNNING,
            }:
                publish_utils.publish_successful_pipeline_run(pipeline_run_id)
        except AuthorizationException:
            pass
