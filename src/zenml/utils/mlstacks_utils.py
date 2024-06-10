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

import json
import os
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)
from uuid import UUID

import click

from zenml.client import Client
from zenml.constants import (
    MLSTACKS_SUPPORTED_STACK_COMPONENTS,
)
from zenml.enums import StackComponentType
from zenml.utils.dashboard_utils import get_component_url, get_stack_url
from zenml.utils.yaml_utils import read_yaml

if TYPE_CHECKING:
    from mlstacks.models import Component, Stack


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


def get_stack_spec_file_path(stack_name: str) -> str:
    """Gets the path to the stack spec file for the given stack name.

    Args:
        stack_name: The name of the stack spec to get the path for.

    Returns:
        The path to the stack spec file for the given stack name.

    Raises:
        KeyError: If the stack does not exist.
    """
    try:
        stack = Client().get_stack(
            name_id_or_prefix=stack_name, allow_name_prefix_match=False
        )
    except KeyError as e:
        raise e
    return stack.stack_spec_path or ""


def stack_spec_exists(stack_name: str) -> bool:
    """Checks whether a stack spec with that name exists or not.

    Args:
        stack_name: The name of the stack spec to check for.

    Returns:
        A boolean indicating whether the stack spec exists or not.
    """
    from zenml.cli.utils import verify_mlstacks_prerequisites_installation

    verify_mlstacks_prerequisites_installation()
    from mlstacks.constants import MLSTACKS_PACKAGE_NAME

    spec_dir = os.path.join(
        click.get_app_dir(MLSTACKS_PACKAGE_NAME), "stack_specs", stack_name
    )
    return Path(spec_dir).exists()


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
    if key in {"artifact_store"} and bool(value):
        if provider == "aws":
            flavor = "s3"
        elif provider == "azure":
            flavor = "azure"
        elif provider == "gcp":
            flavor = "gcp"
        elif provider == "k3d":
            flavor = "minio"
    elif key in {"container_registry"} and bool(value):
        if provider == "aws":
            flavor = "aws"
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
        and isinstance(value, str)
    ):
        flavor = value
    return flavor


def _add_extra_config_to_components(
    components: List["Component"], extra_config: Dict[str, str]
) -> List["Component"]:
    """Adds extra config to mlstacks `Component` objects.

    Args:
        components: A list of mlstacks `Component` objects.
        extra_config: A dictionary of extra config.

    Returns:
        A list of mlstacks `Component` objects.

    Raises:
        KeyError: If the component type is not supported.
    """
    from zenml.cli.utils import verify_mlstacks_prerequisites_installation

    verify_mlstacks_prerequisites_installation()
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

    # Define a list of component attributes that need checking
    component_attributes = ["component_type", "component_flavor", "provider"]

    for component in components:
        component_metadata = ComponentMetadata()
        component_metadata.config = {}

        # Create a dictionary that maps attribute names to their values
        component_values = {
            attr: getattr(component, attr, None)
            for attr in component_attributes
        }

        for config_keys, extra_keys in config_map.items():
            # If all attributes in config_keys match their values in the component
            if all(
                component_values.get(key) == value
                for key, value in zip(component_attributes, config_keys)
            ):
                _add_config(component_metadata, extra_keys)

        # always add project_id to gcp components
        if component.provider == "gcp":
            project_id = extra_config.get("project_id")
            if project_id:
                component_metadata.config["project_id"] = extra_config.get(
                    "project_id"
                )
            else:
                raise KeyError(
                    "No `project_id` is included. Please try again with "
                    "`--extra-config project_id=<project_id>`"
                )

        component.metadata = component_metadata

    return components


def _validate_extra_config(config: Tuple[str]) -> bool:
    """Validates that extra config values are correct.

    Args:
        config: A tuple of extra config values.

    Returns:
        A boolean indicating whether the extra config values are correct.
    """
    return all(item.count("=") <= 1 for item in config)


def _construct_components(
    params: Dict[str, Any], zenml_component_deploy: bool = False
) -> List["Component"]:
    """Constructs mlstacks `Component` objects from raw Click CLI params.

    Args:
        params: Raw Click CLI params.
        zenml_component_deploy: A boolean indicating whether the stack
            contains a single component and is being deployed through `zenml
            component deploy`

    Returns:
        A list of mlstacks `Component` objects.

    Raises:
        ValueError: If one of the extra_config values is invalid.
    """
    from zenml.cli.utils import verify_mlstacks_prerequisites_installation

    verify_mlstacks_prerequisites_installation()
    from mlstacks.models import Component

    provider = params["provider"]
    if not params.get("extra_config"):
        params["extra_config"] = ()
    if not _validate_extra_config(params["extra_config"]):
        raise ValueError(
            "One of the `extra_config` values is invalid. You passed in "
            f"{params['extra_config']}) in which one of the values includes "
            "multiple '=' signs. Please fix and try again."
        )
    extra_config = (
        dict(config.split("=") for config in params["extra_config"])
        if params.get("extra_config")
        else {}
    )
    if zenml_component_deploy:
        components = [
            Component(
                name=params[key],
                component_type=key,
                component_flavor=_get_component_flavor(key, value, provider),
                provider=params["provider"],
            )
            for key, value in params.items()
            if (value) and (key in MLSTACKS_SUPPORTED_STACK_COMPONENTS)
        ]
    else:
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


def _get_stack_tags(tags: Dict[str, str]) -> Dict[str, str]:
    """Gets and parses tags from Click params.

    Args:
        tags: Raw Click CLI params.

    Returns:
        A dictionary of tags.
    """
    return dict(tag.split("=") for tag in tags) if tags else {}


def _construct_base_stack(params: Dict[str, Any]) -> "Stack":
    """Constructs mlstacks `Stack` object from raw Click CLI params.

    Components are added to the `Stack` object subsequently.

    Args:
        params: Raw Click CLI params.

    Returns:
        A mlstacks `Stack` object.
    """
    from zenml.cli.utils import verify_mlstacks_prerequisites_installation

    verify_mlstacks_prerequisites_installation()
    from mlstacks.models import Stack

    tags = _get_stack_tags(params["tags"])

    return Stack(
        spec_version=1,
        spec_type="stack",
        name=params["stack_name"],
        provider=params["provider"],
        default_region=params["region"],
        default_tags=tags,
        components=[],
    )


def convert_click_params_to_mlstacks_primitives(
    params: Dict[str, Any],
    zenml_component_deploy: bool = False,
) -> Tuple["Stack", List["Component"]]:
    """Converts raw Click CLI params to mlstacks primitives.

    Args:
        params: Raw Click CLI params.
        zenml_component_deploy: A boolean indicating whether the stack
            contains a single component and is being deployed through `zenml
            component deploy`

    Returns:
        A tuple of Stack and List[Component] objects.
    """
    from zenml.cli.utils import verify_mlstacks_prerequisites_installation

    verify_mlstacks_prerequisites_installation()
    from mlstacks.constants import MLSTACKS_PACKAGE_NAME
    from mlstacks.models import Component, Stack

    stack: Stack = _construct_base_stack(params)
    components: List[Component] = _construct_components(
        params, zenml_component_deploy
    )

    # writes the file names to the stack spec
    # using format '<provider>-<component_name>.yaml'
    for component in components:
        stack.components.append(
            os.path.join(
                click.get_app_dir(MLSTACKS_PACKAGE_NAME),
                "stack_specs",
                stack.name,
                f"{component.name}.yaml",
            )
        )

    return stack, components


def convert_mlstacks_primitives_to_dicts(
    stack: "Stack", components: List["Component"]
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Converts mlstacks Stack and Components to dicts.

    Args:
        stack: A mlstacks Stack object.
        components: A list of mlstacks Component objects.

    Returns:
        A tuple of Stack and List[Component] dicts.
    """
    from zenml.cli.utils import verify_mlstacks_prerequisites_installation

    verify_mlstacks_prerequisites_installation()

    # convert to json first to strip out Enums objects
    stack_dict = json.loads(stack.model_dump_json())
    components_dicts = [
        json.loads(component.model_dump_json()) for component in components
    ]

    return stack_dict, components_dicts


def _setup_import(
    provider: str,
    stack_name: str,
    stack_spec_dir: str,
    user_stack_spec_file: Optional[str] = None,
) -> Tuple[Dict[str, Any], str]:
    """Sets up the environment for importing a new stack or component.

    Args:
        provider: The cloud provider for which the stack or component
            is deployed.
        stack_name: The name of the stack to import.
        stack_spec_dir: The path to the directory containing the stack spec.
        user_stack_spec_file: The path to the user-created stack spec file.

    Returns:
        A tuple containing the parsed YAML data and the stack spec file path.
    """
    from zenml.cli.utils import verify_mlstacks_prerequisites_installation

    verify_mlstacks_prerequisites_installation()

    from mlstacks.constants import MLSTACKS_PACKAGE_NAME
    from mlstacks.utils import terraform_utils

    tf_dir = os.path.join(
        click.get_app_dir(MLSTACKS_PACKAGE_NAME),
        "terraform",
        f"{provider}-modular",
    )
    stack_spec_file = user_stack_spec_file or os.path.join(
        stack_spec_dir, f"stack-{stack_name}.yaml"
    )
    stack_filename = terraform_utils.get_stack_outputs(
        stack_spec_file, output_key="stack-yaml-path"
    ).get("stack-yaml-path")[2:]
    import_stack_path = os.path.join(tf_dir, stack_filename)
    data = read_yaml(import_stack_path)

    return data, stack_spec_file


def _import_components(
    data: Dict[str, Any],
    stack_spec_dir: str,
    component_name: Optional[str] = None,
) -> Dict[StackComponentType, UUID]:
    """Imports components based on the provided data.

    Args:
        data: The parsed YAML data containing component details.
        stack_spec_dir: The path to the directory containing the stack spec.
        component_name: The name of the component to import (if any).

    Returns:
        A dictionary mapping component types to their respective IDs.
    """
    component_ids = {}
    for component_type_str, component_config in data["components"].items():
        component_type = StackComponentType(component_type_str)
        component_spec_path = os.path.join(
            stack_spec_dir,
            f"{component_name or component_config['flavor']}-{component_type_str}.yaml",
        )
        if component_name:
            component_config["name"] = component_name

        from zenml.cli.stack import _import_stack_component

        component_id = _import_stack_component(
            component_type=component_type,
            component_dict=component_config,
            component_spec_path=component_spec_path,
        )
        component_ids[component_type] = component_id

    return component_ids


def import_new_mlstacks_stack(
    stack_name: str,
    provider: str,
    stack_spec_dir: str,
    user_stack_spec_file: Optional[str] = None,
) -> None:
    """Import a new stack deployed for a particular cloud provider.

    Args:
        stack_name: The name of the stack to import.
        provider: The cloud provider for which the stack is deployed.
        stack_spec_dir: The path to the directory containing the stack spec.
        user_stack_spec_file: The path to the user-created stack spec file.
    """
    data, stack_spec_file = _setup_import(
        provider, stack_name, stack_spec_dir, user_stack_spec_file
    )
    component_ids = _import_components(
        data=data, stack_spec_dir=stack_spec_dir
    )

    imported_stack = Client().create_stack(
        name=stack_name,
        components=component_ids,
        stack_spec_file=stack_spec_file,
    )

    from zenml.cli.utils import print_model_url

    print_model_url(get_stack_url(imported_stack))


def import_new_mlstacks_component(
    stack_name: str, component_name: str, provider: str, stack_spec_dir: str
) -> None:
    """Import a new component deployed for a particular cloud provider.

    Args:
        stack_name: The name of the stack to import.
        component_name: The name of the component to import.
        provider: The cloud provider for which the stack is deployed.
        stack_spec_dir: The path to the directory containing the stack spec.
    """
    data, _ = _setup_import(provider, stack_name, stack_spec_dir)
    component_ids = _import_components(
        data, stack_spec_dir, component_name=component_name
    )
    component_type = list(component_ids.keys())[
        0
    ]  # Assuming only one component is imported
    component = Client().get_stack_component(
        component_type, component_ids[component_type]
    )

    from zenml.cli.utils import print_model_url

    print_model_url(get_component_url(component))


def verify_spec_and_tf_files_exist(
    spec_file_path: str, tf_file_path: str
) -> None:
    """Checks whether both the spec and tf files exist.

    Args:
        spec_file_path: The path to the spec file.
        tf_file_path: The path to the tf file.
    """
    from zenml.cli.utils import error

    if not Path(spec_file_path).exists():
        error(f"Could not find the Stack spec file at {spec_file_path}.")
    elif not Path(tf_file_path).exists():
        error(
            f"Could not find the Terraform files for the stack "
            f"at {tf_file_path}."
        )


def deploy_mlstacks_stack(
    spec_file_path: str,
    stack_name: str,
    stack_provider: str,
    debug_mode: bool = False,
    no_import_stack_flag: bool = False,
    user_created_spec: bool = False,
) -> None:
    """Deploys an MLStacks stack given a spec file path.

    Args:
        spec_file_path: The path to the spec file.
        stack_name: The name of the stack.
        stack_provider: The cloud provider for which the stack is deployed.
        debug_mode: A boolean indicating whether to run in debug mode.
        no_import_stack_flag: A boolean indicating whether to import the stack
            into ZenML.
        user_created_spec: A boolean indicating whether the user created the
            spec file.
    """
    from zenml.cli.utils import (
        declare,
        verify_mlstacks_prerequisites_installation,
    )

    verify_mlstacks_prerequisites_installation()
    from mlstacks.constants import MLSTACKS_PACKAGE_NAME
    from mlstacks.utils import terraform_utils

    spec_dir = os.path.join(
        click.get_app_dir(MLSTACKS_PACKAGE_NAME), "stack_specs", stack_name
    )
    declare("Deploying stack using Terraform...")
    terraform_utils.deploy_stack(spec_file_path, debug_mode=debug_mode)
    declare("Stack successfully deployed.")

    if not no_import_stack_flag:
        declare(f"Importing stack '{stack_name}' into ZenML...")
        import_new_mlstacks_stack(
            stack_name=stack_name,
            provider=stack_provider,
            stack_spec_dir=spec_dir,
            user_stack_spec_file=spec_file_path if user_created_spec else None,
        )
        declare("Stack successfully imported into ZenML.")
