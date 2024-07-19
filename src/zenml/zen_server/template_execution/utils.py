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
from zenml.config.pipeline_run_configuration import (
    PipelineRunConfiguration,
)
from zenml.config.step_configurations import Step, StepConfiguration
from zenml.constants import (
    ENV_ZENML_ACTIVE_STACK_ID,
    ENV_ZENML_ACTIVE_WORKSPACE_ID,
)
from zenml.enums import ExecutionStatus, StackComponentType, StoreType
from zenml.integrations.utils import get_integration_for_module
from zenml.logger import get_logger
from zenml.models import (
    CodeReferenceRequest,
    ComponentResponse,
    FlavorFilter,
    PipelineDeploymentRequest,
    PipelineRunResponse,
    PipelineRunUpdate,
    RunTemplateResponse,
    StackResponse,
)
from zenml.new.pipelines.build_utils import compute_stack_checksum
from zenml.new.pipelines.run_utils import (
    create_placeholder_run,
    get_default_run_name,
    validate_run_config_is_runnable_from_server,
    validate_stack_is_runnable_from_server,
)
from zenml.stack.flavor import Flavor
from zenml.utils import dict_utils, settings_utils
from zenml.zen_server.auth import AuthContext
from zenml.zen_server.template_execution.runner_entrypoint_configuration import (
    RunnerEntrypointConfiguration,
)
from zenml.zen_server.utils import server_config, workload_manager, zen_store

logger = get_logger(__name__)

RUNNER_IMAGE_REPOSITORY = "zenml-runner"


def run_template(
    template: RunTemplateResponse,
    auth_context: AuthContext,
    background_tasks: Optional[BackgroundTasks] = None,
    run_config: Optional[PipelineRunConfiguration] = None,
) -> PipelineRunResponse:
    """Run a pipeline from a template.

    Args:
        template: The template to run.
        auth_context: Authentication context.
        background_tasks: Background tasks.
        run_config: The run configuration.

    Raises:
        ValueError: If the template can not be run.
        RuntimeError: If the server URL is not set in the server configuration.

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
        user_id=auth_context.user.id,
    )

    ensure_async_orchestrator(deployment=deployment_request, stack=stack)

    new_deployment = zen_store().create_deployment(deployment_request)

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
            "The server URL is not set in the server configuration."
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

    placeholder_run = create_placeholder_run(deployment=new_deployment)
    assert placeholder_run

    def _task() -> None:
        try:
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
                message="Starting pipeline run.",
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
                message="Pipeline run started successfully.",
            )
        except Exception:
            logger.exception(
                "Failed to run template %s, run ID: %s",
                str(template.id),
                str(placeholder_run.id),
            )
            zen_store().update_run(
                run_id=placeholder_run.id,
                run_update=PipelineRunUpdate(status=ExecutionStatus.FAILED),
            )
            raise

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


def deployment_request_from_template(
    template: RunTemplateResponse,
    config: PipelineRunConfiguration,
    user_id: UUID,
) -> "PipelineDeploymentRequest":
    """Generate a deployment request from a template.

    Args:
        template: The template from which to create the deployment request.
        config: The run configuration.
        user_id: ID of the user that is trying to run the template.

    Raises:
        ValueError: If the run configuration is missing step parameters.

    Returns:
        The generated deployment request.
    """
    deployment = template.source_deployment
    assert deployment
    pipeline_configuration = PipelineConfiguration(
        **config.model_dump(
            include=set(PipelineConfiguration.model_fields),
            exclude={"name", "parameters"},
        ),
        name=deployment.pipeline_configuration.name,
        parameters=deployment.pipeline_configuration.parameters,
    )

    step_config_dict_base = pipeline_configuration.model_dump(
        exclude={"name", "parameters"}
    )
    steps = {}
    for invocation_id, step in deployment.step_configurations.items():
        step_config_dict = {
            **copy.deepcopy(step_config_dict_base),
            **step.config.model_dump(
                # TODO: Maybe we need to make some of these configurable via
                # yaml as well, e.g. the lazy loaders?
                include={
                    "name",
                    "caching_parameters",
                    "external_input_artifacts",
                    "model_artifacts_or_metadata",
                    "client_lazy_loaders",
                    "outputs",
                }
            ),
        }

        required_parameters = set(step.config.parameters)
        configured_parameters = set()

        if update := config.steps.get(invocation_id):
            update_dict = update.model_dump()
            # Get rid of deprecated name to prevent overriding the step name
            # with `None`.
            update_dict.pop("name", None)
            configured_parameters = set(update.parameters)
            step_config_dict = dict_utils.recursive_update(
                step_config_dict, update=update_dict
            )

        if configured_parameters != required_parameters:
            missing_parameters = required_parameters - configured_parameters
            raise ValueError(
                "Run configuration is missing missing the following required "
                f"parameters for step {step.config.name}: {missing_parameters}."
            )

        step_config = StepConfiguration.model_validate(step_config_dict)
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
        template=template.id,
        pipeline_version_hash=deployment.pipeline_version_hash,
        pipeline_spec=deployment.pipeline_spec,
    )

    return deployment_request


from enum import Enum
from typing import Any, Dict, Optional

from pydantic import create_model

from zenml.client import Client
from zenml.config import ResourceSettings
from zenml.config.step_configurations import StepConfigurationUpdate
from zenml.stack import Flavor


def generate_config_schema(
    stack: StackResponse, config: PipelineRunConfiguration
) -> Dict[str, Any]:
    """Generate a JSON config schema for the stack and run configuration.

    Args:
        stack: The stack.
        config: The run configuration.

    Returns:
        The generated schema dictionary.
    """
    experiment_trackers = []
    step_operators = []

    settings_fields = {"resources": (ResourceSettings, None)}
    for component_list in stack.components.values():
        assert len(component_list) == 1
        component = component_list[0]
        flavors = Client().zen_store.list_flavors(
            FlavorFilter(name=component.flavor, type=component.type)
        )
        assert len(flavors) == 1
        flavor_model = flavors[0]
        flavor = Flavor.from_model(flavor_model)

        for class_ in flavor.config_class.__mro__[1:]:
            # Ugly hack to get the settings class of a flavor without having
            # the integration installed. This is based on the convention that
            # the static config of a stack component should always inherit
            # from the dynamic settings.
            if issubclass(class_, BaseSettings):
                if len(class_.model_fields) > 0:
                    settings_key = f"{component.type}.{component.flavor}"
                    settings_fields[settings_key] = (
                        class_,
                        None,
                    )

                break

        if component.type == StackComponentType.EXPERIMENT_TRACKER:
            experiment_trackers.append(component.name)
        if component.type == StackComponentType.STEP_OPERATOR:
            step_operators.append(component.name)

    settings_model = create_model("Settings", **settings_fields)

    generic_step_fields = {}

    for key, field_info in StepConfigurationUpdate.model_fields.items():
        if key in [
            "name",
            "outputs",
            "step_operator",
            "experiment_tracker",
            "parameters",
        ]:
            continue

        generic_step_fields[key] = (field_info.annotation, field_info)

    if experiment_trackers:
        experiment_tracker_enum = Enum(
            "ExperimentTrackers", {e: e for e in experiment_trackers}
        )
        generic_step_fields["experiment_tracker"] = (
            experiment_tracker_enum,
            None,
        )
    if step_operators:
        step_operator_enum = Enum(
            "StepOperators", {s: s for s in step_operators}
        )
        generic_step_fields["step_operator"] = (step_operator_enum, None)

    generic_step_fields["settings"] = (settings_model, None)

    all_steps = {}
    for name, step_config in config.steps.items():
        step_fields = generic_step_fields.copy()
        if step_config.parameters:
            parameter_fields = {
                name: (Any, None) for name in step_config.parameters
            }
            parameters_class = create_model(
                f"{name}_parameters", **parameter_fields
            )
            step_fields["parameters"] = (parameters_class, None)

        step_model = create_model(name, **step_fields)
        all_steps[name] = (step_model, None)

    all_steps_model = create_model("Steps", **all_steps)

    top_level_fields = {}

    for key, field_info in PipelineRunConfiguration.model_fields.items():
        if key in ["schedule", "build", "steps", "settings", "parameters"]:
            continue

        top_level_fields[key] = (field_info.annotation, field_info)

    top_level_fields["settings"] = (settings_model, None)
    top_level_fields["steps"] = (all_steps_model, None)

    return create_model("Result", **top_level_fields).model_json_schema()
