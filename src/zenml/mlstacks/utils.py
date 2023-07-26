#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.

#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:

#       https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Functionality to handle interaction with the mlstacks package."""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

import pkg_resources

from zenml.cli import utils as cli_utils
from zenml.client import Client
from zenml.constants import (
    MLSTACKS_SUPPORTED_STACK_COMPONENTS,
    NOT_INSTALLED_MESSAGE,
    STACK_RECIPE_PACKAGE_NAME,
)


def stack_exists(stack_name: str) -> bool:
    """Checks whether a stack with that name exists or not.

    Args:
        stack_name: The name of the stack to check for.

    Returns:
        A boolean indicating whether the stack exists or not.
    """
    try:
        Client().get_stack(
            name_id_or_prefix=stack_name, allow_name_prefix_match=False
        )
    except KeyError:
        return False
    return True


def verify_mlstacks_installation() -> None:
    """Checks if the `mlstacks` package is installed."""
    try:
        import mlstacks  # noqa: F401
    except ImportError:
        cli_utils.error(NOT_INSTALLED_MESSAGE)


def get_mlstacks_version() -> Optional[str]:
    """Gets the version of mlstacks locally installed.

    Raises:
        pkg_resources.DistributionNotFound: If mlstacks is not installed.
    """
    try:
        return pkg_resources.get_distribution(
            STACK_RECIPE_PACKAGE_NAME
        ).version
    except pkg_resources.DistributionNotFound:
        return


def _get_component_flavor(
    key: str, value: Union[bool, str], provider: str
) -> str:
    """Constructs the component flavor from Click CLI params.

    Args:
        key: The component key.
        value: The component value.
        provider: The provider name.

    Returns:
        The component flavor.
    """
    if key in {"artifact_store", "container_registry"} and value is True:
        if provider == "aws":
            flavor = "s3"
        elif provider == "azure":
            flavor = "azure"
        elif provider == "gcp":
            flavor = "gcp"
    elif (
        key
        in {
            "experiment_tracker",
            "orchestrator",
            "model_deployer",
            "model_registry",
            "mlops_platform",
            "step_operator",
        }
        and value
        and type(value) == str
    ):
        flavor = value
    return flavor


# def _add_extra_config_to_components(
#     components: List["Component"], extra_config: Dict[str, str]
# ) -> List["Component"]:
#     """Adds extra config to mlstacks `Component` objects.

#     Args:
#         components: A list of mlstacks `Component` objects.
#         extra_config: A dictionary of extra config.

#     Returns:
#         A list of mlstacks `Component` objects.
#     """
#     verify_mlstacks_installation()
#     from mlstacks.models.component import ComponentMetadata

#     for component in components:
#         component_metadata = ComponentMetadata()
#         if component.component_type == "container_registry":
#             if extra_config.get("repo_name"):
#                 component_metadata.config["repo_name"] = extra_config.get(
#                     "repo_name"
#                 )
#         elif component.component_type == "artifact_store":
#             if extra_config.get("bucket_name"):
#                 component_metadata.config["bucket_name"] = extra_config.get(
#                     "bucket_name"
#                 )
#         elif (
#             component.component_type == "experiment_tracker"
#             and component.component_flavor == "mlflow"
#         ):
#             if extra_config.get("mlflow-artifact-S3-access-key"):
#                 component_metadata.config[
#                     "mlflow-artifact-S3-access-key"
#                 ] = extra_config.get("mlflow-artifact-S3-access-key")
#             if extra_config.get("mlflow-artifact-S3-secret-key"):
#                 component_metadata.config[
#                     "mlflow-artifact-S3-secret-key"
#                 ] = extra_config.get("mlflow-artifact-S3-secret-key")
#             if extra_config.get("mlflow-username"):
#                 component_metadata.config[
#                     "mlflow-username"
#                 ] = extra_config.get("mlflow-username")
#             if extra_config.get("mlflow-password"):
#                 component_metadata.config[
#                     "mlflow-password"
#                 ] = extra_config.get("mlflow-password")
#             if extra_config.get("mlflow_bucket"):
#                 component_metadata.config["mlflow_bucket"] = extra_config.get(
#                     "mlflow_bucket"
#                 )
#         elif (
#             component.component_type == "mlops_platform"
#             and component.component_flavor == "zenml"
#         ):
#             if extra_config.get("zenml-version"):
#                 component_metadata.config["zenml-version"] = extra_config.get(
#                     "zenml-version"
#                 )
#             if extra_config.get("zenml-username"):
#                 component_metadata.config["zenml-username"] = extra_config.get(
#                     "zenml-username"
#                 )
#             if extra_config.get("zenml-password"):
#                 component_metadata.config["zenml-password"] = extra_config.get(
#                     "zenml-password"
#                 )
#             if extra_config.get("zenml-database-url"):
#                 component_metadata.config[
#                     "zenml-database-url"
#                 ] = extra_config.get("zenml-database-url")
#         elif (
#             component.provider == "k3d"
#             and component.component_type == "artifact_store"
#             and component.component_flavor == "minio"
#         ):
#             if extra_config.get("zenml-minio-store-access-key"):
#                 component_metadata.config[
#                     "zenml-minio-store-access-key"
#                 ] = extra_config.get("zenml-minio-store-access-key")
#             if extra_config.get("zenml-minio-store-secret-key"):
#                 component_metadata.config[
#                     "zenml-minio-store-secret-key"
#                 ] = extra_config.get("zenml-minio-store-secret-key")
#         elif (
#             component.provider == "k3d"
#             and component.component_type == "experiment_tracker"
#             and component.component_flavor == "mlflow"
#         ):
#             if extra_config.get("mlflow_minio_bucket"):
#                 component_metadata.config[
#                     "mlflow_minio_bucket"
#                 ] = extra_config.get("mlflow_minio_bucket")
#             if extra_config.get("mlflow-username"):
#                 component_metadata.config[
#                     "mlflow-username"
#                 ] = extra_config.get("mlflow-username")
#             if extra_config.get("mlflow-password"):
#                 component_metadata.config[
#                     "mlflow-password"
#                 ] = extra_config.get("mlflow-password")
#         elif (
#             component.provider == "k3d"
#             and component.component_type == "model_deployer"
#             and component.component_flavor == "seldon"
#         ):
#             if extra_config.get("seldon-secret-name"):
#                 component_metadata.config[
#                     "seldon-secret-name"
#                 ] = extra_config.get("seldon-secret-name")
#         elif (
#             component.provider == "k3d"
#             and component.component_type == "model_deployer"
#             and component.component_flavor == "kserve"
#         ):
#             if extra_config.get("kserve-secret-name"):
#                 component_metadata.config[
#                     "kserve-secret-name"
#                 ] = extra_config.get("kserve-secret-name")
#         component.metadata = component_metadata
#     return components


def _add_extra_config_to_components(
    components: List["Component"], extra_config: Dict[str, str]
) -> List["Component"]:
    """Adds extra config to mlstacks `Component` objects.

    Args:
        components: A list of mlstacks `Component` objects.
        extra_config: A dictionary of extra config.

    Returns:
        A list of mlstacks `Component` objects.
    """
    verify_mlstacks_installation()
    from mlstacks.models.component import ComponentMetadata

    # Define configuration map
    config_map = {
        ("container_registry",): ["repo_name"],
        ("artifact_store",): ["bucket_name"],
        ("experiment_tracker", "mlflow"): [
            "mlflow-artifact-S3-access-key",
            "mlflow-artifact-S3-secret-key",
            "mlflow-username",
            "mlflow-password",
            "mlflow_bucket",
        ],
        ("mlops_platform", "zenml"): [
            "zenml-version",
            "zenml-username",
            "zenml-password",
            "zenml-database-url",
        ],
        ("artifact_store", "minio", "k3d"): [
            "zenml-minio-store-access-key",
            "zenml-minio-store-secret-key",
        ],
        ("experiment_tracker", "mlflow", "k3d"): [
            "mlflow_minio_bucket",
            "mlflow-username",
            "mlflow-password",
        ],
        ("model_deployer", "seldon", "k3d"): ["seldon-secret-name"],
        ("model_deployer", "kserve", "k3d"): ["kserve-secret-name"],
    }

    def _add_config(
        component_metadata: ComponentMetadata, keys: List[str]
    ) -> None:
        """Adds key-value pair to the component_metadata config if it exists in extra_config.

        Args:
            component_metadata: The metadata of the component.
            keys: The keys of the configurations.
        """
        for key in keys:
            value = extra_config.get(key)
            if value is not None:
                component_metadata.config[key] = value

    # Process each component
    for component in components:
        component_metadata = ComponentMetadata()
        for config_keys, extra_keys in config_map.items():
            if all(
                getattr(component, config_key, None) == config_key
                for config_key in config_keys
            ):
                _add_config(component_metadata, extra_keys)
        component.metadata = component_metadata

        # always add project_id to gcp components
        if component.provider == "gcp":
            project_id = extra_config.get("project_id")
            if project_id:
                component.metadata.config["project_id"] = extra_config.get(
                    "project_id"
                )
            else:
                raise KeyError(
                    "No `project_id` is included. Please try again with "
                    "`--extra-config project_id=<project_id>`"
                )
    return components


def _construct_components(params: Dict[str, Any]) -> List["Component"]:
    """Constructs mlstacks `Component` objects from raw Click CLI params.

    Args:
        params: Raw Click CLI params.

    Returns:
        A list of mlstacks `Component` objects.
    """
    verify_mlstacks_installation()
    from mlstacks.models import Component

    provider = params["provider"]
    extra_config = (
        dict(config.split("=") for config in params["extra_config"])
        if params["extra_config"]
        else {}
    )

    components = [
        Component(
            name=f"{provider}-{key}",
            component_type=key,
            component_flavor=_get_component_flavor(key, value, provider),
            provider=params["provider"],
        )
        for key, value in params.items()
        if (value) and (key in MLSTACKS_SUPPORTED_STACK_COMPONENTS)
    ]

    components = _add_extra_config_to_components(components, extra_config)
    return components


def _get_tags(tags: Dict[str, str]) -> Dict[str, str]:
    """Gets and parses tags from Click params.

    Args:
        tags: Raw Click CLI params.

    Returns:
        A dictionary of tags.
    """
    return dict(tag.split("=") for tag in tags) if tags else {}


def _construct_stack(params: Dict[str, Any]) -> "Stack":
    """Constructs mlstacks `Stack` object from raw Click CLI params.

    Args:
        params: Raw Click CLI params.

    Returns:
        A mlstacks `Stack` object.
    """
    verify_mlstacks_installation()
    from mlstacks.models import Stack

    tags = _get_tags(params["tags"])

    return Stack(
        spec_version=1,
        spec_type="stack",
        name=params["name"],
        provider=params["provider"],
        default_region=params["region"],
        default_tags=tags,
        components=[],
    )


def convert_click_params_to_mlstacks_primitives(
    params: Dict[str, Any]
) -> Tuple["Stack", List["Component"]]:
    """Converts raw Click CLI params to mlstacks primitives.

    Args:
        params: Raw Click CLI params.

    Returns:
        A tuple of Stack and List[Component] objects.
    """
    verify_mlstacks_installation()
    from mlstacks.models import Component, Stack

    stack: Stack = _construct_stack(params)
    components: List[Component] = _construct_components(params)

    # writes the file names to the stack spec
    # using format '<provider>-<component_name>.yaml'
    for component in components:
        stack.components.append(f"{stack.provider}-{component.name}.yaml")

    return stack, components
