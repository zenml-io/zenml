"""Utility functions to run a pipeline from the server."""

import copy
import hashlib
import sys
from typing import List, Optional, Set, Tuple
from uuid import UUID

from fastapi import BackgroundTasks
from packaging import version

from zenml.config.base_settings import BaseSettings
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.step_configurations import Step, StepConfiguration
from zenml.constants import (
    ENV_ZENML_ACTIVE_STACK_ID,
    ENV_ZENML_ACTIVE_WORKSPACE_ID,
)
from zenml.enums import StackComponentType, StoreType
from zenml.integrations.utils import get_integration_for_module
from zenml.models import (
    CodeReferenceRequest,
    ComponentResponse,
    FlavorFilter,
    PipelineDeploymentRequest,
    PipelineDeploymentResponse,
    PipelineRunResponse,
    StackResponse,
)
from zenml.new.pipelines.run_utils import (
    create_placeholder_run,
    validate_run_config_is_runnable_from_server,
    validate_stack_is_runnable_from_server,
)
from zenml.stack.flavor import Flavor
from zenml.utils import dict_utils, pydantic_utils, settings_utils
from zenml.zen_server.auth import AuthContext
from zenml.zen_server.pipeline_deployment.runner_entrypoint_configuration import (
    RunnerEntrypointConfiguration,
)
from zenml.zen_server.utils import server_config, workload_manager, zen_store

RUNNER_IMAGE_REPOSITORY = "zenml-runner"


def run_pipeline(
    deployment: PipelineDeploymentResponse,
    auth_context: AuthContext,
    background_tasks: Optional[BackgroundTasks] = None,
    run_config: Optional[PipelineRunConfiguration] = None,
) -> PipelineRunResponse:
    """Run a pipeline from an existing deployment.

    Args:
        deployment: The pipeline deployment.
        auth_context: Authentication context.
        background_tasks: Background tasks.
        run_config: The run configuration.

    Raises:
        ValueError: If the deployment does not have an associated stack or
            build.
        RuntimeError: If the server URL is not set in the server configuration.

    Returns:
        ID of the new pipeline run.
    """
    build = deployment.build
    stack = deployment.stack

    if not build:
        raise ValueError("Unable to run deployment without associated build.")

    if not stack:
        raise ValueError("Unable to run deployment without associated stack.")

    validate_stack_is_runnable_from_server(zen_store=zen_store(), stack=stack)
    if run_config:
        validate_run_config_is_runnable_from_server(run_config)

    deployment_request = apply_run_config(
        deployment=deployment,
        run_config=run_config or PipelineRunConfiguration(),
        user_id=auth_context.user.id,
    )

    ensure_async_orchestrator(deployment=deployment_request, stack=stack)

    new_deployment = zen_store().create_deployment(deployment_request)
    placeholder_run = create_placeholder_run(deployment=new_deployment)
    assert placeholder_run

    if auth_context.access_token:
        token = auth_context.access_token
        token.pipeline_id = deployment_request.pipeline

        # We create a non-expiring token to make sure its active for the entire
        # duration of the pipeline run
        api_token = token.encode(expires=None)
    else:
        assert auth_context.encoded_access_token
        api_token = auth_context.encoded_access_token

    server_url = server_config().server_url
    if not server_url:
        raise RuntimeError(
            "The server URL is not set in the server configuration"
        )
    assert build.zenml_version
    zenml_version = build.zenml_version

    environment = {
        ENV_ZENML_ACTIVE_WORKSPACE_ID: str(new_deployment.workspace.id),
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

    def _task() -> None:
        pypi_requirements, apt_packages = get_requirements_for_stack(
            stack=stack
        )

        if build.python_version:
            version_info = version.parse(build.python_version)
            python_version = f"{version_info.major}.{version_info.minor}"
        else:
            python_version = (
                f"{sys.version_info.major}.{sys.version_info.minor}"
            )

        dockerfile = generate_dockerfile(
            pypi_requirements=pypi_requirements,
            apt_packages=apt_packages,
            zenml_version=zenml_version,
            python_version=python_version,
        )

        image_hash = generate_image_hash(dockerfile=dockerfile)

        runner_image = workload_manager().build_and_push_image(
            workload_id=new_deployment.id,
            dockerfile=dockerfile,
            image_name=f"{RUNNER_IMAGE_REPOSITORY}:{image_hash}",
            sync=True,
        )

        workload_manager().log(
            workload_id=new_deployment.id,
            message="Starting pipeline deployment.",
        )
        workload_manager().run(
            workload_id=new_deployment.id,
            image=runner_image,
            command=command,
            arguments=args,
            environment=environment,
            timeout_in_seconds=30,
            sync=True,
        )
        workload_manager().log(
            workload_id=new_deployment.id,
            message="Pipeline deployed successfully.",
        )

    if background_tasks:
        background_tasks.add_task(_task)
    else:
        # Run synchronously if no background tasks were passed. This is probably
        # when coming from a trigger which itself is already running in the
        # background
        _task()

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
        FlavorFilter(name=orchestrator.flavor, type=orchestrator.type)
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


def get_requirements_for_stack(
    stack: StackResponse,
) -> Tuple[List[str], List[str]]:
    """Get requirements for a stack model.

    Args:
        stack: The stack for which to get the requirements.

    Returns:
        Tuple of PyPI and APT requirements of the stack.
    """
    pypi_requirements: Set[str] = set()
    apt_packages: Set[str] = set()

    for component_list in stack.components.values():
        assert len(component_list) == 1
        component = component_list[0]
        (
            component_pypi_requirements,
            component_apt_packages,
        ) = get_requirements_for_component(component=component)
        pypi_requirements = pypi_requirements.union(
            component_pypi_requirements
        )
        apt_packages = apt_packages.union(component_apt_packages)

    return sorted(pypi_requirements), sorted(apt_packages)


def get_requirements_for_component(
    component: ComponentResponse,
) -> Tuple[List[str], List[str]]:
    """Get requirements for a component model.

    Args:
        component: The component for which to get the requirements.

    Returns:
        Tuple of PyPI and APT requirements of the component.
    """
    flavors = zen_store().list_flavors(
        FlavorFilter(name=component.flavor, type=component.type)
    )
    assert len(flavors) == 1
    flavor_source = flavors[0].source
    integration = get_integration_for_module(module_name=flavor_source)

    if integration:
        return integration.get_requirements(), integration.APT_PACKAGES
    else:
        return [], []


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
    parent_image = f"zenmldocker/zenml:{zenml_version}-py{python_version}"

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
        lines.append(
            f"RUN pip install --default-timeout=60 --no-cache-dir "
            f"{pypi_requirements_string}"
        )

    return "\n".join(lines)


def apply_run_config(
    deployment: "PipelineDeploymentResponse",
    run_config: "PipelineRunConfiguration",
    user_id: UUID,
) -> "PipelineDeploymentRequest":
    """Apply run configuration to a deployment.

    Args:
        deployment: The deployment to which to apply the config.
        run_config: The run configuration to apply.
        user_id: The ID of the user that wants to run the deployment.

    Returns:
        The updated deployment.
    """
    pipeline_updates = run_config.model_dump(
        exclude_none=True, include=set(PipelineConfiguration.model_fields)
    )

    pipeline_configuration = pydantic_utils.update_model(
        deployment.pipeline_configuration, update=pipeline_updates
    )
    pipeline_configuration_dict = pipeline_configuration.model_dump(
        exclude_none=True
    )
    steps = {}
    for invocation_id, step in deployment.step_configurations.items():
        step_config_dict = dict_utils.recursive_update(
            copy.deepcopy(pipeline_configuration_dict),
            update=step.config.model_dump(exclude_none=True),
        )
        step_config = StepConfiguration.model_validate(step_config_dict)

        if update := run_config.steps.get(invocation_id):
            update_dict = update.model_dump()
            # Get rid of deprecated name to prevent overriding the step name
            # with `None`.
            update_dict.pop("name", None)
            step_config = pydantic_utils.update_model(
                step_config, update=update_dict
            )
        steps[invocation_id] = Step(spec=step.spec, config=step_config)

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
        user=user_id,
        workspace=deployment.workspace.id,
        run_name_template=run_config.run_name or deployment.run_name_template,
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
    )

    return deployment_request
