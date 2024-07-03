#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""CLI for manipulating ZenML local and global config file."""

import getpass
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Union
from uuid import UUID

import click
from rich.console import Console
from rich.prompt import Confirm
from rich.syntax import Syntax

import zenml
from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.utils import (
    _component_display_name,
    confirmation,
    declare,
    error,
    is_sorted_or_filtered,
    list_options,
    print_model_url,
    print_page_info,
    print_stacks_table,
    verify_mlstacks_prerequisites_installation,
)
from zenml.client import Client
from zenml.console import console
from zenml.constants import (
    ALPHA_MESSAGE,
    MLSTACKS_SUPPORTED_STACK_COMPONENTS,
    STACK_RECIPE_MODULAR_RECIPES,
)
from zenml.enums import CliCategories, StackComponentType
from zenml.exceptions import (
    IllegalOperationError,
    ProvisioningError,
)
from zenml.io.fileio import rmtree
from zenml.logger import get_logger
from zenml.models import StackFilter
from zenml.models.v2.core.service_connector import (
    ServiceConnectorRequest,
    ServiceConnectorResponse,
)
from zenml.models.v2.misc.full_stack import (
    ComponentInfo,
    FullStackRequest,
    ServiceConnectorInfo,
)
from zenml.models.v2.misc.service_connector_type import (
    ServiceConnectorTypedResourcesModel,
)
from zenml.utils.dashboard_utils import get_stack_url
from zenml.utils.io_utils import create_dir_recursive_if_not_exists
from zenml.utils.mlstacks_utils import (
    convert_click_params_to_mlstacks_primitives,
    convert_mlstacks_primitives_to_dicts,
    deploy_mlstacks_stack,
    get_stack_spec_file_path,
    stack_exists,
    stack_spec_exists,
    verify_spec_and_tf_files_exist,
)
from zenml.utils.yaml_utils import read_yaml, write_yaml

if TYPE_CHECKING:
    from zenml.models import StackResponse

logger = get_logger(__name__)


# Stacks
@cli.group(
    cls=TagGroup,
    tag=CliCategories.MANAGEMENT_TOOLS,
)
def stack() -> None:
    """Stacks to define various environments."""


@stack.command(
    "register",
    context_settings=dict(ignore_unknown_options=True),
    help="Register a stack with components.",
)
@click.argument("stack_name", type=str, required=True)
@click.option(
    "-a",
    "--artifact-store",
    "artifact_store",
    help="Name of the artifact store for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-o",
    "--orchestrator",
    "orchestrator",
    help="Name of the orchestrator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-c",
    "--container_registry",
    "container_registry",
    help="Name of the container registry for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-r",
    "--model_registry",
    "model_registry",
    help="Name of the model registry for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-s",
    "--step_operator",
    "step_operator",
    help="Name of the step operator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-f",
    "--feature_store",
    "feature_store",
    help="Name of the feature store for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-d",
    "--model_deployer",
    "model_deployer",
    help="Name of the model deployer for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-e",
    "--experiment_tracker",
    "experiment_tracker",
    help="Name of the experiment tracker for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-al",
    "--alerter",
    "alerter",
    help="Name of the alerter for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-an",
    "--annotator",
    "annotator",
    help="Name of the annotator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-dv",
    "--data_validator",
    "data_validator",
    help="Name of the data validator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-i",
    "--image_builder",
    "image_builder",
    help="Name of the image builder for this stack.",
    type=str,
    required=False,
)
@click.option(
    "--set",
    "set_stack",
    is_flag=True,
    help="Immediately set this stack as active.",
    type=click.BOOL,
)
@click.option(
    "-p",
    "--provider",
    help="Name of the cloud provider for this stack.",
    type=click.Choice(["aws", "azure", "gcp"]),
    required=False,
)
@click.option(
    "-sc",
    "--connector",
    help="Name of the service connector for this stack.",
    type=str,
    required=False,
)
def register_stack(
    stack_name: str,
    artifact_store: Optional[str] = None,
    orchestrator: Optional[str] = None,
    container_registry: Optional[str] = None,
    model_registry: Optional[str] = None,
    step_operator: Optional[str] = None,
    feature_store: Optional[str] = None,
    model_deployer: Optional[str] = None,
    experiment_tracker: Optional[str] = None,
    alerter: Optional[str] = None,
    annotator: Optional[str] = None,
    data_validator: Optional[str] = None,
    image_builder: Optional[str] = None,
    set_stack: bool = False,
    provider: Optional[str] = None,
    connector: Optional[str] = None,
) -> None:
    """Register a stack.

    Args:
        stack_name: Unique name of the stack
        artifact_store: Name of the artifact store for this stack.
        orchestrator: Name of the orchestrator for this stack.
        container_registry: Name of the container registry for this stack.
        model_registry: Name of the model registry for this stack.
        step_operator: Name of the step operator for this stack.
        feature_store: Name of the feature store for this stack.
        model_deployer: Name of the model deployer for this stack.
        experiment_tracker: Name of the experiment tracker for this stack.
        alerter: Name of the alerter for this stack.
        annotator: Name of the annotator for this stack.
        data_validator: Name of the data validator for this stack.
        image_builder: Name of the new image builder for this stack.
        set_stack: Immediately set this stack as active.
        provider: Name of the cloud provider for this stack.
        connector: Name of the service connector for this stack.
    """
    if (provider is None and connector is None) and (
        artifact_store is None or orchestrator is None
    ):
        cli_utils.error(
            "Only stack using service connector can be registered "
            "without specifying an artifact store and an orchestrator. "
            "Please specify the artifact store and the orchestrator or "
            "the service connector or cloud type settings."
        )

    client = Client()

    try:
        client.get_stack(
            name_id_or_prefix=stack_name,
            allow_name_prefix_match=False,
        )
        cli_utils.error(
            f"A stack with name `{stack_name}` already exists, "
            "please use a different name."
        )
    except KeyError:
        pass

    components: Dict[StackComponentType, Union[UUID, ComponentInfo]] = {}
    # cloud flow
    created_objects: Set[str] = set()
    service_connector: Optional[Union[UUID, ServiceConnectorInfo]] = None
    if provider is not None and connector is None:
        service_connector_response = None
        use_auto_configure = False
        try:
            service_connector_response, _ = client.create_service_connector(
                name=stack_name,
                connector_type=provider,
                register=False,
                auto_configure=True,
                verify=False,
            )
        except Exception:
            pass
        if service_connector_response:
            use_auto_configure = Confirm.ask(
                f"[bold]{provider.upper()} cloud service connector[/bold] "
                "has detected connection credentials in your environment.\n"
                "Would you like to use these credentials or create a new "
                "configuration by providing connection details?",
                default=True,
                show_choices=True,
                show_default=True,
            )

        connector_selected: Optional[int] = None
        if not use_auto_configure:
            service_connector_response = None
            existing_connectors = client.list_service_connectors(
                connector_type=provider, size=100
            )
            if existing_connectors.total:
                connector_selected = cli_utils.multi_choice_prompt(
                    object_type=f"{provider.upper()} service connectors",
                    choices=[
                        [connector.name]
                        for connector in existing_connectors.items
                    ],
                    headers=["Name"],
                    prompt_text=f"We found these {provider.upper()} service connectors. "
                    "Do you want to create a new one or use one of the existing ones?",
                    default_choice="0",
                    allow_zero_be_a_new_object=True,
                )
        if use_auto_configure or connector_selected is None:
            service_connector = _get_service_connector_info(
                cloud_provider=provider,
                connector_details=service_connector_response,
            )
            created_objects.add("service_connector")
        else:
            selected_connector = existing_connectors.items[connector_selected]
            service_connector = selected_connector.id
            connector = selected_connector.name
            if isinstance(selected_connector.connector_type, str):
                provider = selected_connector.connector_type
            else:
                provider = selected_connector.connector_type.connector_type
    elif connector is not None:
        service_connector_response = client.get_service_connector(connector)
        service_connector = service_connector_response.id
        if provider:
            if service_connector_response.type != provider:
                cli_utils.warning(
                    f"The service connector `{connector}` is not of type `{provider}`."
                )
        else:
            provider = service_connector_response.type

    if service_connector:
        service_connector_resource_model = None
        # create components
        needed_components = (
            (StackComponentType.ARTIFACT_STORE, artifact_store),
            (StackComponentType.ORCHESTRATOR, orchestrator),
            (StackComponentType.CONTAINER_REGISTRY, container_registry),
        )
        for component_type, preset_name in needed_components:
            component_info: Optional[Union[UUID, ComponentInfo]] = None
            if preset_name is not None:
                component_response = client.get_stack_component(
                    component_type, preset_name
                )
                component_info = component_response.id
            else:
                if isinstance(service_connector, UUID):
                    # find existing components under same connector
                    existing_components = client.list_stack_components(
                        type=component_type.value,
                        connector_id=service_connector,
                        size=100,
                    )
                    # if some existing components are found - prompt user what to do
                    component_selected: Optional[int] = None
                    if existing_components.total > 0:
                        component_selected = cli_utils.multi_choice_prompt(
                            object_type=component_type.value.replace("_", " "),
                            choices=[
                                [component.name]
                                for component in existing_components.items
                            ],
                            headers=["Name"],
                            prompt_text=f"We found these {component_type.value.replace('_', ' ')} "
                            "connected using the current service connector. Do you "
                            "want to create a new one or use existing one?",
                            default_choice="0",
                            allow_zero_be_a_new_object=True,
                        )
                else:
                    component_selected = None

                if component_selected is None:
                    if service_connector_resource_model is None:
                        if isinstance(service_connector, UUID):
                            service_connector_resource_model = (
                                client.verify_service_connector(
                                    service_connector
                                )
                            )
                        else:
                            _, service_connector_resource_model = (
                                client.create_service_connector(
                                    name=stack_name,
                                    connector_type=service_connector.type,
                                    auth_method=service_connector.auth_method,
                                    configuration=service_connector.configuration,
                                    register=False,
                                )
                            )
                            if service_connector_resource_model is None:
                                cli_utils.error(
                                    f"Failed to validate service connector {service_connector}..."
                                )
                    if provider is None:
                        if isinstance(
                            service_connector_resource_model.connector_type,
                            str,
                        ):
                            provider = (
                                service_connector_resource_model.connector_type
                            )
                        else:
                            provider = service_connector_resource_model.connector_type.connector_type

                    component_info = _get_stack_component_info(
                        component_type=component_type.value,
                        cloud_provider=provider,
                        service_connector_resource_models=service_connector_resource_model.resources,
                        service_connector_index=0,
                    )
                    component_name = stack_name
                    created_objects.add(component_type.value)
                else:
                    selected_component = existing_components.items[
                        component_selected
                    ]
                    component_info = selected_component.id
                    component_name = selected_component.name

            components[component_type] = component_info
            if component_type == StackComponentType.ARTIFACT_STORE:
                artifact_store = component_name
            if component_type == StackComponentType.ORCHESTRATOR:
                orchestrator = component_name
            if component_type == StackComponentType.CONTAINER_REGISTRY:
                container_registry = component_name

    # normal flow once all components are defined
    with console.status(f"Registering stack '{stack_name}'...\n"):
        for component_type_, component_name_ in [
            (StackComponentType.ARTIFACT_STORE, artifact_store),
            (StackComponentType.ORCHESTRATOR, orchestrator),
            (StackComponentType.ALERTER, alerter),
            (StackComponentType.ANNOTATOR, annotator),
            (StackComponentType.DATA_VALIDATOR, data_validator),
            (StackComponentType.FEATURE_STORE, feature_store),
            (StackComponentType.IMAGE_BUILDER, image_builder),
            (StackComponentType.MODEL_DEPLOYER, model_deployer),
            (StackComponentType.MODEL_REGISTRY, model_registry),
            (StackComponentType.STEP_OPERATOR, step_operator),
            (StackComponentType.EXPERIMENT_TRACKER, experiment_tracker),
            (StackComponentType.CONTAINER_REGISTRY, container_registry),
        ]:
            if component_name_ and component_type_ not in components:
                components[component_type_] = client.get_stack_component(
                    component_type_, component_name_
                ).id

        try:
            created_stack = client.zen_store.create_full_stack(
                full_stack=FullStackRequest(
                    user=client.active_user.id,
                    workspace=client.active_workspace.id,
                    name=stack_name,
                    components=components,
                    service_connectors=[service_connector]
                    if service_connector
                    else [],
                )
            )
        except (KeyError, IllegalOperationError) as err:
            cli_utils.error(str(err))

        cli_utils.declare(
            f"Stack '{created_stack.name}' successfully registered!"
        )
        cli_utils.print_stack_configuration(
            stack=created_stack,
            active=created_stack.id == client.active_stack_model.id,
        )

    if set_stack:
        client.activate_stack(created_stack.id)

        scope = "repository" if client.uses_local_configuration else "global"
        cli_utils.declare(
            f"Active {scope} stack set to:'{created_stack.name}'"
        )

    delete_commands = []
    if "service_connector" in created_objects:
        created_objects.remove("service_connector")
        connectors = set()
        for each in created_objects:
            if comps_ := created_stack.components[StackComponentType(each)]:
                if conn_ := comps_[0].connector:
                    connectors.add(conn_.name)
        for connector in connectors:
            delete_commands.append(
                "zenml service-connector delete " + connector
            )
    for each in created_objects:
        if comps_ := created_stack.components[StackComponentType(each)]:
            delete_commands.append(
                f"zenml {each.replace('_', '-')} delete {comps_[0].name}"
            )
    delete_commands.append("zenml stack delete -y " + created_stack.name)

    Console().print(
        "To delete the objects created by this command run, please run in a sequence:\n"
    )
    Console().print(Syntax("\n".join(delete_commands[::-1]), "bash"))

    print_model_url(get_stack_url(created_stack))


@stack.command(
    "update",
    context_settings=dict(ignore_unknown_options=True),
    help="Update a stack with new components.",
)
@click.argument("stack_name_or_id", type=str, required=False)
@click.option(
    "-a",
    "--artifact-store",
    "artifact_store",
    help="Name of the new artifact store for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-o",
    "--orchestrator",
    "orchestrator",
    help="Name of the new orchestrator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-c",
    "--container_registry",
    "container_registry",
    help="Name of the new container registry for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-r",
    "--model_registry",
    "model_registry",
    help="Name of the model registry for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-s",
    "--step_operator",
    "step_operator",
    help="Name of the new step operator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-f",
    "--feature_store",
    "feature_store",
    help="Name of the new feature store for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-d",
    "--model_deployer",
    "model_deployer",
    help="Name of the new model deployer for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-e",
    "--experiment_tracker",
    "experiment_tracker",
    help="Name of the new experiment tracker for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-al",
    "--alerter",
    "alerter",
    help="Name of the new alerter for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-an",
    "--annotator",
    "annotator",
    help="Name of the new annotator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-dv",
    "--data_validator",
    "data_validator",
    help="Name of the data validator for this stack.",
    type=str,
    required=False,
)
@click.option(
    "-i",
    "--image_builder",
    "image_builder",
    help="Name of the image builder for this stack.",
    type=str,
    required=False,
)
def update_stack(
    stack_name_or_id: Optional[str] = None,
    artifact_store: Optional[str] = None,
    orchestrator: Optional[str] = None,
    container_registry: Optional[str] = None,
    step_operator: Optional[str] = None,
    feature_store: Optional[str] = None,
    model_deployer: Optional[str] = None,
    experiment_tracker: Optional[str] = None,
    alerter: Optional[str] = None,
    annotator: Optional[str] = None,
    data_validator: Optional[str] = None,
    image_builder: Optional[str] = None,
    model_registry: Optional[str] = None,
) -> None:
    """Update a stack.

    Args:
        stack_name_or_id: Name or id of the stack to update.
        artifact_store: Name of the new artifact store for this stack.
        orchestrator: Name of the new orchestrator for this stack.
        container_registry: Name of the new container registry for this stack.
        step_operator: Name of the new step operator for this stack.
        feature_store: Name of the new feature store for this stack.
        model_deployer: Name of the new model deployer for this stack.
        experiment_tracker: Name of the new experiment tracker for this
            stack.
        alerter: Name of the new alerter for this stack.
        annotator: Name of the new annotator for this stack.
        data_validator: Name of the new data validator for this stack.
        image_builder: Name of the new image builder for this stack.
        model_registry: Name of the new model registry for this stack.
    """
    client = Client()

    with console.status("Updating stack...\n"):
        updates: Dict[StackComponentType, List[Union[str, UUID]]] = dict()
        if artifact_store:
            updates[StackComponentType.ARTIFACT_STORE] = [artifact_store]
        if alerter:
            updates[StackComponentType.ALERTER] = [alerter]
        if annotator:
            updates[StackComponentType.ANNOTATOR] = [annotator]
        if container_registry:
            updates[StackComponentType.CONTAINER_REGISTRY] = [
                container_registry
            ]
        if data_validator:
            updates[StackComponentType.DATA_VALIDATOR] = [data_validator]
        if experiment_tracker:
            updates[StackComponentType.EXPERIMENT_TRACKER] = [
                experiment_tracker
            ]
        if feature_store:
            updates[StackComponentType.FEATURE_STORE] = [feature_store]
        if model_registry:
            updates[StackComponentType.MODEL_REGISTRY] = [model_registry]
        if image_builder:
            updates[StackComponentType.IMAGE_BUILDER] = [image_builder]
        if model_deployer:
            updates[StackComponentType.MODEL_DEPLOYER] = [model_deployer]
        if orchestrator:
            updates[StackComponentType.ORCHESTRATOR] = [orchestrator]
        if step_operator:
            updates[StackComponentType.STEP_OPERATOR] = [step_operator]

        try:
            updated_stack = client.update_stack(
                name_id_or_prefix=stack_name_or_id,
                component_updates=updates,
            )

        except (KeyError, IllegalOperationError) as err:
            cli_utils.error(str(err))

        cli_utils.declare(
            f"Stack `{updated_stack.name}` successfully updated!"
        )
    print_model_url(get_stack_url(updated_stack))


@stack.command(
    "remove-component",
    context_settings=dict(ignore_unknown_options=True),
    help="Remove stack components from a stack.",
)
@click.argument("stack_name_or_id", type=str, required=False)
@click.option(
    "-c",
    "--container_registry",
    "container_registry_flag",
    help="Include this to remove the container registry from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-s",
    "--step_operator",
    "step_operator_flag",
    help="Include this to remove the step operator from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-r",
    "--model_registry",
    "model_registry_flag",
    help="Include this to remove the model registry from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-f",
    "--feature_store",
    "feature_store_flag",
    help="Include this to remove the feature store from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-d",
    "--model_deployer",
    "model_deployer_flag",
    help="Include this to remove the model deployer from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-e",
    "--experiment_tracker",
    "experiment_tracker_flag",
    help="Include this to remove the experiment tracker from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-al",
    "--alerter",
    "alerter_flag",
    help="Include this to remove the alerter from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-an",
    "--annotator",
    "annotator_flag",
    help="Include this to remove the annotator from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-dv",
    "--data_validator",
    "data_validator_flag",
    help="Include this to remove the data validator from this stack.",
    is_flag=True,
    required=False,
)
@click.option(
    "-i",
    "--image_builder",
    "image_builder_flag",
    help="Include this to remove the image builder from this stack.",
    is_flag=True,
    required=False,
)
def remove_stack_component(
    stack_name_or_id: Optional[str] = None,
    container_registry_flag: Optional[bool] = False,
    step_operator_flag: Optional[bool] = False,
    feature_store_flag: Optional[bool] = False,
    model_deployer_flag: Optional[bool] = False,
    experiment_tracker_flag: Optional[bool] = False,
    alerter_flag: Optional[bool] = False,
    annotator_flag: Optional[bool] = False,
    data_validator_flag: Optional[bool] = False,
    image_builder_flag: Optional[bool] = False,
    model_registry_flag: Optional[str] = None,
) -> None:
    """Remove stack components from a stack.

    Args:
        stack_name_or_id: Name of the stack to remove components from.
        container_registry_flag: To remove the container registry from this
            stack.
        step_operator_flag: To remove the step operator from this stack.
        feature_store_flag: To remove the feature store from this stack.
        model_deployer_flag: To remove the model deployer from this stack.
        experiment_tracker_flag: To remove the experiment tracker from this
            stack.
        alerter_flag: To remove the alerter from this stack.
        annotator_flag: To remove the annotator from this stack.
        data_validator_flag: To remove the data validator from this stack.
        image_builder_flag: To remove the image builder from this stack.
        model_registry_flag: To remove the model registry from this stack.
    """
    client = Client()

    with console.status("Updating the stack...\n"):
        stack_component_update: Dict[StackComponentType, List[Any]] = dict()

        if container_registry_flag:
            stack_component_update[StackComponentType.CONTAINER_REGISTRY] = []

        if step_operator_flag:
            stack_component_update[StackComponentType.STEP_OPERATOR] = []

        if feature_store_flag:
            stack_component_update[StackComponentType.FEATURE_STORE] = []

        if model_deployer_flag:
            stack_component_update[StackComponentType.MODEL_DEPLOYER] = []

        if experiment_tracker_flag:
            stack_component_update[StackComponentType.EXPERIMENT_TRACKER] = []

        if alerter_flag:
            stack_component_update[StackComponentType.ALERTER] = []

        if model_registry_flag:
            stack_component_update[StackComponentType.MODEL_REGISTRY] = []

        if annotator_flag:
            stack_component_update[StackComponentType.ANNOTATOR] = []

        if data_validator_flag:
            stack_component_update[StackComponentType.DATA_VALIDATOR] = []

        if image_builder_flag:
            stack_component_update[StackComponentType.IMAGE_BUILDER] = []

        try:
            updated_stack = client.update_stack(
                name_id_or_prefix=stack_name_or_id,
                component_updates=stack_component_update,
            )
        except (KeyError, IllegalOperationError) as err:
            cli_utils.error(str(err))
        cli_utils.declare(
            f"Stack `{updated_stack.name}` successfully updated!"
        )


@stack.command("rename", help="Rename a stack.")
@click.argument("stack_name_or_id", type=str, required=True)
@click.argument("new_stack_name", type=str, required=True)
def rename_stack(
    stack_name_or_id: str,
    new_stack_name: str,
) -> None:
    """Rename a stack.

    Args:
        stack_name_or_id: Name of the stack to rename.
        new_stack_name: New name of the stack.
    """
    client = Client()

    with console.status("Renaming stack...\n"):
        try:
            stack_ = client.update_stack(
                name_id_or_prefix=stack_name_or_id,
                name=new_stack_name,
            )
        except (KeyError, IllegalOperationError) as err:
            cli_utils.error(str(err))
        cli_utils.declare(
            f"Stack `{stack_name_or_id}` successfully renamed to `"
            f"{new_stack_name}`!"
        )

    print_model_url(get_stack_url(stack_))


@stack.command("list")
@list_options(StackFilter)
@click.pass_context
def list_stacks(ctx: click.Context, **kwargs: Any) -> None:
    """List all stacks that fulfill the filter requirements.

    Args:
        ctx: the Click context
        kwargs: Keyword arguments to filter the stacks.
    """
    client = Client()
    with console.status("Listing stacks...\n"):
        stacks = client.list_stacks(**kwargs)
        if not stacks:
            cli_utils.declare("No stacks found for the given filters.")
            return
        print_stacks_table(
            client=client,
            stacks=stacks.items,
            show_active=not is_sorted_or_filtered(ctx),
        )
        print_page_info(stacks)


@stack.command(
    "describe",
    help="Show details about the current active stack.",
)
@click.argument(
    "stack_name_or_id",
    type=click.STRING,
    required=False,
)
@click.option(
    "--outputs",
    "-o",
    is_flag=True,
    default=False,
    help="Include the outputs from mlstacks deployments.",
)
def describe_stack(
    stack_name_or_id: Optional[str] = None, outputs: bool = False
) -> None:
    """Show details about a named stack or the active stack.

    Args:
        stack_name_or_id: Name of the stack to describe.
        outputs: Include the outputs from mlstacks deployments.
    """
    client = Client()

    with console.status("Describing the stack...\n"):
        try:
            stack_: "StackResponse" = client.get_stack(
                name_id_or_prefix=stack_name_or_id
            )
        except KeyError as err:
            cli_utils.error(str(err))

        cli_utils.print_stack_configuration(
            stack=stack_,
            active=stack_.id == client.active_stack_model.id,
        )
        if outputs:
            cli_utils.print_stack_outputs(stack_)

    print_model_url(get_stack_url(stack_))


@stack.command("delete", help="Delete a stack given its name.")
@click.argument("stack_name_or_id", type=str)
@click.option("--yes", "-y", is_flag=True, required=False)
@click.option(
    "--recursive",
    "-r",
    is_flag=True,
    help="Recursively delete all stack components",
)
def delete_stack(
    stack_name_or_id: str, yes: bool = False, recursive: bool = False
) -> None:
    """Delete a stack.

    Args:
        stack_name_or_id: Name or id of the stack to delete.
        yes: Stack will be deleted without prompting for
            confirmation.
        recursive: The stack will be deleted along with the corresponding stack
            associated with it.
    """
    recursive_confirmation = False
    if recursive:
        recursive_confirmation = yes or cli_utils.confirmation(
            "If there are stack components present in another stack, "
            "those stack components will be ignored for removal \n"
            "Do you want to continue ?"
        )

        if not recursive_confirmation:
            cli_utils.declare("Stack deletion canceled.")
            return

    confirmation = (
        recursive_confirmation
        or yes
        or cli_utils.confirmation(
            f"This will delete stack '{stack_name_or_id}'. \n"
            "Are you sure you want to proceed?"
        )
    )

    if not confirmation:
        cli_utils.declare("Stack deletion canceled.")
        return

    with console.status(f"Deleting stack '{stack_name_or_id}'...\n"):
        client = Client()

        if recursive and recursive_confirmation:
            client.delete_stack(stack_name_or_id, recursive=True)
            return

        try:
            client.delete_stack(stack_name_or_id)
        except (KeyError, ValueError, IllegalOperationError) as err:
            cli_utils.error(str(err))
        cli_utils.declare(f"Deleted stack '{stack_name_or_id}'.")


@stack.command("set", help="Sets a stack as active.")
@click.argument("stack_name_or_id", type=str)
def set_active_stack_command(stack_name_or_id: str) -> None:
    """Sets a stack as active.

    Args:
        stack_name_or_id: Name of the stack to set as active.
    """
    client = Client()
    scope = "repository" if client.uses_local_configuration else "global"

    with console.status(
        f"Setting the {scope} active stack to '{stack_name_or_id}'..."
    ):
        try:
            client.activate_stack(stack_name_id_or_prefix=stack_name_or_id)
        except KeyError as err:
            cli_utils.error(str(err))

        cli_utils.declare(
            f"Active {scope} stack set to: "
            f"'{client.active_stack_model.name}'"
        )


@stack.command("get")
def get_active_stack() -> None:
    """Gets the active stack."""
    scope = "repository" if Client().uses_local_configuration else "global"

    with console.status("Getting the active stack..."):
        client = Client()
        try:
            cli_utils.declare(
                f"The {scope} active stack is: '{client.active_stack_model.name}'"
            )
        except KeyError as err:
            cli_utils.error(str(err))


@stack.command("up")
def up_stack() -> None:
    """Provisions resources for the active stack."""
    stack_ = Client().active_stack

    cli_utils.declare(
        f"Provisioning resources for active stack '{stack_.name}'."
    )
    try:
        stack_.provision()
        stack_.resume()
    except ProvisioningError as e:
        cli_utils.error(str(e))


@stack.command(
    "down", help="Suspends resources of the active stack deployment."
)
@click.option(
    "--force",
    "-f",
    "force",
    is_flag=True,
    help="Deprovisions local resources instead of suspending them.",
)
def down_stack(force: bool = False) -> None:
    """Suspends resources of the active stack deployment.

    Args:
        force: Deprovisions local resources instead of suspending them.
    """
    stack_ = Client().active_stack

    if force:
        cli_utils.declare(
            f"Deprovisioning resources for active stack '{stack_.name}'."
        )
        stack_.deprovision()
    else:
        cli_utils.declare(
            f"Suspending resources for active stack '{stack_.name}'."
        )
        stack_.suspend()


@stack.command("export", help="Exports a stack to a YAML file.")
@click.argument("stack_name_or_id", type=str, required=False)
@click.argument("filename", type=str, required=False)
def export_stack(
    stack_name_or_id: Optional[str] = None,
    filename: Optional[str] = None,
) -> None:
    """Export a stack to YAML.

    Args:
        stack_name_or_id: The name of the stack to export.
        filename: The filename to export the stack to.
    """
    # Get configuration of given stack
    client = Client()
    try:
        stack_to_export = client.get_stack(name_id_or_prefix=stack_name_or_id)
    except KeyError as err:
        cli_utils.error(str(err))

    # write zenml version and stack dict to YAML
    yaml_data = stack_to_export.to_yaml()
    yaml_data["zenml_version"] = zenml.__version__

    if filename is None:
        filename = stack_to_export.name + ".yaml"
    write_yaml(filename, yaml_data)

    cli_utils.declare(
        f"Exported stack '{stack_to_export.name}' to file '{filename}'."
    )


def _import_stack_component(
    component_type: StackComponentType,
    component_dict: Dict[str, Any],
    component_spec_path: Optional[str] = None,
) -> UUID:
    """Import a single stack component with given type/config.

    Args:
        component_type: The type of component to import.
        component_dict: Dict representation of the component to import.
        component_spec_path: Path to the component spec file.

    Returns:
        The ID of the imported component.
    """
    name = component_dict["name"]
    flavor = component_dict["flavor"]
    config = component_dict["configuration"]

    # make sure component can be registered, otherwise ask for new name
    client = Client()

    try:
        component = client.get_stack_component(
            name_id_or_prefix=name,
            component_type=component_type,
        )
        if component.configuration == config:
            return component.id
        else:
            display_name = _component_display_name(component_type)
            name = click.prompt(
                f"A component of type '{display_name}' with the name "
                f"'{name}' already exists, "
                f"but is configured differently. "
                f"Please choose a different name.",
                type=str,
            )
    except KeyError:
        pass

    component = client.create_stack_component(
        name=name,
        component_type=component_type,
        flavor=flavor,
        configuration=config,
        component_spec_path=component_spec_path,
    )
    return component.id


@stack.command("import", help="Import a stack from YAML.")
@click.argument("stack_name", type=str, required=True)
@click.option("--filename", "-f", type=str, required=False)
@click.option(
    "--ignore-version-mismatch",
    is_flag=True,
    help="Import stack components even if the installed version of ZenML "
    "is different from the one specified in the stack YAML file",
)
def import_stack(
    stack_name: str,
    filename: Optional[str],
    ignore_version_mismatch: bool = False,
) -> None:
    """Import a stack from YAML.

    Args:
        stack_name: The name of the stack to import.
        filename: The filename to import the stack from.
        ignore_version_mismatch: Import stack components even if
            the installed version of ZenML is different from the
            one specified in the stack YAML file.
    """
    # handle 'zenml stack import file.yaml' calls
    if stack_name.endswith(".yaml") and filename is None:
        filename = stack_name
        data = read_yaml(filename)
        stack_name = data["stack_name"]  # read stack_name from export

    # standard 'zenml stack import stack_name [file.yaml]' calls
    else:
        # if filename is not given, assume default export name
        # "<stack_name>.yaml"
        if filename is None:
            filename = stack_name + ".yaml"
        data = read_yaml(filename)
        cli_utils.declare(
            f"Using '{filename}' to import '{stack_name}' stack."
        )

    # assert zenml version is the same if force is false
    if data["zenml_version"] != zenml.__version__:
        if ignore_version_mismatch:
            cli_utils.warning(
                f"The stack that will be installed is using ZenML version "
                f"{data['zenml_version']}. You have version "
                f"{zenml.__version__} installed. Some components might not "
                "work as expected."
            )
        else:
            cli_utils.error(
                f"Cannot import stacks from other ZenML versions. "
                f"The stack was created using ZenML version "
                f"{data['zenml_version']}, you have version "
                f"{zenml.__version__} installed. You can "
                "retry using the `--ignore-version-mismatch` "
                "flag. However, be aware that this might "
                "fail or lead to other unexpected behavior."
            )

    # ask user for a new stack_name if current one already exists
    client = Client()
    if client.list_stacks(name=stack_name):
        stack_name = click.prompt(
            f"Stack `{stack_name}` already exists. Please choose a different "
            f"name",
            type=str,
        )

    # import stack components
    component_ids = {}
    for component_type_str, component_config in data["components"].items():
        component_type = StackComponentType(component_type_str)

        component_id = _import_stack_component(
            component_type=component_type,
            component_dict=component_config,
        )
        component_ids[component_type] = component_id

    imported_stack = Client().create_stack(
        name=stack_name, components=component_ids
    )

    print_model_url(get_stack_url(imported_stack))


@stack.command("copy", help="Copy a stack to a new stack name.")
@click.argument("source_stack_name_or_id", type=str, required=True)
@click.argument("target_stack", type=str, required=True)
def copy_stack(source_stack_name_or_id: str, target_stack: str) -> None:
    """Copy a stack.

    Args:
        source_stack_name_or_id: The name or id of the stack to copy.
        target_stack: Name of the copied stack.
    """
    client = Client()

    with console.status(f"Copying stack `{source_stack_name_or_id}`...\n"):
        try:
            stack_to_copy = client.get_stack(
                name_id_or_prefix=source_stack_name_or_id
            )
        except KeyError as err:
            cli_utils.error(str(err))

        component_mapping: Dict[StackComponentType, Union[str, UUID]] = {}

        for c_type, c_list in stack_to_copy.components.items():
            if c_list:
                component_mapping[c_type] = c_list[0].id

        copied_stack = client.create_stack(
            name=target_stack,
            components=component_mapping,
        )

    print_model_url(get_stack_url(copied_stack))


@stack.command(
    "register-secrets",
    help="Interactively register all required secrets for a stack.",
)
@click.argument("stack_name_or_id", type=str, required=False)
@click.option(
    "--skip-existing",
    "skip_existing",
    is_flag=True,
    default=False,
    help="Skip secrets with existing values.",
    type=bool,
)
def register_secrets(
    skip_existing: bool,
    stack_name_or_id: Optional[str] = None,
) -> None:
    """Interactively registers all required secrets for a stack.

    Args:
        skip_existing: If `True`, skip asking for secret values that already
            exist.
        stack_name_or_id: Name of the stack for which to register secrets.
                          If empty, the active stack will be used.
    """
    from zenml.stack.stack import Stack

    client = Client()

    stack_model = client.get_stack(name_id_or_prefix=stack_name_or_id)

    stack_ = Stack.from_model(stack_model)
    required_secrets = stack_.required_secrets

    if not required_secrets:
        cli_utils.declare("No secrets required for this stack.")
        return

    secret_names = {s.name for s in required_secrets}

    secrets_to_register = []
    secrets_to_update = []
    for name in secret_names:
        try:
            secret_content = client.get_secret(name).secret_values.copy()
            secret_exists = True
        except KeyError:
            secret_content = {}
            secret_exists = False

        required_keys = {s.key for s in required_secrets if s.name == name}
        needs_update = False

        for key in required_keys:
            existing_value = secret_content.get(key, None)

            if existing_value:
                if skip_existing:
                    continue

                value = getpass.getpass(
                    f"Value for secret `{name}.{key}` "
                    "(Leave empty to use existing value):"
                )
                if value:
                    value = cli_utils.expand_argument_value_from_file(
                        name=key, value=value
                    )
                else:
                    value = existing_value

                # only need to update if the value changed
                needs_update = needs_update or value != existing_value
            else:
                value = None
                while not value:
                    value = getpass.getpass(
                        f"Value for secret `{name}.{key}`:"
                    )
                value = cli_utils.expand_argument_value_from_file(
                    name=key, value=value
                )
                needs_update = True

            secret_content[key] = value

        if not secret_exists:
            secrets_to_register.append(
                (
                    name,
                    secret_content,
                )
            )
        elif needs_update:
            secrets_to_update.append(
                (
                    name,
                    secret_content,
                )
            )

    for secret_name, secret_values in secrets_to_register:
        cli_utils.declare(f"Registering secret `{secret_name}`:")
        cli_utils.pretty_print_secret(secret_values, hide_secret=True)
        client.create_secret(secret_name, values=secret_values)
    for secret_name, secret_values in secrets_to_update:
        cli_utils.declare(f"Updating secret `{secret_name}`:")
        cli_utils.pretty_print_secret(secret_values, hide_secret=True)
        client.update_secret(secret_name, add_or_update_values=secret_values)


def _get_deployment_params_interactively(
    click_params: Dict[str, Any],
) -> Dict[str, Any]:
    """Get deployment values from command line arguments.

    Args:
        click_params: Required and pre-existing values.

    Returns:
        Full deployment arguments.
    """
    deployment_values = {
        "provider": click_params["provider"],
        "stack_name": click_params["stack_name"],
        "region": click_params["region"],
    }
    for component_type in MLSTACKS_SUPPORTED_STACK_COMPONENTS:
        verify_mlstacks_prerequisites_installation()
        from mlstacks.constants import ALLOWED_FLAVORS

        if (
            click.prompt(
                f"Enable {component_type}?",
                type=click.Choice(["y", "n"]),
                default="n",
            )
            == "y"
        ):
            component_flavor = click.prompt(
                f"  Enter {component_type} flavor",
                type=click.Choice(ALLOWED_FLAVORS[component_type]),
            )
            deployment_values[component_type] = component_flavor

    if (
        click.prompt(
            "Deploy using debug_mode?",
            type=click.Choice(["y", "n"]),
            default="n",
        )
        == "y"
    ):
        deployment_values["debug_mode"] = True

    extra_config = []
    # use click.prompt to populate extra_config until someone just hits enter
    while True:
        declare(
            "\nAdd to extra_config for stack deployment -->\n",
            bold=True,
        )
        key = click.prompt(
            "Enter `extra_config` key or hit enter to skip",
            type=str,
            default="",
        )
        if key == "":
            break
        value = click.prompt(
            f"Enter value for '{key}'",
            type=str,
        )
        extra_config.append(f"{key}={value}")

    # get mandatory GCP project_id if provider is GCP
    # skip if project_id already specified in extra_config
    if click_params["provider"] == "gcp" and not any(
        s.startswith("project_id=") for s in extra_config
    ):
        project_id = click.prompt("What is your GCP project_id?", type=str)
        extra_config.append(f"project_id={project_id}")
        declare(f"Project ID '{project_id}' added to extra_config.")

    deployment_values["extra_config"] = extra_config

    tags = []
    # use click.prompt to populate tags until someone just hits enter
    while True:
        declare(
            "\nAdd to tags for stack deployment -->\n",
            bold=True,
        )
        tag = click.prompt(
            "Enter `tags` key or hit enter to skip",
            type=str,
            default="",
        )
        if tag == "":
            break
        value = click.prompt(
            f"Enter value for '{tag}'",
            type=str,
        )
        tags.append(f"{tag}={value}")
    deployment_values["tags"] = tags

    return deployment_values


@stack.command(help="Deploy a stack using mlstacks.")
@click.option(
    "--provider",
    "-p",
    "provider",
    required=True,
    type=click.Choice(STACK_RECIPE_MODULAR_RECIPES),
)
@click.option(
    "--name",
    "-n",
    "stack_name",
    type=click.STRING,
    required=True,
    help="Set a name for the ZenML stack that will be imported from the YAML "
    "configuration file which gets generated after deploying the stack recipe. "
    "Defaults to the name of the stack recipe being deployed.",
)
@click.option(
    "--region",
    "-r",
    "region",
    type=click.STRING,
    required=True,
    help="The region to deploy the stack to.",
)
@click.option(
    "--no-import",
    "-ni",
    "no_import_stack_flag",
    is_flag=True,
    help="If you don't want the stack to be imported automatically.",
)
@click.option(
    "--artifact-store",
    "-a",
    "artifact_store",
    required=False,
    is_flag=True,
    help="Whether to deploy an artifact store.",
)
@click.option(
    "--container-registry",
    "-c",
    "container_registry",
    required=False,
    is_flag=True,
    help="Whether to deploy a container registry.",
)
@click.option(
    "--mlops-platform",
    "-m",
    "mlops_platform",
    type=click.Choice(["zenml"]),
    required=False,
    help="The flavor of MLOps platform to use."
    "If not specified, the default MLOps platform will be used.",
)
@click.option(
    "--orchestrator",
    "-o",
    required=False,
    type=click.Choice(
        [
            "kubernetes",
            "kubeflow",
            "tekton",
            "sagemaker",
            "skypilot",
            "vertex",
        ]
    ),
    help="The flavor of orchestrator to use. "
    "If not specified, the default orchestrator will be used.",
)
@click.option(
    "--model-deployer",
    "-md",
    "model_deployer",
    required=False,
    type=click.Choice(["mlflow", "seldon"]),
    help="The flavor of model deployer to use. ",
)
@click.option(
    "--experiment-tracker",
    "-e",
    "experiment_tracker",
    required=False,
    type=click.Choice(["mlflow"]),
    help="The flavor of experiment tracker to use.",
)
@click.option(
    "--step-operator",
    "-s",
    "step_operator",
    required=False,
    type=click.Choice(["sagemaker"]),
    help="The flavor of step operator to use.",
)
@click.option(
    "--file",
    "-f",
    "file",
    required=False,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Use a YAML specification file as the basis of the stack deployment.",
)
@click.option(
    "--debug-mode",
    "-d",
    "debug_mode",
    is_flag=True,
    default=False,
    help="Whether to run the stack deployment in debug mode.",
)
@click.option(
    "--extra-config",
    "-x",
    "extra_config",
    multiple=True,
    help="Extra configurations as key=value pairs. This option can be used multiple times.",
)
@click.option(
    "--tags",
    "-t",
    "tags",
    required=False,
    type=click.STRING,
    help="Pass one or more tags.",
    multiple=True,
)
@click.option(
    "--interactive",
    "-i",
    "interactive",
    is_flag=True,
    default=False,
    help="Deploy the stack interactively.",
)
@click.pass_context
def deploy(
    ctx: click.Context,
    provider: str,
    stack_name: str,
    region: str,
    mlops_platform: Optional[str] = None,
    orchestrator: Optional[str] = None,
    model_deployer: Optional[str] = None,
    experiment_tracker: Optional[str] = None,
    step_operator: Optional[str] = None,
    no_import_stack_flag: bool = False,
    artifact_store: Optional[bool] = None,
    container_registry: Optional[bool] = None,
    file: Optional[str] = None,
    debug_mode: bool = False,
    tags: Optional[List[str]] = None,
    extra_config: Optional[List[str]] = None,
    interactive: bool = False,
) -> None:
    """Deploy a stack with mlstacks.

    `zenml stack_recipe pull <STACK_RECIPE_NAME>` has to be called with the
    same relative path before the `deploy` command.

    Args:
        ctx: The click context.
        provider: The cloud provider to deploy the stack to.
        stack_name: A name for the ZenML stack that gets imported as a result
            of the recipe deployment.
        no_import_stack_flag: If you don't want the stack to be imported into
            ZenML after deployment.
        artifact_store: The flavor of artifact store to deploy. In the case of
            the artifact store, it doesn't matter what you specify here, as
            there's only one flavor per cloud provider and that will be deployed.
        orchestrator: The flavor of orchestrator to use.
        container_registry: The flavor of container registry to deploy. In the case of
            the container registry, it doesn't matter what you specify here, as
            there's only one flavor per cloud provider and that will be deployed.
        model_deployer: The flavor of model deployer to deploy.
        experiment_tracker: The flavor of experiment tracker to deploy.
        step_operator: The flavor of step operator to deploy.
        extra_config: Extra configurations as key=value pairs.
        tags: Pass one or more tags.
        debug_mode: Whether to run the stack deployment in debug mode.
        file: Use a YAML specification file as the basis of the stack
            deployment.
        mlops_platform: The flavor of MLOps platform to use.
        region: The region to deploy the stack to.
        interactive: Deploy the stack interactively.
    """
    with track_handler(
        event=AnalyticsEvent.DEPLOY_STACK,
    ) as analytics_handler:
        if stack_exists(stack_name):
            cli_utils.error(
                f"Stack with name '{stack_name}' already exists. Please choose a "
                "different name."
            )
        elif stack_spec_exists(stack_name):
            cli_utils.error(
                f"Stack spec for stack named '{stack_name}' already exists. "
                "Please choose a different name."
            )

        cli_utils.declare("Checking prerequisites are installed...")
        cli_utils.verify_mlstacks_prerequisites_installation()
        cli_utils.warning(ALPHA_MESSAGE)

        if not file:
            cli_params: Dict[str, Any] = ctx.params
            if interactive:
                cli_params = _get_deployment_params_interactively(cli_params)
            stack, components = convert_click_params_to_mlstacks_primitives(
                cli_params
            )

            from mlstacks.utils import zenml_utils

            cli_utils.declare("Checking flavor compatibility...")
            if not zenml_utils.has_valid_flavor_combinations(
                stack, components
            ):
                cli_utils.error(
                    "The specified stack and component flavors are not compatible "
                    "with the provider or with one another. Please try again."
                )

            stack_dict, component_dicts = convert_mlstacks_primitives_to_dicts(
                stack, components
            )
            # write the stack and component yaml files
            from mlstacks.constants import MLSTACKS_PACKAGE_NAME

            spec_dir = os.path.join(
                click.get_app_dir(MLSTACKS_PACKAGE_NAME),
                "stack_specs",
                stack.name,
            )
            cli_utils.declare(f"Writing spec files to {spec_dir}...")
            create_dir_recursive_if_not_exists(spec_dir)

            stack_file_path = os.path.join(
                spec_dir, f"stack-{stack.name}.yaml"
            )
            write_yaml(file_path=stack_file_path, contents=stack_dict)
            for component in component_dicts:
                write_yaml(
                    file_path=os.path.join(
                        spec_dir, f"{component['name']}.yaml"
                    ),
                    contents=component,
                )
        else:
            declare("Importing from stack specification file...")
            stack_file_path = file

            from mlstacks.utils.yaml_utils import load_stack_yaml

            stack = load_stack_yaml(stack_file_path)

        analytics_handler.metadata = {
            "stack_provider": stack.provider,
            "debug_mode": debug_mode,
            "no_import_stack_flag": no_import_stack_flag,
            "user_created_spec": bool(file),
            "mlops_platform": mlops_platform,
            "orchestrator": orchestrator,
            "model_deployer": model_deployer,
            "experiment_tracker": experiment_tracker,
            "step_operator": step_operator,
            "artifact_store": artifact_store,
            "container_registry": container_registry,
        }

        deploy_mlstacks_stack(
            spec_file_path=stack_file_path,
            stack_name=stack.name,
            stack_provider=stack.provider,
            debug_mode=debug_mode,
            no_import_stack_flag=no_import_stack_flag,
            user_created_spec=bool(file),
        )


@stack.command(
    help="Destroy stack components created previously with "
    "`zenml stack deploy`"
)
@click.argument("stack_name", required=True)
@click.option(
    "--debug",
    "-d",
    "debug_mode",
    is_flag=True,
    default=False,
    help="Whether to run Terraform in debug mode.",
)
def destroy(
    stack_name: str,
    debug_mode: bool = False,
) -> None:
    """Destroy all resources previously created with `zenml stack deploy`.

    Args:
        stack_name: Name of the stack
        debug_mode: Whether to run Terraform in debug mode.
    """
    if not confirmation(
        f"Are you sure you want to destroy stack '{stack_name}' and all "
        "associated infrastructure?"
    ):
        error("Aborting stack destroy...")

    with track_handler(
        event=AnalyticsEvent.DESTROY_STACK,
    ) as analytics_handler:
        analytics_handler.metadata["debug_mode"] = debug_mode
        cli_utils.verify_mlstacks_prerequisites_installation()
        from mlstacks.constants import MLSTACKS_PACKAGE_NAME

        # check the stack actually exists
        if not stack_exists(stack_name):
            cli_utils.error(
                f"Stack with name '{stack_name}' does not exist. Please check and "
                "try again."
            )

        spec_file_path = get_stack_spec_file_path(stack_name)
        spec_files_dir: str = os.path.join(
            click.get_app_dir(MLSTACKS_PACKAGE_NAME), "stack_specs", stack_name
        )
        user_created_spec = str(Path(spec_file_path).parent) != spec_files_dir

        provider = read_yaml(file_path=spec_file_path).get("provider")
        tf_definitions_path: str = os.path.join(
            click.get_app_dir(MLSTACKS_PACKAGE_NAME),
            "terraform",
            f"{provider}-modular",
        )

        cli_utils.declare(
            "Checking Terraform definitions and spec files are present..."
        )
        verify_spec_and_tf_files_exist(spec_file_path, tf_definitions_path)

        from mlstacks.utils import terraform_utils

        cli_utils.declare(
            f"Destroying stack '{stack_name}' using Terraform..."
        )
        terraform_utils.destroy_stack(
            stack_path=spec_file_path, debug_mode=debug_mode
        )
        cli_utils.declare(f"Stack '{stack_name}' successfully destroyed.")

        if cli_utils.confirmation(
            f"Would you like to recursively delete the associated ZenML "
            f"stack '{stack_name}'?\nThis will delete the stack and any "
            "underlying stack components."
        ):
            from zenml.client import Client

            client = Client()
            client.delete_stack(name_id_or_prefix=stack_name, recursive=True)
            cli_utils.declare(
                f"Stack '{stack_name}' successfully deleted from ZenML."
            )

        spec_dir = os.path.dirname(spec_file_path)
        if not user_created_spec and cli_utils.confirmation(
            f"Would you like to delete the `mlstacks` spec directory for "
            f"this stack, located at {spec_dir}?"
        ):
            rmtree(spec_files_dir)
            cli_utils.declare(
                f"Spec directory for stack '{stack_name}' successfully deleted."
            )
        cli_utils.declare(f"Stack '{stack_name}' successfully destroyed.")


@stack.command(
    "connect",
    help="Connect a service-connector to a stack's components. "
    "Note that this only connects the service-connector to the current "
    "components of the stack and not to the stack itself, which means that "
    "you need to rerun the command after adding new components to the stack.",
)
@click.argument("stack_name_or_id", type=str, required=False)
@click.option(
    "--connector",
    "-c",
    "connector",
    help="The name, ID or prefix of the connector to use.",
    required=False,
    type=str,
)
@click.option(
    "--interactive",
    "-i",
    "interactive",
    is_flag=True,
    default=False,
    help="Configure a service connector resource interactively.",
    type=click.BOOL,
)
@click.option(
    "--no-verify",
    "no_verify",
    is_flag=True,
    default=False,
    help="Skip verification of the connector resource.",
    type=click.BOOL,
)
def connect_stack(
    stack_name_or_id: Optional[str] = None,
    connector: Optional[str] = None,
    interactive: bool = False,
    no_verify: bool = False,
) -> None:
    """Connect a service-connector to all components of a stack.

    Args:
        stack_name_or_id: Name of the stack to connect.
        connector: The name, ID or prefix of the connector to use.
        interactive: Configure a service connector resource interactively.
        no_verify: Skip verification of the connector resource.
    """
    from zenml.cli.stack_components import (
        connect_stack_component_with_service_connector,
    )

    client = Client()
    stack_to_connect = client.get_stack(name_id_or_prefix=stack_name_or_id)
    for component in stack_to_connect.components.values():
        connect_stack_component_with_service_connector(
            component_type=component[0].type,
            name_id_or_prefix=component[0].name,
            connector=connector,
            interactive=interactive,
            no_verify=no_verify,
        )


def _get_service_connector_info(
    cloud_provider: str,
    connector_details: Optional[
        Union[ServiceConnectorResponse, ServiceConnectorRequest]
    ],
) -> ServiceConnectorInfo:
    """Get a service connector info with given cloud provider.

    Args:
        cloud_provider: The cloud provider to use.
        connector_details: Whether to use implicit credentials.

    Returns:
        The info model of the created service connector.

    Raises:
        ValueError: If the cloud provider is not supported.
    """
    from rich.prompt import Prompt

    if cloud_provider not in {"aws", "azure", "gcp"}:
        raise ValueError(f"Unknown cloud provider {cloud_provider}")

    client = Client()
    auth_methods = client.get_service_connector_type(
        cloud_provider
    ).auth_method_dict
    if not connector_details:
        fixed_auth_methods = list(
            [
                (key, value)
                for key, value in auth_methods.items()
                if key != "implicit"
            ]
        )
        choices = []
        headers = ["Name", "Required"]
        for _, value in fixed_auth_methods:
            schema = value.config_schema
            required = ""
            for each_req in schema["required"]:
                field = schema["properties"][each_req]
                required += f"[bold]{each_req}[/bold]  [italic]({field.get('title','no description')})[/italic]\n"
            choices.append([value.name, required])

        selected_auth_idx = cli_utils.multi_choice_prompt(
            object_type=f"authentication methods for {cloud_provider}",
            choices=choices,
            headers=headers,
            prompt_text="Please choose one of the authentication option above.",
        )
        if selected_auth_idx is None:
            cli_utils.error("No authentication method selected.")
        auth_type = fixed_auth_methods[selected_auth_idx][0]
    else:
        auth_type = connector_details.auth_method

    selected_auth_model = auth_methods[auth_type]

    required_fields = selected_auth_model.config_schema["required"]
    properties = selected_auth_model.config_schema["properties"]

    answers = {}
    for req_field in required_fields:
        if connector_details:
            if conf_value := connector_details.configuration.get(
                req_field, None
            ):
                answers[req_field] = conf_value
            elif secret_value := connector_details.secrets.get(
                req_field, None
            ):
                answers[req_field] = secret_value.get_secret_value()
        if req_field not in answers:
            answers[req_field] = Prompt.ask(
                f"Please enter value for `{req_field}`:",
                password="format" in properties[req_field]
                and properties[req_field]["format"] == "password",
            )

    return ServiceConnectorInfo(
        type=cloud_provider,
        auth_method=auth_type,
        configuration=answers,
    )


def _get_stack_component_info(
    component_type: str,
    cloud_provider: str,
    service_connector_resource_models: List[
        ServiceConnectorTypedResourcesModel
    ],
    service_connector_index: Optional[int] = None,
) -> ComponentInfo:
    """Get a stack component info with given type and service connector.

    Args:
        component_type: The type of component to create.
        cloud_provider: The cloud provider to use.
        service_connector_resource_models: The list of the available service connector resource models.
        service_connector_index: The index of the service connector to use.

    Returns:
        The info model of the stack component.

    Raises:
        ValueError: If the cloud provider is not supported.
        ValueError: If the component type is not supported.
    """
    from rich.prompt import Prompt

    if cloud_provider not in {"aws", "azure", "gcp"}:
        raise ValueError(f"Unknown cloud provider {cloud_provider}")

    AWS_DOCS = (
        "https://docs.zenml.io/how-to/auth-management/aws-service-connector"
    )

    flavor = "undefined"
    service_connector_resource_id = None
    config = {}
    if component_type == "artifact_store":
        available_storages: List[str] = []
        if cloud_provider == "aws":
            for each in service_connector_resource_models:
                if each.resource_type == "s3-bucket":
                    available_storages = each.resource_ids or []
            flavor = "s3"
            if not available_storages:
                cli_utils.error(
                    "We were unable to find any S3 buckets available "
                    "to configured service connector. Please, verify "
                    "that needed permission are granted for the "
                    "service connector.\nDocumentation for the S3 "
                    "Buckets configuration can be found at "
                    f"{AWS_DOCS}#s3-bucket"
                )
        elif cloud_provider == "azure":
            flavor = "azure"
        elif cloud_provider == "gcp":
            flavor = "gcs"

        selected_storage_idx = cli_utils.multi_choice_prompt(
            object_type=f"{cloud_provider.upper()} storages",
            choices=[[st] for st in available_storages],
            headers=["Storage"],
            prompt_text="Please choose one of the storages for the new artifact store:",
        )
        if selected_storage_idx is None:
            cli_utils.error("No storage selected.")

        selected_storage = available_storages[selected_storage_idx]

        config = {"path": selected_storage}
        service_connector_resource_id = selected_storage
    elif component_type == "orchestrator":
        if cloud_provider == "aws":
            available_orchestrators = []
            for each in service_connector_resource_models:
                types = []
                if each.resource_type == "aws-generic":
                    types = ["Sagemaker", "Skypilot (EC2)"]
                if each.resource_type == "kubernetes-cluster":
                    types = ["Kubernetes"]

                if each.resource_ids:
                    for orchestrator in each.resource_ids:
                        for t in types:
                            available_orchestrators.append([t, orchestrator])
            if not available_orchestrators:
                cli_utils.error(
                    "We were unable to find any orchestrator engines "
                    "available to the service connector. Please, verify "
                    "that needed permission are granted for the "
                    "service connector.\nDocumentation for the Generic "
                    "AWS resource configuration can be found at "
                    f"{AWS_DOCS}#generic-aws-resource\n"
                    "Documentation for the Kubernetes resource "
                    "configuration can be found at "
                    f"{AWS_DOCS}#eks-kubernetes-cluster"
                )
        elif cloud_provider == "gcp":
            pass
        elif cloud_provider == "azure":
            pass

        selected_orchestrator_idx = cli_utils.multi_choice_prompt(
            object_type=f"orchestrators on {cloud_provider.upper()}",
            choices=available_orchestrators,
            headers=["Orchestrator Type", "Orchestrator details"],
            prompt_text="Please choose one of the orchestrators for the new orchestrator:",
        )
        if selected_orchestrator_idx is None:
            cli_utils.error("No orchestrator selected.")

        selected_orchestrator = available_orchestrators[
            selected_orchestrator_idx
        ]

        if selected_orchestrator[0] == "Sagemaker":
            flavor = "sagemaker"
            execution_role = Prompt.ask("Please enter an execution role ARN:")
            config = {"execution_role": execution_role}
        elif selected_orchestrator[0] == "Skypilot (EC2)":
            flavor = "vm_aws"
            config = {"region": selected_orchestrator[1]}
        elif selected_orchestrator[0] == "Kubernetes":
            flavor = "kubernetes"
            config = {}
        else:
            raise ValueError(
                f"Unknown orchestrator type {selected_orchestrator[0]}"
            )
        service_connector_resource_id = selected_orchestrator[1]
    elif component_type == "container_registry":
        available_registries: List[str] = []
        if cloud_provider == "aws":
            flavor = "aws"
            for each in service_connector_resource_models:
                if each.resource_type == "docker-registry":
                    available_registries = each.resource_ids or []
            if not available_registries:
                cli_utils.error(
                    "We were unable to find any container registries "
                    "available to the service connector. Please, verify "
                    "that needed permission are granted for the "
                    "service connector.\nDocumentation for the ECR "
                    "container registry resource configuration can "
                    f"be found at {AWS_DOCS}#ecr-container-registry"
                )
        elif cloud_provider == "azure":
            flavor = "azure"
        elif cloud_provider == "gcp":
            flavor = "gcp"

        selected_registry_idx = cli_utils.multi_choice_prompt(
            object_type=f"{cloud_provider.upper()} registries",
            choices=[[st] for st in available_registries],
            headers=["Container Registry"],
            prompt_text="Please choose one of the registries for the new container registry:",
        )
        if selected_registry_idx is None:
            cli_utils.error("No container registry selected.")
        selected_registry = available_registries[selected_registry_idx]
        config = {"uri": selected_registry}
        service_connector_resource_id = selected_registry
    else:
        raise ValueError(f"Unknown component type {component_type}")

    return ComponentInfo(
        flavor=flavor,
        configuration=config,
        service_connector_index=service_connector_index,
        service_connector_resource_id=service_connector_resource_id,
    )
