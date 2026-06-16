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
"""Modal orchestrator implementation."""

import os
from enum import Enum
from threading import Lock
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast
from uuid import UUID, uuid4

import modal

from zenml.client import Client
from zenml.config.resource_settings import ResourceSettings
from zenml.constants import (
    METADATA_ORCHESTRATOR_RUN_ID,
    ORCHESTRATOR_DOCKER_IMAGE_KEY,
)
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.enums import ExecutionMode, ExecutionStatus, StackComponentType
from zenml.integrations.modal import sandbox_utils
from zenml.integrations.modal.flavors import (
    ModalOrchestratorConfig,
    ModalOrchestratorSettings,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType
from zenml.models import PipelineRunUpdate
from zenml.orchestrators import ContainerizedOrchestrator, SubmissionResult
from zenml.orchestrators import utils as orchestrator_utils
from zenml.orchestrators.publish_utils import (
    publish_step_run_metadata,
)
from zenml.pipelines.dynamic.entrypoint_configuration import (
    DynamicPipelineEntrypointConfiguration,
)
from zenml.stack import Stack, StackValidator
from zenml.step_operators.step_operator_entrypoint_configuration import (
    StepOperatorEntrypointConfiguration,
)

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import (
        PipelineRunResponse,
        PipelineSnapshotResponse,
        StepRunResponse,
    )

logger = get_logger(__name__)

ENV_ZENML_MODAL_RUN_ID = "ZENML_MODAL_RUN_ID"
ENV_ZENML_MODAL_APP_NAME = "ZENML_MODAL_APP_NAME"
MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY = "modal_orchestration_sandbox_id"
MODAL_APP_NAME_METADATA_KEY = "modal_app_name"
MODAL_SANDBOX_ID_METADATA_KEY = "sandbox_id"
MODAL_STATIC_STEP_SANDBOX_ID_METADATA_KEY_PREFIX = "modal_step_sandbox_id_"
MODAL_ENVIRONMENT_METADATA_KEY = "modal_environment"
MODAL_ORCHESTRATOR_GPU_SETTINGS_FIELD = "ModalOrchestratorSettings.gpu"
MODAL_ORCHESTRATOR_GPU_SETTINGS_EXAMPLE = (
    "Set ModalOrchestratorSettings(gpu='<TYPE>') together with "
    "ResourceSettings(gpu_count=1) on the pipeline or step that requests GPU "
    "resources, or set gpu_count=0 to run on CPU."
)


def get_modal_app_name(modal_run_id: str) -> str:
    """Build the deterministic Modal app name for a ZenML run."""
    return f"zenml-{modal_run_id}"[:64]


def _metadata_value(metadata: Dict[str, Any], key: str) -> Optional[str]:
    """Read a metadata value as a string."""
    value = metadata.get(key)
    if value is None:
        return None

    if isinstance(value, Enum):
        value = value.value

    return str(value)


def _metadata_values_with_prefix(
    metadata: Dict[str, Any], prefix: str
) -> Dict[str, str]:
    """Read string metadata values for keys with a shared prefix."""
    values: Dict[str, str] = {}
    for key in metadata:
        if not key.startswith(prefix):
            continue
        if value := _metadata_value(metadata, key):
            values[key.removeprefix(prefix)] = value
    return values


def get_static_step_sandbox_metadata_key(step_name: str) -> str:
    """Build an append-safe run metadata key for a static child sandbox."""
    return f"{MODAL_STATIC_STEP_SANDBOX_ID_METADATA_KEY_PREFIX}{step_name}"


class ModalOrchestrator(ContainerizedOrchestrator):
    """Orchestrator that runs ZenML pipelines in Modal Sandboxes."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the Modal orchestrator."""
        super().__init__(*args, **kwargs)
        self._modal_client: Optional["modal.Client"] = None
        self._modal_client_lock = Lock()

    @property
    def config(self) -> ModalOrchestratorConfig:
        """Get the Modal orchestrator configuration."""
        return cast(ModalOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Get the settings class for the Modal orchestrator."""
        return ModalOrchestratorSettings

    @property
    def supported_execution_modes(self) -> List[ExecutionMode]:
        """Get the execution modes supported by the Modal orchestrator."""
        return [
            ExecutionMode.FAIL_FAST,
            ExecutionMode.STOP_ON_FAILURE,
            ExecutionMode.CONTINUE_ON_FAILURE,
        ]

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validate that the active stack can run in remote Modal Sandboxes."""

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Modal orchestrator runs code remotely and needs to "
                    "read and write files in the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please use a remote artifact "
                    "store with the Modal orchestrator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Modal orchestrator runs code remotely and needs to "
                    "pull Docker images, but the container registry "
                    f"`{container_registry.name}` of the active stack is "
                    "local. Please use a remote container registry with the "
                    "Modal orchestrator."
                )

            for component in stack.all_components:
                if component.local_path is None:
                    continue

                return False, (
                    f"The `{component.name}` {component.type.value} stores "
                    f"runtime files at local path `{component.local_path}`. "
                    "A Modal sandbox runs away from this machine and cannot "
                    "access local filesystem paths. Please replace it with a "
                    "remote-compatible stack component before using the Modal "
                    "orchestrator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    def get_modal_client(self) -> Optional["modal.Client"]:
        """Get the Modal client used by orchestrator entrypoints."""
        if (
            self._modal_client is not None
            and not self._modal_client.is_closed()
        ):
            return self._modal_client

        with self._modal_client_lock:
            if (
                self._modal_client is not None
                and not self._modal_client.is_closed()
            ):
                return self._modal_client

            self._modal_client = (
                sandbox_utils.create_modal_client_from_credentials(
                    token_id=self.config.token_id,
                    token_secret=self.config.token_secret,
                )
            )
            return self._modal_client

    def _inject_modal_credentials(self, environment: Dict[str, str]) -> None:
        """Forward Modal credentials into a controller sandbox environment.

        The controller sandbox creates child sandboxes by calling the Modal
        API, so it needs its own Modal credentials. These are resolved from the
        component config token pair when set, otherwise from the local Modal
        config (`MODAL_TOKEN_ID` / `MODAL_TOKEN_SECRET` or `~/.modal.toml`), the
        same source the step operator relies on. The keys are marked sensitive
        in ``sandbox_utils``, so they are injected as a Modal Secret rather than
        a plain environment variable.
        """
        token_pair = sandbox_utils.resolve_modal_token_pair(
            token_id=self.config.token_id,
            token_secret=self.config.token_secret,
        )
        if token_pair is None:
            logger.warning(
                "No Modal credentials could be resolved for the controller "
                "sandbox. The controller will fail to create child sandboxes "
                "unless Modal credentials are available in its environment. "
                "Configure token_id and token_secret on the Modal orchestrator "
                "or run `modal setup` before submitting the pipeline."
            )
            return

        token_id, token_secret = token_pair
        environment[sandbox_utils.MODAL_TOKEN_ID_ENV_KEY] = token_id
        environment[sandbox_utils.MODAL_TOKEN_SECRET_ENV_KEY] = token_secret

    def get_orchestrator_run_id(self) -> str:
        """Return the stable Modal run ID from the sandbox environment."""
        try:
            return os.environ[ENV_ZENML_MODAL_RUN_ID]
        except KeyError as e:
            raise RuntimeError(
                f"Unable to get Modal orchestrator run ID from the "
                f"{ENV_ZENML_MODAL_RUN_ID} environment variable."
            ) from e

    def submit_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        base_environment: Dict[str, str],
        step_environments: Dict[str, Dict[str, str]],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submit a static pipeline controller sandbox to Modal."""
        if snapshot.schedule:
            raise RuntimeError(
                "Scheduling static pipelines is not supported for the Modal "
                "orchestrator yet."
            )

        from zenml.integrations.modal.orchestrators.modal_orchestrator_entrypoint import (
            ModalOrchestratorEntrypointConfiguration,
        )

        # The static Modal controller recomputes per-step environments after
        # it loads the active stack and run-scoped secrets inside Modal.
        del step_environments

        command = (
            ModalOrchestratorEntrypointConfiguration.get_entrypoint_command()
        )
        args = (
            ModalOrchestratorEntrypointConfiguration.get_entrypoint_arguments(
                snapshot_id=snapshot.id,
                run_id=placeholder_run.id if placeholder_run else None,
            )
        )

        return self._submit_orchestration_sandbox(
            snapshot=snapshot,
            stack=stack,
            entrypoint_command=command + args,
            environment=base_environment,
            placeholder_run=placeholder_run,
        )

    def submit_dynamic_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submit a dynamic pipeline orchestration sandbox to Modal."""
        if snapshot.schedule:
            raise RuntimeError(
                "Scheduling dynamic pipelines is not supported for the Modal "
                "orchestrator yet."
            )

        command = (
            DynamicPipelineEntrypointConfiguration.get_entrypoint_command()
        )
        args = DynamicPipelineEntrypointConfiguration.get_entrypoint_arguments(
            snapshot_id=snapshot.id,
            run_id=placeholder_run.id if placeholder_run else None,
        )

        return self._submit_orchestration_sandbox(
            snapshot=snapshot,
            stack=stack,
            entrypoint_command=command + args,
            environment=environment,
            placeholder_run=placeholder_run,
        )

    def _submit_orchestration_sandbox(
        self,
        *,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        entrypoint_command: list[str],
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"],
    ) -> SubmissionResult:
        """Submit the Modal sandbox that controls a ZenML run."""
        settings = cast(ModalOrchestratorSettings, self.get_settings(snapshot))
        modal_environment = sandbox_utils.normalize_optional_config_value(
            settings.modal_environment
        )
        modal_run_id = (
            str(placeholder_run.id) if placeholder_run else str(uuid4())
        )
        app_name = get_modal_app_name(modal_run_id)

        if placeholder_run:
            Client().zen_store.update_run(
                run_id=placeholder_run.id,
                run_update=PipelineRunUpdate(orchestrator_run_id=modal_run_id),
            )

        try:
            image_name = self.get_image(snapshot=snapshot)
        except KeyError:
            invocation_id = next(iter(snapshot.step_configurations))
            image_name = self.get_image(
                snapshot=snapshot, step_name=invocation_id
            )

        if not stack.container_registry:
            raise ValueError(
                "No container registry found in the stack. Please add a "
                "container registry before using the Modal orchestrator."
            )

        sandbox_environment = environment.copy()
        sandbox_environment[ENV_ZENML_MODAL_RUN_ID] = modal_run_id
        sandbox_environment[ENV_ZENML_MODAL_APP_NAME] = app_name

        self._inject_modal_credentials(sandbox_environment)

        modal_client = self.get_modal_client()
        zenml_image = sandbox_utils.get_modal_image_from_registry(
            image_name, stack.container_registry.credentials
        )
        app = sandbox_utils.lookup_modal_app(
            app_name,
            modal_environment=modal_environment,
            modal_client=modal_client,
        )
        sandbox = sandbox_utils.create_modal_sandbox(
            entrypoint_command,
            app=app,
            image=zenml_image,
            settings=settings,
            resource_settings=snapshot.pipeline_configuration.resource_settings
            or ResourceSettings(),
            environment=sandbox_environment,
            modal_client=modal_client,
            gpu_settings_field=MODAL_ORCHESTRATOR_GPU_SETTINGS_FIELD,
            gpu_settings_example=MODAL_ORCHESTRATOR_GPU_SETTINGS_EXAMPLE,
        )

        metadata: Dict[str, MetadataType] = {
            METADATA_ORCHESTRATOR_RUN_ID: modal_run_id,
            MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY: sandbox.object_id,
            MODAL_APP_NAME_METADATA_KEY: app_name,
        }
        if modal_environment:
            metadata[MODAL_ENVIRONMENT_METADATA_KEY] = modal_environment

        wait_for_completion = None
        if settings.synchronous:

            def _wait_for_completion() -> None:
                logger.info(
                    "Waiting for Modal orchestration sandbox `%s` to finish.",
                    sandbox.object_id,
                )
                return_code = sandbox_utils.wait_for_sandbox(sandbox)
                if return_code != 0:
                    raise RuntimeError(
                        "Modal orchestration sandbox "
                        f"`{sandbox.object_id}` failed with exit code "
                        f"{return_code}."
                    )

            wait_for_completion = _wait_for_completion
        else:
            logger.info(
                "Modal orchestration sandbox `%s` started.", sandbox.object_id
            )

        return SubmissionResult(
            wait_for_completion=wait_for_completion,
            metadata=metadata,
        )

    def submit_isolated_step(
        self, step_run_info: "StepRunInfo", environment: Dict[str, str]
    ) -> None:
        """Submit a dynamic isolated step sandbox to Modal."""
        command, args = orchestrator_utils.get_step_entrypoint_command(
            invocation_id=step_run_info.pipeline_step_name,
            config=step_run_info.config,
            entrypoint_config_class=StepOperatorEntrypointConfiguration,
            snapshot_id=step_run_info.snapshot.id,
            step_run_id=str(step_run_info.step_run_id),
        )

        image_name = step_run_info.get_image(key=ORCHESTRATOR_DOCKER_IMAGE_KEY)
        settings = cast(
            ModalOrchestratorSettings, self.get_settings(step_run_info)
        )
        modal_run_id = os.environ.get(
            ENV_ZENML_MODAL_RUN_ID, str(step_run_info.run_id)
        )
        app_name = os.environ.get(
            ENV_ZENML_MODAL_APP_NAME, get_modal_app_name(modal_run_id)
        )
        sandbox_environment = environment.copy()
        sandbox_environment[ENV_ZENML_MODAL_RUN_ID] = modal_run_id
        sandbox_environment[ENV_ZENML_MODAL_APP_NAME] = app_name

        sandbox = self._create_step_sandbox(
            app_name=app_name,
            image_name=image_name,
            settings=settings,
            resource_settings=step_run_info.config.resource_settings,
            environment=sandbox_environment,
            entrypoint_command=command + args,
        )

        metadata = self.get_step_sandbox_metadata(settings, sandbox.object_id)
        try:
            publish_step_run_metadata(
                step_run_info.step_run_id,
                {self.id: metadata},
            )
            step_run_info.step_run.run_metadata.update(metadata)
        except Exception:
            self._terminate_created_sandbox_after_metadata_error(sandbox)
            raise

    def create_static_step_sandbox(
        self,
        *,
        snapshot: "PipelineSnapshotResponse",
        step_name: str,
        environment: Dict[str, str],
    ) -> "modal.Sandbox":
        """Create a child sandbox for a static pipeline step."""
        settings = cast(
            ModalOrchestratorSettings,
            self.get_settings(snapshot.step_configurations[step_name]),
        )
        command = StepEntrypointConfiguration.get_entrypoint_command()
        args = StepEntrypointConfiguration.get_entrypoint_arguments(
            step_name=step_name,
            snapshot_id=snapshot.id,
        )
        image_name = self.get_image(snapshot=snapshot, step_name=step_name)
        return self._create_step_sandbox(
            app_name=os.environ.get(
                ENV_ZENML_MODAL_APP_NAME,
                get_modal_app_name(self.get_orchestrator_run_id()),
            ),
            image_name=image_name,
            settings=settings,
            resource_settings=snapshot.step_configurations[
                step_name
            ].config.resource_settings,
            environment=environment,
            entrypoint_command=command + args,
        )

    def _create_step_sandbox(
        self,
        *,
        app_name: str,
        image_name: str,
        settings: ModalOrchestratorSettings,
        resource_settings: ResourceSettings,
        environment: Dict[str, str],
        entrypoint_command: list[str],
    ) -> "modal.Sandbox":
        """Create a Modal sandbox for one ZenML step."""
        stack = Client().active_stack
        if not stack.container_registry:
            raise ValueError(
                "No container registry found in the active stack. Please add "
                "a container registry before using the Modal orchestrator."
            )

        modal_environment = sandbox_utils.normalize_optional_config_value(
            settings.modal_environment
        )
        modal_client = self.get_modal_client()
        zenml_image = sandbox_utils.get_modal_image_from_registry(
            image_name, stack.container_registry.credentials
        )
        app = sandbox_utils.lookup_modal_app(
            app_name,
            modal_environment=modal_environment,
            modal_client=modal_client,
        )
        return sandbox_utils.create_modal_sandbox(
            entrypoint_command,
            app=app,
            image=zenml_image,
            settings=settings,
            resource_settings=resource_settings or ResourceSettings(),
            environment=environment,
            modal_client=modal_client,
            gpu_settings_field=MODAL_ORCHESTRATOR_GPU_SETTINGS_FIELD,
            gpu_settings_example=MODAL_ORCHESTRATOR_GPU_SETTINGS_EXAMPLE,
        )

    @staticmethod
    def get_step_sandbox_metadata(
        settings: ModalOrchestratorSettings, sandbox_id: str
    ) -> Dict[str, MetadataType]:
        """Build step sandbox metadata for orchestrator entrypoints."""
        metadata: Dict[str, MetadataType] = {
            MODAL_SANDBOX_ID_METADATA_KEY: sandbox_id
        }
        modal_environment = sandbox_utils.normalize_optional_config_value(
            settings.modal_environment
        )
        if modal_environment:
            metadata[MODAL_ENVIRONMENT_METADATA_KEY] = modal_environment
        return metadata

    def get_isolated_step_status(
        self, step_run: "StepRunResponse"
    ) -> ExecutionStatus:
        """Get the status of a dynamic isolated step sandbox."""
        sandbox_id = _metadata_value(
            step_run.run_metadata, MODAL_SANDBOX_ID_METADATA_KEY
        )
        if not sandbox_id:
            logger.warning(
                "No Modal sandbox metadata found for step run `%s`.",
                step_run.id,
            )
            return step_run.status

        try:
            return sandbox_utils.get_sandbox_status(
                sandbox_id, modal_client=self.get_modal_client()
            )
        except Exception as e:
            logger.warning(
                "Failed to fetch Modal sandbox `%s` for step run `%s`: %s",
                sandbox_id,
                step_run.id,
                e,
            )
            return ExecutionStatus.FAILED

    def stop_isolated_step(self, step_run: "StepRunResponse") -> None:
        """Stop a dynamic isolated step sandbox if it is still running."""
        sandbox_id = _metadata_value(
            step_run.run_metadata, MODAL_SANDBOX_ID_METADATA_KEY
        )
        if not sandbox_id:
            logger.warning(
                "No Modal sandbox metadata found for step run `%s`.",
                step_run.id,
            )
            return

        self.terminate_sandbox_if_running(
            sandbox_id=sandbox_id,
            description=f"step run `{step_run.id}`",
        )

    def fetch_status(
        self, run: "PipelineRunResponse", include_steps: bool = False
    ) -> Tuple[
        Optional[ExecutionStatus], Optional[Dict[str, ExecutionStatus]]
    ]:
        """Fetch Modal sandbox status for a pipeline run and its steps."""
        pipeline_status = None
        sandbox_id = _metadata_value(
            run.run_metadata, MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY
        )
        if sandbox_id and not run.status.is_finished:
            try:
                status = sandbox_utils.get_sandbox_status(
                    sandbox_id, modal_client=self.get_modal_client()
                )
            except Exception as e:
                logger.warning(
                    "Failed to fetch Modal orchestration sandbox `%s`: %s",
                    sandbox_id,
                    e,
                )
            else:
                pipeline_status = status
        elif not sandbox_id:
            logger.warning(
                "No Modal orchestration sandbox metadata found for run `%s`.",
                run.id,
            )

        step_statuses = None
        if include_steps:
            step_statuses = {}
            run_with_steps = self._get_fresh_pipeline_run(run)
            try:
                steps = run_with_steps.steps
            except Exception:
                logger.debug(
                    "Pipeline run `%s` is not hydrated with step metadata.",
                    run.id,
                    exc_info=True,
                )
                steps = {}

            fallback_sandbox_ids = _metadata_values_with_prefix(
                run_with_steps.run_metadata,
                MODAL_STATIC_STEP_SANDBOX_ID_METADATA_KEY_PREFIX,
            )

            for step_name, step_run in steps.items():
                if step_run.status.is_finished:
                    continue

                step_sandbox_id = _metadata_value(
                    step_run.run_metadata, MODAL_SANDBOX_ID_METADATA_KEY
                )
                if not step_sandbox_id:
                    step_sandbox_id = fallback_sandbox_ids.get(step_name)
                if not step_sandbox_id:
                    continue

                try:
                    status = sandbox_utils.get_sandbox_status(
                        step_sandbox_id,
                        modal_client=self.get_modal_client(),
                    )
                    step_statuses[step_name] = status
                except Exception as e:
                    logger.warning(
                        "Failed to fetch Modal sandbox `%s` for step `%s`: %s",
                        step_sandbox_id,
                        step_name,
                        e,
                    )

        return pipeline_status, step_statuses

    def _stop_run(
        self, run: "PipelineRunResponse", graceful: bool = False
    ) -> None:
        """Stop a Modal run, honoring graceful stops where possible."""
        refreshed_run: Optional["PipelineRunResponse"] = None
        if graceful:
            snapshot = run.snapshot
            if snapshot is None:
                refreshed_run = self._get_fresh_pipeline_run(run)
                snapshot = refreshed_run.snapshot

            if snapshot is not None and not snapshot.is_dynamic:
                logger.info(
                    "Gracefully stopping Modal run `%s`. The orchestration "
                    "sandbox will stop scheduling new steps and let running "
                    "child sandboxes finish.",
                    run.id,
                )
                return

            logger.warning(
                "Graceful stops are only supported for static Modal runs. "
                "Force-stopping Modal run `%s` instead.",
                run.id,
            )

        errors: List[str] = []
        attempted_child_sandbox_ids: set[str] = set()
        attempted_orchestration_sandbox_ids: set[str] = set()

        if refreshed_run is None:
            refreshed_run = self._get_fresh_pipeline_run(run)

        def _terminate_child_sandboxes(
            target_run: "PipelineRunResponse",
        ) -> None:
            for sandbox_id in self._get_child_sandbox_ids(target_run):
                if sandbox_id in attempted_child_sandbox_ids:
                    continue
                attempted_child_sandbox_ids.add(sandbox_id)
                try:
                    self.terminate_sandbox_if_running(
                        sandbox_id=sandbox_id,
                        description=(
                            f"child sandbox `{sandbox_id}` for run `{run.id}`"
                        ),
                    )
                except Exception as e:
                    errors.append(str(e))

        def _terminate_orchestration_sandbox(
            target_run: "PipelineRunResponse",
        ) -> None:
            orchestration_sandbox_id = _metadata_value(
                target_run.run_metadata,
                MODAL_ORCHESTRATION_SANDBOX_ID_METADATA_KEY,
            )
            if not orchestration_sandbox_id:
                logger.warning(
                    "No Modal orchestration sandbox metadata found for run `%s`.",
                    run.id,
                )
                return
            if orchestration_sandbox_id in attempted_orchestration_sandbox_ids:
                return

            attempted_orchestration_sandbox_ids.add(orchestration_sandbox_id)
            try:
                self.terminate_sandbox_if_running(
                    sandbox_id=orchestration_sandbox_id,
                    description=f"orchestration sandbox for run `{run.id}`",
                )
            except Exception as e:
                errors.append(str(e))

        _terminate_child_sandboxes(refreshed_run)
        _terminate_orchestration_sandbox(refreshed_run)

        late_run = self._get_fresh_pipeline_run(run)
        _terminate_child_sandboxes(late_run)
        _terminate_orchestration_sandbox(late_run)

        if errors:
            raise RuntimeError(
                "Failed to stop all Modal sandboxes: " + "; ".join(errors)
            )

    @staticmethod
    def _get_fresh_pipeline_run(
        run: "PipelineRunResponse",
    ) -> "PipelineRunResponse":
        """Fetch the latest hydrated run, falling back to the given one."""
        try:
            return Client().get_pipeline_run(run.id)
        except Exception:
            logger.debug(
                "Failed to fetch a fresh Modal pipeline run before cleanup.",
                exc_info=True,
            )
            return run

    @staticmethod
    def _get_child_sandbox_ids(run: "PipelineRunResponse") -> set[str]:
        """Read child sandbox IDs from step and static fallback metadata."""
        child_sandbox_ids: set[str] = set()
        try:
            steps = run.steps
        except Exception:
            logger.debug(
                "Pipeline run `%s` is not hydrated with step metadata.",
                run.id,
                exc_info=True,
            )
            steps = {}

        for step_run in steps.values():
            if sandbox_id := _metadata_value(
                step_run.run_metadata, MODAL_SANDBOX_ID_METADATA_KEY
            ):
                child_sandbox_ids.add(sandbox_id)

        child_sandbox_ids.update(
            _metadata_values_with_prefix(
                run.run_metadata,
                MODAL_STATIC_STEP_SANDBOX_ID_METADATA_KEY_PREFIX,
            ).values()
        )
        return child_sandbox_ids

    def terminate_sandbox_if_running(
        self, *, sandbox_id: str, description: str
    ) -> None:
        """Terminate a running Modal sandbox for an orchestrator entrypoint."""
        sandbox = sandbox_utils.get_sandbox_by_id(
            sandbox_id, modal_client=self.get_modal_client()
        )
        if sandbox.poll() is not None:
            logger.debug(
                "Modal sandbox for %s is already finished.", description
            )
            return

        sandbox.terminate()
        logger.info("Terminated Modal sandbox for %s.", description)

    @staticmethod
    def _terminate_created_sandbox_after_metadata_error(
        sandbox: "modal.Sandbox",
    ) -> None:
        """Terminate a newly-created sandbox after metadata publication fails."""
        try:
            sandbox.terminate()
        except Exception:
            logger.exception(
                "Failed to terminate Modal sandbox `%s` after metadata "
                "publication failed.",
                sandbox.object_id,
            )

    def get_pipeline_run_metadata(
        self, run_id: UUID
    ) -> Dict[str, MetadataType]:
        """Get run metadata from the Modal sandbox environment."""
        metadata: Dict[str, MetadataType] = {
            METADATA_ORCHESTRATOR_RUN_ID: self.get_orchestrator_run_id()
        }
        if app_name := os.environ.get(ENV_ZENML_MODAL_APP_NAME):
            metadata[MODAL_APP_NAME_METADATA_KEY] = app_name
        return metadata
