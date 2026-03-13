#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Utility functions to run a pipeline from the server."""

import hashlib
import os
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import UUID

from packaging import version

from zenml import LogsRequest
from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.config.base_settings import BaseSettings
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_run_configuration import (
    PipelineRunConfiguration,
)
from zenml.config.step_configurations import Step, StepConfigurationUpdate
from zenml.constants import (
    ENV_ZENML_ACTIVE_PROJECT_ID,
    ENV_ZENML_ACTIVE_STACK_ID,
    ENV_ZENML_RUNNER_IMAGE_DISABLE_UV,
    ENV_ZENML_RUNNER_PARENT_IMAGE,
    ENV_ZENML_RUNNER_POD_TIMEOUT,
    LOGS_RUNNER_SOURCE,
    RUN_TEMPLATE_TRIGGERS_FEATURE_NAME,
    handle_bool_env_var,
    handle_int_env_var,
)
from zenml.enums import ExecutionStatus, StackComponentType, StoreType
from zenml.exceptions import IllegalOperationError, MaxConcurrentTasksError
from zenml.logger import get_logger
from zenml.models import (
    CodeReferenceRequest,
    FlavorFilter,
    PipelineBuildResponse,
    PipelineRunResponse,
    PipelineRunTriggerInfo,
    PipelineRunUpdate,
    PipelineSnapshotRequest,
    PipelineSnapshotResponse,
    PipelineSnapshotRunRequest,
    StackResponse,
)
from zenml.pipelines.build_utils import compute_stack_checksum
from zenml.pipelines.run_utils import (
    create_placeholder_run,
    validate_run_config_is_runnable_from_server,
    validate_stack_is_runnable_from_server,
)
from zenml.stack.flavor import Flavor
from zenml.utils import pydantic_utils, requirements_utils, settings_utils
from zenml.zen_server.auth import AuthContext, generate_access_token
from zenml.zen_server.feature_gate.endpoint_utils import (
    check_entitlement,
    report_usage,
)
from zenml.zen_server.pipeline_execution.runner_entrypoint_configuration import (
    RunnerEntrypointConfiguration,
)
from zenml.zen_server.pipeline_execution.workload_manager_interface import (
    WorkloadType,
)
from zenml.zen_server.utils import (
    get_auth_context,
    server_config,
    set_auth_context,
    snapshot_executor,
    workload_manager,
    zen_store,
)

logger = get_logger(__name__)

RUNNER_IMAGE_REPOSITORY = "zenml-runner"


class BoundedThreadPoolExecutor:
    """Thread pool executor which only allows a maximum number of concurrent tasks."""

    def __init__(self, max_workers: int, **kwargs: Any) -> None:
        """Initialize the executor.

        Args:
            max_workers: The maximum number of workers.
            **kwargs: Arguments to pass to the thread pool executor.
        """
        self._executor = ThreadPoolExecutor(max_workers=max_workers, **kwargs)
        self._semaphore = threading.BoundedSemaphore(value=max_workers)

    def submit(
        self, fn: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Future[Any]:
        """Submit a task to the executor.

        Args:
            fn: The function to execute.
            *args: The arguments to pass to the function.
            **kwargs: The keyword arguments to pass to the function.

        Raises:
            Exception: If the task submission fails.
            MaxConcurrentTasksError: If the maximum number of concurrent tasks
                is reached.

        Returns:
            The future of the task.
        """
        if not self._semaphore.acquire(blocking=False):
            raise MaxConcurrentTasksError(
                "Maximum number of concurrent tasks reached."
            )

        try:
            future = self._executor.submit(fn, *args, **kwargs)
        except Exception:
            self._semaphore.release()
            raise
        else:
            future.add_done_callback(lambda _: self._semaphore.release())
            return future

    def shutdown(self, **kwargs: Any) -> None:
        """Shutdown the executor.

        Args:
            **kwargs: Keyword arguments to pass to the shutdown method of the
                executor.
        """
        self._executor.shutdown(**kwargs)


def run_snapshot(
    snapshot: PipelineSnapshotResponse,
    auth_context: AuthContext,
    request: PipelineSnapshotRunRequest,
    sync: bool = False,
    template_id: Optional[UUID] = None,
    create_new_snapshot: bool = True,
    implicit_auth_context: bool = True,
    wait_runner_pod: bool = True,
    trigger_id: UUID | None = None,
) -> PipelineRunResponse:
    """Run a snapshot from the server.

    Args:
        snapshot: The snapshot to run.
        auth_context: Authentication context.
        request: The run request.
        sync: Whether to run the snapshot synchronously.
        template_id: The ID of the template from which to create the snapshot
            request.
        create_new_snapshot: Whether to create a new, copy snapshot.
        implicit_auth_context: Whether to use implicit auth context or create an explicit new one.
        wait_runner_pod: Whether to wait for runner pod completion.
        trigger_id: The trigger ID that generated the snapshot run (optional).

    Raises:
        MaxConcurrentTasksError: If the maximum number of concurrent run
            snapshot tasks is reached.

    Returns:
        ID of the new pipeline run.
    """
    if not implicit_auth_context:
        set_auth_context(auth_context)
    logger.info("Current auth context: %s", get_auth_context())
    build, stack, zenml_version = validate_snapshot_for_server_execution(
        snapshot=snapshot,
        run_configuration=request.run_configuration,
    )

    snapshot_request = snapshot_request_from_source_snapshot(
        source_snapshot=snapshot,
        config=request.run_configuration or PipelineRunConfiguration(),
        template_id=template_id,
    )

    ensure_async_orchestrator(snapshot=snapshot_request, stack=stack)

    if create_new_snapshot:
        target_snapshot = zen_store().create_snapshot(snapshot_request)
    else:
        target_snapshot = snapshot

    trigger_info = None
    if request.step_run:
        trigger_info = PipelineRunTriggerInfo(
            step_run_id=request.step_run,
        )

    placeholder_run = create_placeholder_run(
        snapshot=target_snapshot,
        trigger_info=trigger_info,
        logs=LogsRequest(source=LOGS_RUNNER_SOURCE),
    )

    if trigger_id:
        zen_store().create_trigger_execution(
            trigger_id=trigger_id,
            pipeline_run_id=placeholder_run.id,
        )

    report_usage(
        feature=RUN_TEMPLATE_TRIGGERS_FEATURE_NAME,
        resource_id=placeholder_run.id,
    )

    environment = build_runner_environment(
        snapshot=target_snapshot,
        stack=stack,
        run_id=placeholder_run.id,
        auth_context=auth_context,
        zenml_version=zenml_version,
    )
    command = RunnerEntrypointConfiguration.get_entrypoint_command()
    args = RunnerEntrypointConfiguration.get_entrypoint_arguments(
        snapshot_id=target_snapshot.id,
        run_id=placeholder_run.id,
    )
    dockerfile = build_runner_dockerfile(
        stack=stack, build=build, zenml_version=zenml_version
    )

    workload_id = placeholder_run.id if trigger_id else target_snapshot.id
    workload_type = WorkloadType.RUN if trigger_id else WorkloadType.SNAPSHOT

    def _task() -> None:
        with track_handler(
            event=AnalyticsEvent.RUN_PIPELINE
        ) as analytics_handler:
            analytics_handler.metadata = get_pipeline_run_analytics_metadata(
                snapshot=target_snapshot,
                stack=stack,
                source_snapshot_id=snapshot.id,
                run_id=placeholder_run.id,
            )

            analytics_handler.metadata["trigger_execution"] = (
                True if trigger_id else False
            )

            try:
                _build_and_run(
                    workload_id=workload_id,
                    workload_type=workload_type,
                    command=command,
                    arguments=args,
                    environment=environment,
                    dockerfile=dockerfile,
                    wait_for_completion=wait_runner_pod,
                    success_message="Pipeline run started successfully.",
                )
            except Exception:
                logger.exception(
                    "Failed to run snapshot %s, run ID: %s",
                    str(snapshot.id),
                    str(placeholder_run.id),
                )
                run_status = zen_store().get_run_status(placeholder_run.id)
                if run_status == ExecutionStatus.INITIALIZING:
                    # The run isn't in the provisioning status yet, which means
                    # the orchestrator wasn't able to submit the run. In this
                    # case, we can update the run to failed.
                    zen_store().update_run(
                        run_id=placeholder_run.id,
                        run_update=PipelineRunUpdate(
                            status=ExecutionStatus.FAILED,
                            status_reason="Failed to start run.",
                        ),
                    )
                    raise

    if sync:
        _task()
    else:
        try:
            snapshot_executor().submit(_task)
        except MaxConcurrentTasksError:
            zen_store().delete_run(run_id=placeholder_run.id)
            raise MaxConcurrentTasksError(
                "Maximum number of concurrent snapshot tasks reached."
            ) from None

    return placeholder_run


def resume_run(run: PipelineRunResponse) -> None:
    """Resume a run from the server.

    Args:
        run: The pipeline run that should be resumed

    Raises:
        MaxConcurrentTasksError: If workload submission exceeds concurrency
            limits.
        IllegalOperationError: If the run is not resuming.
    """
    if run.status != ExecutionStatus.RESUMING:
        raise IllegalOperationError(
            "Cannot restart a run that is not resuming."
        )

    if not server_config().workload_manager_enabled:
        raise IllegalOperationError(
            "Resuming runs is only possible when the workload manager is enabled."
        )

    snapshot = run.snapshot
    if not run.snapshot or not run.snapshot.runnable:
        raise IllegalOperationError(
            "Cannot resume a run that is not based on a runnable snapshot."
        )
    if not snapshot.is_dynamic:
        raise IllegalOperationError(
            "Cannot resume a run of a static pipeline."
        )

    has_runner_logs = any(
        log.source == LOGS_RUNNER_SOURCE for log in run.log_collection or []
    )
    if not has_runner_logs:
        # TODO: How should we handle multiple resumes here? Currently, the logs
        # simply get appended.
        zen_store().update_run(
            run.id,
            PipelineRunUpdate(
                add_logs=[LogsRequest(source=LOGS_RUNNER_SOURCE)]
            ),
        )

    auth_context = get_auth_context()
    assert auth_context

    build, stack, zenml_version = validate_snapshot_for_server_execution(
        snapshot=snapshot
    )
    environment = build_runner_environment(
        snapshot=snapshot,
        stack=stack,
        run_id=run.id,
        auth_context=auth_context,
        zenml_version=zenml_version,
    )
    command = RunnerEntrypointConfiguration.get_entrypoint_command()
    args = RunnerEntrypointConfiguration.get_entrypoint_arguments(
        snapshot_id=snapshot.id,
        run_id=run.id,
        resume=True,
    )
    dockerfile = build_runner_dockerfile(
        stack=stack, build=build, zenml_version=zenml_version
    )

    def _task() -> None:
        _build_and_run(
            workload_id=run.id,
            workload_type=WorkloadType.RUN,
            command=command,
            arguments=args,
            environment=environment,
            dockerfile=dockerfile,
            wait_for_completion=False,
        )

    # TODO: Do we actually want to check/report usage of this feature here?
    # I assume yes, because it's equivalent to a snapshot run, but is
    # automatically triggered when answering a wait condition.
    check_entitlement(feature=RUN_TEMPLATE_TRIGGERS_FEATURE_NAME)
    try:
        snapshot_executor().submit(_task)
        report_usage(
            feature=RUN_TEMPLATE_TRIGGERS_FEATURE_NAME,
            resource_id=run.id,
        )
    except MaxConcurrentTasksError:
        raise MaxConcurrentTasksError(
            "Maximum number of concurrent snapshot tasks reached."
        ) from None


def ensure_async_orchestrator(
    snapshot: PipelineSnapshotRequest, stack: StackResponse
) -> None:
    """Ensures the orchestrator is configured to run async.

    Args:
        snapshot: Snapshot request in which the orchestrator
            configuration should be updated to ensure the orchestrator is
            running async.
        stack: The stack on which the snapshot will run.
    """
    orchestrator = stack.components[StackComponentType.ORCHESTRATOR][0]
    flavors = zen_store().list_flavors(
        FlavorFilter(name=orchestrator.flavor_name, type=orchestrator.type)
    )
    flavor = Flavor.from_model(flavors[0])

    if "synchronous" in flavor.config_class.model_fields:
        key = settings_utils.get_flavor_setting_key(flavor)

        if settings := snapshot.pipeline_configuration.settings.get(key):
            settings_dict = settings.model_dump()
        else:
            settings_dict = {}

        settings_dict["synchronous"] = False
        snapshot.pipeline_configuration.settings[key] = (
            BaseSettings.model_validate(settings_dict)
        )


def generate_image_hash(dockerfile: str) -> str:
    """Generate a hash of the Dockerfile.

    Args:
        dockerfile: The Dockerfile for which to generate the hash.

    Returns:
        The hash of the Dockerfile.
    """
    hash_ = hashlib.md5()  # nosec
    # Uncomment this line when developing to guarantee a new docker image gets
    # built after restarting the server
    # hash_.update(f"{os.getpid()}".encode())
    hash_.update(dockerfile.encode())
    return hash_.hexdigest()


def generate_dockerfile(
    pypi_requirements: List[str],
    apt_packages: List[str],
    zenml_version: str,
    python_version: str,
) -> str:
    """Generate a Dockerfile that installs the requirements.

    Args:
        pypi_requirements: The PyPI requirements to install.
        apt_packages: The APT packages to install.
        zenml_version: The ZenML version to use as parent image.
        python_version: The Python version to use as parent image.

    Returns:
        The Dockerfile.
    """
    parent_image = os.environ.get(
        ENV_ZENML_RUNNER_PARENT_IMAGE,
        f"zenmldocker/zenml:{zenml_version}-py{python_version}",
    )

    lines = [f"FROM {parent_image}"]
    if apt_packages:
        apt_packages_string = " ".join(f"'{p}'" for p in apt_packages)
        lines.append(
            "RUN apt-get update && apt-get install -y "
            f"--no-install-recommends {apt_packages_string}"
        )

    if pypi_requirements:
        pypi_requirements_string = " ".join(
            [f"'{r}'" for r in pypi_requirements]
        )

        if handle_bool_env_var(
            ENV_ZENML_RUNNER_IMAGE_DISABLE_UV, default=False
        ):
            lines.append(
                f"RUN pip install --default-timeout=60 --no-cache-dir "
                f"{pypi_requirements_string}"
            )
        else:
            lines.append("RUN pip install uv")
            lines.append(
                f"RUN uv pip install --no-cache-dir {pypi_requirements_string}"
            )

    return "\n".join(lines)


def snapshot_request_from_source_snapshot(
    source_snapshot: PipelineSnapshotResponse,
    config: PipelineRunConfiguration,
    template_id: Optional[UUID] = None,
) -> "PipelineSnapshotRequest":
    """Generate a snapshot request from a source snapshot.

    Args:
        source_snapshot: The source snapshot from which to create the
            snapshot request.
        config: The run configuration.
        template_id: The ID of the template from which to create the snapshot
            request.

    Raises:
        ValueError: If there are missing/extra step parameters in the run
            configuration.

    Returns:
        The generated snapshot request.
    """
    assert source_snapshot.stack
    assert source_snapshot.build

    pipeline_update_exclude = {"name"}
    if not source_snapshot.is_dynamic:
        pipeline_update_exclude.add("parameters")

    if config.settings:
        convert_component_shortcut_settings_keys(
            settings=config.settings, stack=source_snapshot.stack
        )

    pipeline_update = config.model_dump(
        include=set(PipelineConfiguration.model_fields),
        exclude=pipeline_update_exclude,
        exclude_unset=True,
        exclude_none=True,
    )
    if pipeline_secrets := pipeline_update.get("secrets", []):
        pipeline_update["secrets"] = [
            zen_store().get_secret_by_name_or_id(secret).id
            for secret in pipeline_secrets
        ]
    pipeline_configuration = pydantic_utils.update_model(
        source_snapshot.pipeline_configuration, pipeline_update
    )

    pipeline_spec = source_snapshot.pipeline_spec
    if pipeline_spec and pipeline_configuration.parameters:
        # Also include the updated pipeline parameters in the pipeline spec, as
        # the frontend and some other code still relies on the parameters in it
        pipeline_spec = pipeline_spec.model_copy(
            update={"parameters": pipeline_configuration.parameters}
        )

    steps = {}
    step_config_updates = config.steps or {}
    for invocation_id, step in source_snapshot.step_configurations.items():
        step_update_model = step_config_updates.get(
            invocation_id, StepConfigurationUpdate()
        )
        if step_update_model.settings:
            convert_component_shortcut_settings_keys(
                settings=step_update_model.settings,
                stack=source_snapshot.stack,
            )
        step_update = step_update_model.model_dump(
            # Get rid of deprecated name to prevent overriding the step name
            # with `None`.
            exclude={"name"},
            exclude_unset=True,
            exclude_none=True,
        )
        if step_secrets := step_update.get("secrets", []):
            step_update["secrets"] = [
                zen_store().get_secret_by_name_or_id(secret).id
                for secret in step_secrets
            ]
        step_config = pydantic_utils.update_model(
            step.step_config_overrides, step_update
        )
        merged_step_config = step_config.apply_pipeline_configuration(
            pipeline_configuration
        )

        required_parameters = set(step.config.parameters)
        configured_parameters = set(step_config.parameters)

        unknown_parameters = configured_parameters - required_parameters
        if unknown_parameters:
            raise ValueError(
                "Run configuration contains the following unknown "
                f"parameters for step {invocation_id}: {unknown_parameters}."
            )

        missing_parameters = required_parameters - configured_parameters
        if missing_parameters:
            raise ValueError(
                "Run configuration is missing the following required "
                f"parameters for step {invocation_id}: {missing_parameters}."
            )

        steps[invocation_id] = Step(
            spec=step.spec,
            config=merged_step_config,
            step_config_overrides=step_config,
        )

    code_reference_request = None
    if source_snapshot.code_reference:
        code_reference_request = CodeReferenceRequest(
            commit=source_snapshot.code_reference.commit,
            subdirectory=source_snapshot.code_reference.subdirectory,
            code_repository=source_snapshot.code_reference.code_repository.id,
        )

    zenml_version = zen_store().get_store_info().version

    # Compute the source snapshot ID:
    # - If the source snapshot has a name, we use it as the source snapshot.
    #   That way, all runs will be associated with this snapshot.
    # - If the source snapshot is based on another snapshot (which therefore
    #   has a name), we use that one instead.
    # - If the source snapshot does not have a name and is not based on another
    #   snapshot, we don't set a source snapshot.
    #
    # With this, we ensure that all runs are associated with the closest named
    # source snapshot.
    source_snapshot_id = None
    if source_snapshot.name:
        source_snapshot_id = source_snapshot.id
    elif source_snapshot.source_snapshot_id:
        source_snapshot_id = source_snapshot.source_snapshot_id

    return PipelineSnapshotRequest(
        project=source_snapshot.project_id,
        is_dynamic=source_snapshot.is_dynamic,
        run_name_template=config.run_name or source_snapshot.run_name_template,
        pipeline_configuration=pipeline_configuration,
        step_configurations=steps,
        client_environment={},
        client_version=zenml_version,
        server_version=zenml_version,
        stack=source_snapshot.stack.id,
        pipeline=source_snapshot.pipeline.id
        if source_snapshot.pipeline
        else None,
        build=source_snapshot.build.id,
        schedule=None,
        code_reference=code_reference_request,
        code_path=source_snapshot.code_path,
        template=template_id,
        source_snapshot=source_snapshot_id,
        pipeline_version_hash=source_snapshot.pipeline_version_hash,
        pipeline_spec=pipeline_spec,
        source_code=source_snapshot.source_code,
    )


def get_pipeline_run_analytics_metadata(
    snapshot: "PipelineSnapshotResponse",
    stack: StackResponse,
    source_snapshot_id: UUID,
    run_id: UUID,
) -> Dict[str, Any]:
    """Get metadata for the pipeline run analytics event.

    Args:
        snapshot: The snapshot of the run.
        stack: The stack on which the run will happen.
        source_snapshot_id: ID of the source snapshot from which the run
            was started.
        run_id: ID of the run.

    Returns:
        The analytics metadata.
    """
    custom_materializer = False
    for step in snapshot.step_configurations.values():
        for output in step.config.outputs.values():
            for source in output.materializer_source:
                if not source.is_internal:
                    custom_materializer = True

    assert snapshot.user_id
    stack_creator = stack.user_id
    own_stack = stack_creator and stack_creator == snapshot.user_id

    stack_metadata = {
        component_type.value: component_list[0].flavor_name
        for component_type, component_list in stack.components.items()
    }

    return {
        "project_id": snapshot.project_id,
        "store_type": "rest",  # This method is called from within a REST endpoint
        **stack_metadata,
        "total_steps": len(snapshot.step_configurations),
        "schedule": snapshot.schedule is not None,
        "custom_materializer": custom_materializer,
        "own_stack": own_stack,
        "pipeline_run_id": str(run_id),
        "source_snapshot_id": str(source_snapshot_id),
    }


def convert_component_shortcut_settings_keys(
    settings: Dict[str, "BaseSettings"], stack: "StackResponse"
) -> None:
    """Convert component shortcut settings keys.

    Args:
        settings: Dictionary of settings.
        stack: The stack response.

    Raises:
        ValueError: If the shortcut key is ambiguous because the stack has
            multiple components of the same type.
        ValueError: If stack component settings were defined both using the
            full and the shortcut key.
    """
    for component_type, component_list in stack.components.items():
        shortcut_key = str(component_type)
        if component_settings := settings.pop(shortcut_key, None):
            if len(component_list) > 1:
                raise ValueError(
                    "Unable to convert shortcut settings key for stack with "
                    f"multiple components of type {component_type}."
                )

            key = f"{component_type}.{component_list[0].flavor_name}"
            if key in settings:
                raise ValueError(
                    f"Duplicate settings provided for your {shortcut_key} "
                    f"using the keys {shortcut_key} and {key}. Remove settings "
                    "for one of them to fix this error."
                )

            settings[key] = component_settings


def validate_snapshot_for_server_execution(
    snapshot: PipelineSnapshotResponse,
    run_configuration: Optional[PipelineRunConfiguration] = None,
) -> Tuple[PipelineBuildResponse, StackResponse, str]:
    """Validate that a snapshot can be executed from the server.

    Args:
        snapshot: Snapshot to validate.
        run_configuration: Optional run configuration to validate as well.

    Raises:
        ValueError: If the snapshot or run configuration is not runnable from
            the server.

    Returns:
        The snapshot build, stack, and ZenML version.
    """
    if not snapshot.runnable:
        if stack := snapshot.stack:
            validate_stack_is_runnable_from_server(
                zen_store=zen_store(), stack=stack
            )
        if not snapshot.build:
            raise ValueError(
                "This snapshot can not be run via the server because it does "
                "not have an associated build. This is probably because the "
                "build has been deleted."
            )

        raise ValueError("This snapshot can not be run via the server.")

    build = snapshot.build
    assert build
    stack = build.stack
    assert stack

    if build.stack_checksum and build.stack_checksum != compute_stack_checksum(
        stack=stack
    ):
        raise ValueError(
            f"The stack {stack.name} has been updated since it was used for "
            "the snapshot. This means the Docker "
            "images associated with this template most likely do not contain "
            "the necessary requirements. Please create a new snapshot with "
            "the updated stack."
        )

    validate_stack_is_runnable_from_server(zen_store=zen_store(), stack=stack)
    if run_configuration:
        validate_run_config_is_runnable_from_server(
            run_configuration, is_dynamic=snapshot.is_dynamic
        )

    assert build.zenml_version
    return build, stack, build.zenml_version


def build_runner_environment(
    snapshot: PipelineSnapshotResponse,
    stack: StackResponse,
    run_id: UUID,
    auth_context: AuthContext,
    zenml_version: str,
) -> Dict[str, str]:
    """Build environment variables for a runner workload.

    Args:
        snapshot: Snapshot to execute.
        stack: Stack to use for the run.
        run_id: Pipeline run ID scoped into the API token.
        auth_context: Authentication context.
        zenml_version: ZenML version to use.

    Raises:
        RuntimeError: If the server URL is not configured.

    Returns:
        Runner workload environment variables.
    """
    server_url = server_config().server_url
    if not server_url:
        raise RuntimeError(
            "The server URL is not set in the server configuration."
        )

    # We create an API token scoped to the pipeline run that never expires.
    api_token = generate_access_token(
        user_id=auth_context.user.id,
        pipeline_run_id=run_id,
        # Keep the original API key or device scopes, if any.
        api_key=auth_context.api_key,
        device=auth_context.device,
        # Never expire the token.
        expires_in=0,
    ).access_token

    return {
        ENV_ZENML_ACTIVE_PROJECT_ID: str(snapshot.project_id),
        ENV_ZENML_ACTIVE_STACK_ID: str(stack.id),
        "ZENML_VERSION": zenml_version,
        "ZENML_STORE_URL": server_url,
        "ZENML_STORE_TYPE": StoreType.REST.value,
        "ZENML_STORE_API_TOKEN": api_token,
        "ZENML_STORE_VERIFY_SSL": "True",
    }


def build_runner_dockerfile(
    stack: StackResponse,
    build: PipelineBuildResponse,
    zenml_version: str,
) -> str:
    """Build the runner Dockerfile.

    Args:
        stack: Stack to use.
        build: Snapshot build metadata.
        zenml_version: ZenML version to use.

    Returns:
        Dockerfile content for the runner workload.
    """
    if build.python_version:
        version_info = version.parse(build.python_version)
        python_version = f"{version_info.major}.{version_info.minor}"
    else:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    pypi_requirements, apt_packages = (
        requirements_utils.get_requirements_for_stack(
            stack=stack, python_version=python_version
        )
    )

    return generate_dockerfile(
        pypi_requirements=pypi_requirements,
        apt_packages=apt_packages,
        zenml_version=zenml_version,
        python_version=python_version,
    )


def _build_and_run(
    workload_id: UUID,
    workload_type: WorkloadType,
    command: List[str],
    arguments: List[str],
    environment: Dict[str, str],
    dockerfile: str,
    wait_for_completion: bool,
    success_message: str | None = None,
) -> None:
    """Build and run a runner workload.

    Args:
        workload_id: Workload ID.
        workload_type: Workload type.
        command: Entrypoint command.
        arguments: Entrypoint arguments.
        environment: Workload environment variables.
        dockerfile: Dockerfile for the runner image.
        wait_for_completion: Whether to wait for the runner workload.
        success_message: Optional message logged after a successful start.
    """
    image_hash = generate_image_hash(dockerfile=dockerfile)
    logger.info(
        "Building runner image %s for dockerfile:\n%s", image_hash, dockerfile
    )

    # Building a Docker image with requirements and apt packages from the
    # stack only (no code). Ideally, only orchestrator requirements should
    # be added to the Docker image, but we have to instantiate the entire
    # stack to get the orchestrator to run pipelines.
    runner_image = workload_manager().build_and_push_image(
        workload_id=workload_id,
        workload_type=workload_type,
        dockerfile=dockerfile,
        image_name=f"{RUNNER_IMAGE_REPOSITORY}:{image_hash}",
        sync=True,
    )

    workload_manager().log(
        workload_id=workload_id,
        message="Starting pipeline run.",
    )

    runner_timeout = handle_int_env_var(
        ENV_ZENML_RUNNER_POD_TIMEOUT, default=180
    )

    # Could do this same thing with a step operator, but we need some
    # minor changes to the abstract interface to support that.
    workload_manager().run(
        workload_id=workload_id,
        image=runner_image,
        command=command,
        arguments=arguments,
        environment=environment,
        timeout_in_seconds=runner_timeout,
        sync=wait_for_completion,
    )
    if success_message:
        workload_manager().log(
            workload_id=workload_id,
            message=success_message,
        )
