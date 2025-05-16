"""Utility functions to run a pipeline from the server."""

import hashlib
import os
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from packaging import version

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
    RUN_TEMPLATE_TRIGGERS_FEATURE_NAME,
    handle_bool_env_var,
    handle_int_env_var,
)
from zenml.enums import ExecutionStatus, StackComponentType, StoreType
from zenml.exceptions import MaxConcurrentTasksError
from zenml.logger import get_logger
from zenml.models import (
    CodeReferenceRequest,
    FlavorFilter,
    PipelineDeploymentRequest,
    PipelineDeploymentResponse,
    PipelineRunResponse,
    PipelineRunUpdate,
    RunTemplateResponse,
    StackResponse,
)
from zenml.pipelines.build_utils import compute_stack_checksum
from zenml.pipelines.run_utils import (
    create_placeholder_run,
    get_default_run_name,
    validate_run_config_is_runnable_from_server,
    validate_stack_is_runnable_from_server,
)
from zenml.stack.flavor import Flavor
from zenml.utils import pydantic_utils, requirements_utils, settings_utils
from zenml.utils.time_utils import utc_now
from zenml.zen_server.auth import AuthContext, generate_access_token
from zenml.zen_server.feature_gate.endpoint_utils import (
    report_usage,
)
from zenml.zen_server.template_execution.runner_entrypoint_configuration import (
    RunnerEntrypointConfiguration,
)
from zenml.zen_server.utils import (
    run_template_executor,
    server_config,
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


def run_template(
    template: RunTemplateResponse,
    auth_context: AuthContext,
    run_config: Optional[PipelineRunConfiguration] = None,
    sync: bool = False,
) -> PipelineRunResponse:
    """Run a pipeline from a template.

    Args:
        template: The template to run.
        auth_context: Authentication context.
        run_config: The run configuration.
        sync: Whether to run the template synchronously.

    Raises:
        ValueError: If the template can not be run.
        RuntimeError: If the server URL is not set in the server configuration.
        MaxConcurrentTasksError: If the maximum number of concurrent run
            template tasks is reached.

    Returns:
        ID of the new pipeline run.
    """
    if not template.runnable:
        raise ValueError(
            "This template can not be run because its associated deployment, "
            "stack or build have been deleted."
        )

    # Guaranteed by the `runnable` check above
    build = template.build
    assert build
    stack = build.stack
    assert stack

    if build.stack_checksum and build.stack_checksum != compute_stack_checksum(
        stack=stack
    ):
        raise ValueError(
            f"The stack {stack.name} has been updated since it was used for "
            "the run that is the base for this template. This means the Docker "
            "images associated with this template most likely do not contain "
            "the necessary requirements. Please create a new template from a "
            "recent run on this stack."
        )

    validate_stack_is_runnable_from_server(zen_store=zen_store(), stack=stack)
    if run_config:
        validate_run_config_is_runnable_from_server(run_config)

    deployment_request = deployment_request_from_template(
        template=template,
        config=run_config or PipelineRunConfiguration(),
    )

    ensure_async_orchestrator(deployment=deployment_request, stack=stack)

    new_deployment = zen_store().create_deployment(deployment_request)

    server_url = server_config().server_url
    if not server_url:
        raise RuntimeError(
            "The server URL is not set in the server configuration."
        )
    assert build.zenml_version
    zenml_version = build.zenml_version

    placeholder_run = create_placeholder_run(deployment=new_deployment)
    assert placeholder_run

    report_usage(
        feature=RUN_TEMPLATE_TRIGGERS_FEATURE_NAME,
        resource_id=placeholder_run.id,
    )

    # We create an API token scoped to the pipeline run that never expires
    api_token = generate_access_token(
        user_id=auth_context.user.id,
        pipeline_run_id=placeholder_run.id,
        # Keep the original API key or device scopes, if any
        api_key=auth_context.api_key,
        device=auth_context.device,
        # Never expire the token
        expires_in=0,
    ).access_token

    environment = {
        ENV_ZENML_ACTIVE_PROJECT_ID: str(new_deployment.project_id),
        ENV_ZENML_ACTIVE_STACK_ID: str(stack.id),
        "ZENML_VERSION": zenml_version,
        "ZENML_STORE_URL": server_url,
        "ZENML_STORE_TYPE": StoreType.REST.value,
        "ZENML_STORE_API_TOKEN": api_token,
        "ZENML_STORE_VERIFY_SSL": "True",
    }

    command = RunnerEntrypointConfiguration.get_entrypoint_command()
    args = RunnerEntrypointConfiguration.get_entrypoint_arguments(
        deployment_id=new_deployment.id
    )

    if build.python_version:
        version_info = version.parse(build.python_version)
        python_version = f"{version_info.major}.{version_info.minor}"
    else:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

    (
        pypi_requirements,
        apt_packages,
    ) = requirements_utils.get_requirements_for_stack(
        stack=stack, python_version=python_version
    )

    dockerfile = generate_dockerfile(
        pypi_requirements=pypi_requirements,
        apt_packages=apt_packages,
        zenml_version=zenml_version,
        python_version=python_version,
    )

    # Building a docker image with requirements and apt packages from the
    # stack only (no code). Ideally, only orchestrator requirements should
    # be added to the docker image, but we have to instantiate the entire
    # stack to get the orchestrator to run pipelines.
    image_hash = generate_image_hash(dockerfile=dockerfile)
    logger.info(
        "Building runner image %s for dockerfile:\n%s", image_hash, dockerfile
    )

    def _task() -> None:
        runner_image = workload_manager().build_and_push_image(
            workload_id=new_deployment.id,
            dockerfile=dockerfile,
            image_name=f"{RUNNER_IMAGE_REPOSITORY}:{image_hash}",
            sync=True,
        )

        workload_manager().log(
            workload_id=new_deployment.id,
            message="Starting pipeline run.",
        )

        runner_timeout = handle_int_env_var(
            ENV_ZENML_RUNNER_POD_TIMEOUT, default=60
        )

        # could do this same thing with a step operator, but we need some
        # minor changes to the abstract interface to support that.
        workload_manager().run(
            workload_id=new_deployment.id,
            image=runner_image,
            command=command,
            arguments=args,
            environment=environment,
            timeout_in_seconds=runner_timeout,
            sync=True,
        )
        workload_manager().log(
            workload_id=new_deployment.id,
            message="Pipeline run started successfully.",
        )

    def _task_with_analytics_and_error_handling() -> None:
        with track_handler(
            event=AnalyticsEvent.RUN_PIPELINE
        ) as analytics_handler:
            analytics_handler.metadata = get_pipeline_run_analytics_metadata(
                deployment=new_deployment,
                stack=stack,
                template_id=template.id,
                run_id=placeholder_run.id,
            )

            try:
                _task()
            except Exception:
                logger.exception(
                    "Failed to run template %s, run ID: %s",
                    str(template.id),
                    str(placeholder_run.id),
                )
                zen_store().update_run(
                    run_id=placeholder_run.id,
                    run_update=PipelineRunUpdate(
                        status=ExecutionStatus.FAILED,
                        end_time=utc_now(),
                    ),
                )
                raise

    if sync:
        _task_with_analytics_and_error_handling()
    else:
        try:
            run_template_executor().submit(
                _task_with_analytics_and_error_handling
            )
        except MaxConcurrentTasksError:
            zen_store().delete_run(run_id=placeholder_run.id)
            raise MaxConcurrentTasksError(
                "Maximum number of concurrent run template tasks reached."
            ) from None

    return placeholder_run


def ensure_async_orchestrator(
    deployment: PipelineDeploymentRequest, stack: StackResponse
) -> None:
    """Ensures the orchestrator is configured to run async.

    Args:
        deployment: Deployment request in which the orchestrator
            configuration should be updated to ensure the orchestrator is
            running async.
        stack: The stack on which the deployment will run.
    """
    orchestrator = stack.components[StackComponentType.ORCHESTRATOR][0]
    flavors = zen_store().list_flavors(
        FlavorFilter(name=orchestrator.flavor_name, type=orchestrator.type)
    )
    flavor = Flavor.from_model(flavors[0])

    if "synchronous" in flavor.config_class.model_fields:
        key = settings_utils.get_flavor_setting_key(flavor)

        if settings := deployment.pipeline_configuration.settings.get(key):
            settings_dict = settings.model_dump()
        else:
            settings_dict = {}

        settings_dict["synchronous"] = False
        deployment.pipeline_configuration.settings[key] = (
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


def deployment_request_from_template(
    template: RunTemplateResponse,
    config: PipelineRunConfiguration,
) -> "PipelineDeploymentRequest":
    """Generate a deployment request from a template.

    Args:
        template: The template from which to create the deployment request.
        config: The run configuration.

    Raises:
        ValueError: If there are missing/extra step parameters in the run
            configuration.

    Returns:
        The generated deployment request.
    """
    deployment = template.source_deployment
    assert deployment

    pipeline_update = config.model_dump(
        include=set(PipelineConfiguration.model_fields),
        exclude={"name", "parameters"},
        exclude_unset=True,
        exclude_none=True,
    )
    pipeline_configuration = pydantic_utils.update_model(
        deployment.pipeline_configuration, pipeline_update
    )

    steps = {}
    for invocation_id, step in deployment.step_configurations.items():
        step_update = config.steps.get(
            invocation_id, StepConfigurationUpdate()
        ).model_dump(
            # Get rid of deprecated name to prevent overriding the step name
            # with `None`.
            exclude={"name"},
            exclude_unset=True,
            exclude_none=True,
        )
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
    if deployment.code_reference:
        code_reference_request = CodeReferenceRequest(
            commit=deployment.code_reference.commit,
            subdirectory=deployment.code_reference.subdirectory,
            code_repository=deployment.code_reference.code_repository.id,
        )

    zenml_version = zen_store().get_store_info().version
    assert deployment.stack
    assert deployment.build
    deployment_request = PipelineDeploymentRequest(
        project=deployment.project_id,
        run_name_template=config.run_name
        or get_default_run_name(pipeline_name=pipeline_configuration.name),
        pipeline_configuration=pipeline_configuration,
        step_configurations=steps,
        client_environment={},
        client_version=zenml_version,
        server_version=zenml_version,
        stack=deployment.stack.id,
        pipeline=deployment.pipeline.id if deployment.pipeline else None,
        build=deployment.build.id,
        schedule=None,
        code_reference=code_reference_request,
        code_path=deployment.code_path,
        template=template.id,
        pipeline_version_hash=deployment.pipeline_version_hash,
        pipeline_spec=deployment.pipeline_spec,
    )

    return deployment_request


def get_pipeline_run_analytics_metadata(
    deployment: "PipelineDeploymentResponse",
    stack: StackResponse,
    template_id: UUID,
    run_id: UUID,
) -> Dict[str, Any]:
    """Get metadata for the pipeline run analytics event.

    Args:
        deployment: The deployment of the run.
        stack: The stack on which the run will happen.
        template_id: ID of the template from which the run was started.
        run_id: ID of the run.

    Returns:
        The analytics metadata.
    """
    custom_materializer = False
    for step in deployment.step_configurations.values():
        for output in step.config.outputs.values():
            for source in output.materializer_source:
                if not source.is_internal:
                    custom_materializer = True

    assert deployment.user_id
    stack_creator = stack.user_id
    own_stack = stack_creator and stack_creator == deployment.user_id

    stack_metadata = {
        component_type.value: component_list[0].flavor_name
        for component_type, component_list in stack.components.items()
    }

    return {
        "project_id": deployment.project_id,
        "store_type": "rest",  # This method is called from within a REST endpoint
        **stack_metadata,
        "total_steps": len(deployment.step_configurations),
        "schedule": deployment.schedule is not None,
        "custom_materializer": custom_materializer,
        "own_stack": own_stack,
        "pipeline_run_id": str(run_id),
        "template_id": str(template_id),
    }
