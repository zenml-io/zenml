#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Databricks utilities."""

import os
import re
import sys
from importlib.metadata import distribution
from typing import TYPE_CHECKING, Dict, List, Optional

from databricks.sdk import WorkspaceClient as DatabricksClient
from databricks.sdk.errors import NotFound
from databricks.sdk.service import iam
from databricks.sdk.service.compute import (
    AutoScale,
    AwsAttributes,
    AwsAvailability,
    AzureAttributes,
    AzureAvailability,
    ClientsTypes,
    ClusterSpec,
    DbfsStorageInfo,
    DockerBasicAuth,
    DockerImage,
    GcpAttributes,
    GcpAvailability,
    InitScriptInfo,
    Library,
    PythonPyPiLibrary,
    WorkloadType,
)
from databricks.sdk.service.jobs import (
    PythonWheelTask,
    Run,
    RunLifeCycleState,
    RunResultState,
    SubmitTask,
    TaskDependency,
)
from databricks.sdk.service.jobs import Task as DatabricksTask
from databricks.sdk.service.workspace import ImportFormat

from zenml import __version__
from zenml.constants import ENV_ZENML_CUSTOM_SOURCE_ROOT
from zenml.enums import ExecutionStatus
from zenml.integrations.databricks.flavors.databricks_shared_settings import (
    DatabricksAvailabilityType,
    DatabricksBaseSettings,
)
from zenml.logger import get_logger
from zenml.utils.package_utils import clean_requirements
from zenml.utils.pipeline_docker_image_builder import (
    PipelineDockerImageBuilder,
)

if TYPE_CHECKING:
    from zenml.config import DockerSettings
    from zenml.stack import Stack

logger = get_logger(__name__)

DATABRICKS_WHEELS_DIRECTORY_PREFIX = "/Workspace/Shared/.zenml"
DATABRICKS_SPARK_DEFAULT_VERSION = "16.4.x-scala2.12"
DATABRICKS_DEFAULT_NODE_TYPE_ID = "Standard_D4s_v5"
DATABRICKS_ZENML_DEFAULT_CUSTOM_REPOSITORY_PATH = "."
ENV_ZENML_DATABRICKS_WHEEL_PACKAGE = "ZENML_DATABRICKS_WHEEL_PACKAGE"
_ZENML_REQUIREMENT_PATTERN = re.compile(
    r"^\s*zenml(?:\[[^\]]+\])?(?:\s*(?:[<>=!~]=?|@)|\s*;|\s*$)",
    re.IGNORECASE,
)
_AZURE_AVAILABILITY_BY_TYPE = {
    "ON_DEMAND": AzureAvailability.ON_DEMAND_AZURE,
    "SPOT": AzureAvailability.SPOT_AZURE,
    "SPOT_WITH_FALLBACK": AzureAvailability.SPOT_WITH_FALLBACK_AZURE,
}
_GCP_AVAILABILITY_BY_TYPE = {
    "ON_DEMAND": GcpAvailability.ON_DEMAND_GCP,
    "SPOT": GcpAvailability.PREEMPTIBLE_GCP,
    "SPOT_WITH_FALLBACK": GcpAvailability.PREEMPTIBLE_WITH_FALLBACK_GCP,
}


def _is_pip_option(requirement: str) -> bool:
    """Check whether a requirements line is a pip option.

    Args:
        requirement: Requirements file line.

    Returns:
        Whether the line is a pip option instead of a package requirement.
    """
    return requirement.lstrip().startswith("-")


def collect_requirements(
    docker_settings: "DockerSettings", stack: "Stack"
) -> List[str]:
    """Collect clean Python requirements for Databricks wheel execution.

    Args:
        docker_settings: Docker settings attached to the step or pipeline.
        stack: The active stack.

    Returns:
        A sorted list of clean requirements.
    """
    docker_image_builder = PipelineDockerImageBuilder()
    requirements_files = docker_image_builder.gather_requirements_files(
        docker_settings=docker_settings,
        stack=stack,
        log=False,
    )
    ignored_pip_options = {
        filename: pip_options
        for filename, _, pip_options in requirements_files
        if pip_options
    }
    if ignored_pip_options:
        logger.warning(
            "Databricks PyPI libraries do not support arbitrary pip "
            "options from requirements files. The following pip options "
            "will not be applied: %s",
            ignored_pip_options,
        )

    requirements = [
        line
        for _, content, _ in requirements_files
        for line in content.strip().split("\n")
        if line
    ]
    pip_option_requirements = [
        requirement
        for requirement in requirements
        if _is_pip_option(requirement)
    ]
    if pip_option_requirements:
        logger.warning(
            "Databricks PyPI libraries do not support pip options inside "
            "requirements files. The following requirement lines will not "
            "be applied: %s",
            pip_option_requirements,
        )
        requirements = [
            requirement
            for requirement in requirements
            if not _is_pip_option(requirement)
        ]

    return clean_requirements(sorted(set(requirements)))


def upload_wheel_to_workspace(
    databricks_client: DatabricksClient,
    wheel_path: str,
    databricks_directory: str,
) -> str:
    """Upload a wheel file to a Databricks workspace directory.

    Args:
        databricks_client: Databricks client.
        wheel_path: Local wheel path.
        databricks_directory: Remote Databricks directory path.

    Raises:
        RuntimeError: If the wheel upload fails.

    Returns:
        The Databricks workspace wheel path.
    """
    wheel_filename = os.path.basename(wheel_path)
    databricks_wheel_path = f"{databricks_directory}/{wheel_filename}"

    try:
        databricks_client.workspace.mkdirs(path=databricks_directory)
        with open(wheel_path, "rb") as f:
            databricks_client.workspace.upload(
                path=databricks_wheel_path,
                content=f.read(),
                format=ImportFormat.AUTO,
                overwrite=True,
            )
    except Exception as e:
        raise RuntimeError(
            f"Failed to upload wheel file to Databricks workspace at "
            f"{databricks_wheel_path}. Ensure your Databricks workspace has "
            f"the necessary permissions and the path is accessible. "
            f"Original error: {e}"
        ) from e

    logger.info(
        "Successfully uploaded wheel to Databricks workspace: %s",
        databricks_wheel_path,
    )
    return databricks_wheel_path


def delete_workspace_directory(
    databricks_client: DatabricksClient,
    databricks_directory: str,
    context: str,
) -> None:
    """Delete a Databricks workspace directory best-effort.

    Args:
        databricks_client: Databricks client.
        databricks_directory: Workspace directory to delete.
        context: Context for warning logs if cleanup fails.
    """
    try:
        databricks_client.workspace.delete(
            path=databricks_directory,
            recursive=True,
        )
    except NotFound:
        logger.debug(
            "Databricks workspace wheel directory `%s` was already "
            "deleted after %s.",
            databricks_directory,
            context,
        )
    except Exception as e:
        logger.warning(
            "Failed to delete Databricks workspace wheel directory `%s` "
            "after %s: %s",
            databricks_directory,
            context,
            e,
        )


def _get_wheel_package_project_root(wheel_package: str) -> str:
    """Get the absolute project root for an installed wheel package.

    Args:
        wheel_package: The generated wheel package name.

    Returns:
        Absolute path to the package root inside the installed wheel.
    """
    dist = distribution(wheel_package)
    return os.path.abspath(
        os.path.join(str(dist.locate_file(".")), wheel_package)
    )


def add_wheel_package_to_sys_path(wheel_package: str) -> str:
    """Add the generated wheel package root to the Python path.

    Args:
        wheel_package: The generated wheel package name.

    Returns:
        Absolute path to the package root inside the installed wheel.
    """
    project_root = _get_wheel_package_project_root(wheel_package)

    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    return project_root


def configure_databricks_wheel_environment(wheel_package: str) -> str:
    """Configure runtime environment variables for a Databricks wheel.

    Args:
        wheel_package: The generated wheel package name.

    Returns:
        Absolute path to the package root inside the installed wheel.
    """
    project_root = add_wheel_package_to_sys_path(wheel_package)
    os.environ[ENV_ZENML_DATABRICKS_WHEEL_PACKAGE] = wheel_package
    os.environ[ENV_ZENML_CUSTOM_SOURCE_ROOT] = project_root
    return project_root


def get_databricks_wheel_source() -> Optional[tuple[str, str]]:
    """Get the source root and package name of an installed Databricks wheel.

    When code is already running from a Databricks wheel, building a new wheel
    from the active custom source root can point at the Databricks working
    directory instead of the packaged project source. In that case we rebuild
    from the installed wheel package contents instead.

    Returns:
        Tuple of (source_root, package_name) if running from a Databricks wheel,
        otherwise None.
    """
    wheel_package = os.environ.get(ENV_ZENML_DATABRICKS_WHEEL_PACKAGE)
    if not wheel_package:
        return None

    return _get_wheel_package_project_root(wheel_package), wheel_package


def _has_zenml_requirement(libraries: Optional[List[str]]) -> bool:
    """Check whether libraries already include a ZenML requirement.

    Args:
        libraries: Python package requirements.

    Returns:
        Whether a ZenML package requirement is already present.
    """
    return any(
        _ZENML_REQUIREMENT_PATTERN.match(library)
        for library in libraries or []
    )


def _get_databricks_libraries(
    libraries: Optional[List[str]],
    zenml_project_wheel: Optional[str],
) -> List[Library]:
    """Build Databricks library descriptors for a task.

    Args:
        libraries: Python package requirements or wheel paths to install.
        zenml_project_wheel: Optional workspace path to the generated ZenML
            project wheel.

    Returns:
        Databricks library descriptors for the task.
    """
    db_libraries = []
    if libraries:
        for library in libraries:
            if library.endswith(".whl"):
                db_libraries.append(Library(whl=library))
            else:
                db_libraries.append(Library(pypi=PythonPyPiLibrary(library)))
    if zenml_project_wheel:
        db_libraries.append(Library(whl=zenml_project_wheel))
    if not _has_zenml_requirement(libraries):
        db_libraries.append(
            Library(pypi=PythonPyPiLibrary(f"zenml=={__version__}"))
        )
    return db_libraries


def convert_step_to_task(
    task_name: str,
    command: str,
    arguments: List[str],
    libraries: Optional[List[str]] = None,
    depends_on: Optional[List[str]] = None,
    zenml_project_wheel: Optional[str] = None,
    job_cluster_key: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    max_retries: Optional[int] = None,
    min_retry_interval_millis: Optional[int] = None,
    retry_on_timeout: Optional[bool] = None,
) -> DatabricksTask:
    """Convert a ZenML step to a Databricks task.

    Args:
        task_name: Name of the task.
        command: Command to run.
        arguments: Arguments to pass to the command.
        libraries: List of libraries to install.
        depends_on: List of tasks to depend on.
        zenml_project_wheel: Path to the ZenML project wheel.
        job_cluster_key: ID of the Databricks job_cluster_key.
        timeout_seconds: Timeout in seconds for the task.
        max_retries: Maximum number of retries for a failed task.
        min_retry_interval_millis: Minimum interval between retries
            in milliseconds.
        retry_on_timeout: Whether to retry on timeout.

    Returns:
        Databricks task.
    """
    return DatabricksTask(
        task_key=task_name,
        job_cluster_key=job_cluster_key,
        libraries=_get_databricks_libraries(
            libraries=libraries,
            zenml_project_wheel=zenml_project_wheel,
        ),
        python_wheel_task=PythonWheelTask(
            package_name="zenml",
            entry_point=command,
            parameters=arguments,
        ),
        depends_on=[TaskDependency(task) for task in depends_on]
        if depends_on
        else None,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        min_retry_interval_millis=min_retry_interval_millis,
        retry_on_timeout=retry_on_timeout,
    )


def convert_step_to_submit_task(
    task_name: str,
    command: str,
    arguments: List[str],
    new_cluster: ClusterSpec,
    libraries: Optional[List[str]] = None,
    zenml_project_wheel: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
) -> SubmitTask:
    """Convert a ZenML step to a Databricks submit task.

    Args:
        task_name: Name of the task.
        command: Command to run.
        arguments: Arguments to pass to the command.
        new_cluster: Cluster spec for the submit task.
        libraries: List of libraries to install.
        zenml_project_wheel: Path to the ZenML project wheel.
        timeout_seconds: Timeout in seconds for the task.

    Returns:
        Databricks submit task.
    """
    return SubmitTask(
        task_key=task_name,
        libraries=_get_databricks_libraries(
            libraries=libraries,
            zenml_project_wheel=zenml_project_wheel,
        ),
        new_cluster=new_cluster,
        python_wheel_task=PythonWheelTask(
            package_name="zenml",
            entry_point=command,
            parameters=arguments,
        ),
        timeout_seconds=timeout_seconds,
    )


def _resolve_policy_id(
    databricks_client: DatabricksClient, policy_id: Optional[str]
) -> Optional[str]:
    """Resolve the Databricks cluster policy ID.

    Args:
        databricks_client: Databricks client.
        policy_id: Configured policy ID.

    Returns:
        Policy ID to use, or None if no default policy exists.
    """
    if policy_id is not None:
        databricks_client.cluster_policies.get(policy_id=policy_id)
        return policy_id

    for policy in databricks_client.cluster_policies.list():
        if policy.name == "Job Compute":
            assert policy.policy_id is not None
            return policy.policy_id

    logger.debug(
        "Could not find the default `Job Compute` Databricks cluster policy. "
        "Submitting the cluster without a policy ID."
    )
    return None


DatabricksAvailabilityAttributes = tuple[
    Optional[AwsAttributes], Optional[AzureAttributes], Optional[GcpAttributes]
]


def _get_cloud_availability_attributes(
    databricks_client: DatabricksClient,
    availability_type: Optional[DatabricksAvailabilityType],
) -> DatabricksAvailabilityAttributes:
    """Build cloud-specific cluster availability attributes.

    Args:
        databricks_client: Databricks client.
        availability_type: Configured availability type.

    Returns:
        ClusterSpec keyword arguments for availability settings.
    """
    if availability_type is None:
        return None, None, None

    availability = availability_type.value
    host = (databricks_client.config.host or "").lower()

    if "azuredatabricks" in host:
        return (
            None,
            AzureAttributes(
                availability=_AZURE_AVAILABILITY_BY_TYPE[availability]
            ),
            None,
        )

    if "gcp.databricks" in host or ".gcp." in host:
        return (
            None,
            None,
            GcpAttributes(
                availability=_GCP_AVAILABILITY_BY_TYPE[availability]
            ),
        )

    return (
        AwsAttributes(availability=AwsAvailability(availability)),
        None,
        None,
    )


def _build_init_script_info(script: str) -> InitScriptInfo:
    """Build a Databricks init script descriptor.

    Args:
        script: DBFS init script path. Validated to start with ``dbfs:/`` by
            ``DatabricksBaseSettings._validate_init_script_paths``.

    Returns:
        Databricks init script descriptor.
    """
    return InitScriptInfo(dbfs=DbfsStorageInfo(destination=script))


def build_databricks_cluster_spec(
    databricks_client: DatabricksClient,
    settings: DatabricksBaseSettings,
    env_vars: Dict[str, str],
) -> ClusterSpec:
    """Build a Databricks cluster spec from shared settings.

    Args:
        databricks_client: Databricks client.
        settings: Databricks settings.
        env_vars: Environment variables for the cluster.

    Returns:
        Cluster spec.
    """
    docker_image = None
    if settings.docker_image_url:
        basic_auth = None
        if settings.docker_image_username:
            basic_auth = DockerBasicAuth(
                username=settings.docker_image_username,
                password=settings.docker_image_password,
            )
        docker_image = DockerImage(
            url=settings.docker_image_url,
            basic_auth=basic_auth,
        )

    init_scripts = None
    if settings.init_scripts:
        init_scripts = [
            _build_init_script_info(script) for script in settings.init_scripts
        ]

    aws_attributes, azure_attributes, gcp_attributes = (
        _get_cloud_availability_attributes(
            databricks_client=databricks_client,
            availability_type=settings.availability_type,
        )
    )

    num_workers = None
    autoscale = None
    if settings.num_workers is not None:
        num_workers = settings.num_workers
    else:
        autoscale = AutoScale(
            min_workers=settings.autoscale[0],
            max_workers=settings.autoscale[1],
        )

    return ClusterSpec(
        spark_version=settings.spark_version
        or DATABRICKS_SPARK_DEFAULT_VERSION,
        node_type_id=settings.node_type_id or DATABRICKS_DEFAULT_NODE_TYPE_ID,
        driver_node_type_id=settings.driver_node_type_id,
        policy_id=_resolve_policy_id(databricks_client, settings.policy_id),
        single_user_name=settings.single_user_name,
        spark_env_vars=env_vars,
        spark_conf=settings.spark_conf or {},
        workload_type=WorkloadType(
            clients=ClientsTypes(jobs=True, notebooks=False)
        ),
        custom_tags=settings.custom_tags,
        docker_image=docker_image,
        init_scripts=init_scripts,
        autotermination_minutes=settings.autotermination_minutes,
        num_workers=num_workers,
        autoscale=autoscale,
        aws_attributes=aws_attributes,
        azure_attributes=azure_attributes,
        gcp_attributes=gcp_attributes,
    )


def build_access_control_list(
    settings: DatabricksBaseSettings,
) -> Optional[List[iam.AccessControlRequest]]:
    """Build access control entries for Databricks jobs and runs.

    Args:
        settings: Databricks settings.

    Returns:
        Access control list or None.
    """
    if not settings.access_control_list:
        return None

    return [
        iam.AccessControlRequest(
            group_name=acl.group_name,
            user_name=acl.user_name,
            service_principal_name=acl.service_principal_name,
            permission_level=iam.PermissionLevel(acl.permission_level.value),
        )
        for acl in settings.access_control_list
    ]


def map_databricks_run_to_execution_status(run: Run) -> ExecutionStatus:
    """Map a Databricks run state to a ZenML execution status.

    Args:
        run: Databricks run.

    Returns:
        ZenML execution status.
    """
    state = run.state
    if state is None or state.life_cycle_state is None:
        return ExecutionStatus.FAILED

    life_cycle_state = state.life_cycle_state
    if life_cycle_state in {
        RunLifeCycleState.BLOCKED,
        RunLifeCycleState.PENDING,
        RunLifeCycleState.QUEUED,
        RunLifeCycleState.RUNNING,
        RunLifeCycleState.TERMINATING,
    }:
        return ExecutionStatus.RUNNING

    if life_cycle_state == RunLifeCycleState.WAITING_FOR_RETRY:
        return ExecutionStatus.RUNNING

    if life_cycle_state in {
        RunLifeCycleState.INTERNAL_ERROR,
        RunLifeCycleState.SKIPPED,
    }:
        return ExecutionStatus.FAILED

    if life_cycle_state != RunLifeCycleState.TERMINATED:
        return ExecutionStatus.FAILED

    result_state = state.result_state
    if result_state in {
        RunResultState.SUCCESS,
        RunResultState.SUCCESS_WITH_FAILURES,
    }:
        return ExecutionStatus.COMPLETED

    if result_state in {
        RunResultState.CANCELED,
        RunResultState.UPSTREAM_CANCELED,
    }:
        return ExecutionStatus.STOPPED

    return ExecutionStatus.FAILED


def sanitize_labels(labels: Dict[str, str]) -> None:
    """Update the label values to be valid databricks labels.

    See:
    https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/#syntax-and-character-set

    Args:
        labels: the labels to sanitize.
    """
    for key, value in labels.items():
        # databricks labels must be alphanumeric, no longer than
        # 63 characters, and must begin and end with an alphanumeric
        # character ([a-z0-9A-Z])
        labels[key] = re.sub(r"[^0-9a-zA-Z-_\.]+", "_", value)[:63].strip(
            "-_."
        )
