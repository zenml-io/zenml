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
import re
import time
import webbrowser
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Set,
    Union,
)
from uuid import UUID

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.prompt import Confirm
from rich.style import Style
from rich.syntax import Syntax

import zenml
from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_handler
from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.cli.text_utils import OldSchoolMarkdownHeading
from zenml.cli.utils import (
    _component_display_name,
    is_sorted_or_filtered,
    list_options,
    print_model_url,
    print_page_info,
    print_stacks_table,
)
from zenml.client import Client
from zenml.console import console
from zenml.enums import (
    CliCategories,
    StackComponentType,
    StackDeploymentProvider,
)
from zenml.exceptions import (
    IllegalOperationError,
)
from zenml.logger import get_logger
from zenml.models import (
    ComponentInfo,
    ServiceConnectorInfo,
    ServiceConnectorResourcesInfo,
    StackFilter,
    StackRequest,
)
from zenml.models.v2.core.service_connector import (
    ServiceConnectorRequest,
    ServiceConnectorResponse,
)
from zenml.service_connectors.service_connector_utils import (
    get_resources_options_from_resource_model_for_full_stack,
)
from zenml.utils import requirements_utils
from zenml.utils.dashboard_utils import get_component_url, get_stack_url
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
            "The only way to register a stack without specifying an "
            "orchestrator and an artifact store is by using either a provider"
            "(-p/--provider) or an existing service connector "
            "(-sc/--connector). Please specify the artifact store and "
            "the orchestrator or the service connector or cloud type settings."
        )

    client = Client()

    if provider is not None or connector is not None:
        if client.zen_store.is_local_store():
            cli_utils.error(
                "You are registering a stack using a service connector, but "
                "this feature cannot be used with a local ZenML deployment. "
                "ZenML needs to be accessible from the cloud provider to allow "
                "the stack and its components to be registered automatically. "
                "Please deploy ZenML in a remote environment as described in "
                "the documentation: https://docs.zenml.io/getting-started/deploying-zenml "
                "or use a managed ZenML Pro server instance for quick access "
                "to this feature and more: https://www.zenml.io/pro"
            )

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

    labels: Dict[str, str] = {}
    components: Dict[StackComponentType, List[Union[UUID, ComponentInfo]]] = {}

    # Cloud Flow
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
        except NotImplementedError:
            cli_utils.warning(
                f"The {provider.upper()} service connector libraries are not "
                "installed properly. Please run `zenml integration install "
                f"{provider}` and try again to enable auto-discovery of the "
                "connection configuration."
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
                    prompt_text=f"We found these {provider.upper()} service "
                    "connectors. Do you want to create a new one or use one "
                    "of the existing ones?",
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
        labels["zenml:wizard"] = "true"
        if provider:
            labels["zenml:provider"] = provider
        resources_info = None
        # explore the service connector
        with console.status(
            "Exploring resources available to the service connector...\n"
        ):
            resources_info = (
                get_resources_options_from_resource_model_for_full_stack(
                    connector_details=service_connector
                )
            )
        if resources_info is None:
            cli_utils.error(
                f"Failed to fetch service connector resources information for {service_connector}..."
            )

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
                component_name = component_response.name
            else:
                if isinstance(service_connector, UUID):
                    # find existing components under same connector
                    if (
                        component_type
                        in resources_info.components_resources_info
                    ):
                        existing_components = [
                            existing_response
                            for res_info in resources_info.components_resources_info[
                                component_type
                            ]
                            for existing_response in res_info.connected_through_service_connector
                        ]

                        # if some existing components are found - prompt user what to do
                        component_selected: Optional[int] = None
                        component_selected = cli_utils.multi_choice_prompt(
                            object_type=component_type.value.replace("_", " "),
                            choices=[
                                [
                                    component.flavor_name,
                                    component.name,
                                    component.configuration or "",
                                    component.connector_resource_id,
                                ]
                                for component in existing_components
                            ],
                            headers=[
                                "Type",
                                "Name",
                                "Configuration",
                                "Connected as",
                            ],
                            prompt_text=f"We found these {component_type.value.replace('_', ' ')} "
                            "connected using the current service connector. Do you "
                            "want to create a new one or use existing one?",
                            default_choice="0",
                            allow_zero_be_a_new_object=True,
                        )
                else:
                    component_selected = None

                if component_selected is None:
                    component_info = _get_stack_component_info(
                        component_type=component_type.value,
                        cloud_provider=provider
                        or resources_info.connector_type,
                        resources_info=resources_info,
                        service_connector_index=0,
                    )
                    component_name = stack_name
                    created_objects.add(component_type.value)
                else:
                    selected_component = existing_components[
                        component_selected
                    ]
                    component_info = selected_component.id
                    component_name = selected_component.name

            components[component_type] = [component_info]
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
                components[component_type_] = [
                    client.get_stack_component(
                        component_type_, component_name_
                    ).id
                ]

        try:
            created_stack = client.zen_store.create_stack(
                stack=StackRequest(
                    user=client.active_user.id,
                    workspace=client.active_workspace.id,
                    name=stack_name,
                    components=components,
                    service_connectors=[service_connector]
                    if service_connector
                    else [],
                    labels=labels,
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
def describe_stack(stack_name_or_id: Optional[str] = None) -> None:
    """Show details about a named stack or the active stack.

    Args:
        stack_name_or_id: Name of the stack to describe.
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
            f"Active {scope} stack set to: '{client.active_stack_model.name}'"
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
) -> UUID:
    """Import a single stack component with given type/config.

    Args:
        component_type: The type of component to import.
        component_dict: Dict representation of the component to import.

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


def validate_name(ctx: click.Context, param: str, value: str) -> str:
    """Validate the name of the stack.

    Args:
        ctx: The click context.
        param: The parameter name.
        value: The value of the parameter.

    Returns:
        The validated value.

    Raises:
        BadParameter: If the name is invalid.
    """
    if not value:
        return value

    if not re.match(r"^[a-zA-Z0-9-]*$", value):
        raise click.BadParameter(
            "Stack name must contain only alphanumeric characters and hyphens."
        )

    if len(value) > 16:
        raise click.BadParameter(
            "Stack name must have a maximum length of 16 characters."
        )

    return value


@stack.command(
    help="""Deploy a fully functional ZenML stack in one of the cloud providers.

Running this command will initiate an assisted process that will walk you
through automatically provisioning all the cloud infrastructure resources
necessary for a fully functional ZenML stack in the cloud provider of your
choice. A corresponding ZenML stack will also be automatically registered along
with all the necessary components and properly authenticated through service
connectors.
"""
)
@click.option(
    "--provider",
    "-p",
    "provider",
    required=True,
    type=click.Choice(StackDeploymentProvider.values()),
)
@click.option(
    "--name",
    "-n",
    "stack_name",
    type=click.STRING,
    required=False,
    help="Custom string to use as a prefix to generate names for the ZenML "
    "stack, its components service connectors as well as provisioned cloud "
    "infrastructure resources. May only contain alphanumeric characters and "
    "hyphens and have a maximum length of 16 characters.",
    callback=validate_name,
)
@click.option(
    "--location",
    "-l",
    type=click.STRING,
    required=False,
    help="The location to deploy the stack to.",
)
@click.option(
    "--set",
    "set_stack",
    is_flag=True,
    help="Immediately set this stack as active.",
    type=click.BOOL,
)
@click.pass_context
def deploy(
    ctx: click.Context,
    provider: str,
    stack_name: Optional[str] = None,
    location: Optional[str] = None,
    set_stack: bool = False,
) -> None:
    """Deploy and register a fully functional cloud ZenML stack.

    Args:
        ctx: The click context.
        provider: The cloud provider to deploy the stack to.
        stack_name: A name for the ZenML stack that gets imported as a result
            of the recipe deployment.
        location: The location to deploy the stack to.
        set_stack: Immediately set the deployed stack as active.

    Raises:
        Abort: If the user aborts the deployment.
        KeyboardInterrupt: If the user interrupts the deployment.
    """
    stack_name = stack_name or f"zenml-{provider}-stack"

    # Set up the markdown renderer to use the old-school markdown heading
    Markdown.elements.update(
        {
            "heading_open": OldSchoolMarkdownHeading,
        }
    )

    client = Client()
    if client.zen_store.is_local_store():
        cli_utils.error(
            "This feature cannot be used with a local ZenML deployment. "
            "ZenML needs to be accessible from the cloud provider to allow the "
            "stack and its components to be registered automatically. "
            "Please deploy ZenML in a remote environment as described in the "
            "documentation: https://docs.zenml.io/getting-started/deploying-zenml "
            "or use a managed ZenML Pro server instance for quick access to "
            "this feature and more: https://www.zenml.io/pro"
        )

    with track_handler(
        event=AnalyticsEvent.DEPLOY_FULL_STACK,
    ) as analytics_handler:
        analytics_handler.metadata = {
            "provider": provider,
        }

        deployment = client.zen_store.get_stack_deployment_info(
            provider=StackDeploymentProvider(provider),
        )

        if location and location not in deployment.locations.values():
            cli_utils.error(
                f"Invalid location '{location}' for provider '{provider}'. "
                f"Valid locations are: {', '.join(deployment.locations.values())}"
            )

        console.print(
            Markdown(
                f"# {provider.upper()} ZenML Cloud Stack Deployment\n"
                + deployment.description
            )
        )
        console.print(Markdown("## Details\n" + deployment.instructions))

        deployment_config = client.zen_store.get_stack_deployment_config(
            provider=StackDeploymentProvider(provider),
            stack_name=stack_name,
            location=location,
        )

        if deployment_config.instructions:
            console.print(
                Markdown("## Instructions\n" + deployment_config.instructions),
                "\n",
            )

        if deployment_config.configuration:
            console.print(
                deployment_config.configuration,
                no_wrap=True,
                overflow="ignore",
                crop=False,
                style=Style(bgcolor="grey15"),
            )

        if not cli_utils.confirmation(
            "\n\nProceed to continue with the deployment. You will be "
            f"automatically redirected to "
            f"{deployment_config.deployment_url_text} in your browser.",
        ):
            raise click.Abort()

        date_start = datetime.utcnow()

        webbrowser.open(deployment_config.deployment_url)
        console.print(
            Markdown(
                f"If your browser did not open automatically, please open "
                f"the following URL into your browser to deploy the stack to "
                f"{provider.upper()}: "
                f"[{deployment_config.deployment_url_text}]"
                f"({deployment_config.deployment_url}).\n\n"
            )
        )

        try:
            cli_utils.declare(
                "\n\nWaiting for the deployment to complete and the stack to be "
                "registered. Press CTRL+C to abort...\n"
            )

            while True:
                deployed_stack = client.zen_store.get_stack_deployment_stack(
                    provider=StackDeploymentProvider(provider),
                    stack_name=stack_name,
                    location=location,
                    date_start=date_start,
                )
                if deployed_stack:
                    break
                time.sleep(10)

            analytics_handler.metadata.update(
                {
                    "stack_id": deployed_stack.stack.id,
                }
            )

        except KeyboardInterrupt:
            cli_utils.declare("Stack deployment aborted.")
            raise

    stack_desc = f"""## Stack successfully registered! 🚀
Stack [{deployed_stack.stack.name}]({get_stack_url(deployed_stack.stack)}):\n"""

    for component_type, components in deployed_stack.stack.components.items():
        if components:
            component = components[0]
            stack_desc += (
                f" * `{component.flavor_name}` {component_type.value}: "
                f"[{component.name}]({get_component_url(component)})\n"
            )

    if deployed_stack.service_connector:
        stack_desc += (
            f" * Service Connector: {deployed_stack.service_connector.name}\n"
        )

    console.print(Markdown(stack_desc))

    follow_up = f"""
## Follow-up

{deployment.post_deploy_instructions}

To use the `{deployed_stack.stack.name}` stack to run pipelines:

* install the required ZenML integrations by running: `zenml integration install {" ".join(deployment.integrations)}`
"""
    if set_stack:
        client.activate_stack(deployed_stack.stack.id)
        follow_up += f"""
* the `{deployed_stack.stack.name}` stack has already been set as active
"""
    else:
        follow_up += f"""
* set the `{deployed_stack.stack.name}` stack as active by running: `zenml stack set {deployed_stack.stack.name}`
"""

    console.print(
        Markdown(follow_up),
    )


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

    if cloud_provider not in {"aws", "gcp", "azure"}:
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
                required += f"[bold]{each_req}[/bold]  [italic]({field.get('title', 'no description')})[/italic]\n"
            choices.append([value.name, required])

        selected_auth_idx = cli_utils.multi_choice_prompt(
            object_type=f"authentication methods for {cloud_provider.upper()}",
            choices=choices,
            headers=headers,
            prompt_text="Please choose one of the authentication option above",
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
    resources_info: ServiceConnectorResourcesInfo,
    service_connector_index: Optional[int] = None,
) -> ComponentInfo:
    """Get a stack component info with given type and service connector.

    Args:
        component_type: The type of component to create.
        cloud_provider: The cloud provider to use.
        resources_info: The resources info of the service connector.
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

    flavor = "undefined"
    service_connector_resource_id = None
    config = {}
    choices = [
        [cri.flavor, resource_id]
        for cri in resources_info.components_resources_info[
            StackComponentType(component_type)
        ]
        for resource_id in cri.accessible_by_service_connector
    ]
    if component_type == "artifact_store":
        selected_storage_idx = cli_utils.multi_choice_prompt(
            object_type=f"{cloud_provider.upper()} storages",
            choices=choices,
            headers=["Artifact Store Type", "Storage"],
            prompt_text="Please choose one of the storages for the new artifact store:",
        )
        if selected_storage_idx is None:
            cli_utils.error("No storage selected.")

        selected_storage = choices[selected_storage_idx]

        flavor = selected_storage[0]
        config = {"path": selected_storage[1]}
        service_connector_resource_id = selected_storage[1]
    elif component_type == "orchestrator":

        def query_region(
            provider: StackDeploymentProvider,
            compute_type: str,
            is_skypilot: bool = False,
        ) -> str:
            deployment_info = Client().zen_store.get_stack_deployment_info(
                provider
            )
            region = Prompt.ask(
                f"Select the location for your {compute_type}:",
                choices=sorted(
                    deployment_info.skypilot_default_regions.values()
                    if is_skypilot
                    else deployment_info.locations.values()
                ),
                show_choices=True,
            )
            return region

        selected_orchestrator_idx = cli_utils.multi_choice_prompt(
            object_type=f"orchestrators on {cloud_provider.upper()}",
            choices=choices,
            headers=["Orchestrator Type", "Details"],
            prompt_text="Please choose one of the orchestrators for the new orchestrator:",
        )
        if selected_orchestrator_idx is None:
            cli_utils.error("No orchestrator selected.")

        selected_orchestrator = choices[selected_orchestrator_idx]

        config = {}
        flavor = selected_orchestrator[0]
        if flavor == "sagemaker":
            execution_role = Prompt.ask("Enter an execution role ARN:")
            config["execution_role"] = execution_role
        elif flavor == "vm_aws":
            config["region"] = selected_orchestrator[1]
        elif flavor == "vm_gcp":
            config["region"] = query_region(
                StackDeploymentProvider.GCP,
                "Skypilot cluster",
                is_skypilot=True,
            )
        elif flavor == "vm_azure":
            config["region"] = query_region(
                StackDeploymentProvider.AZURE,
                "Skypilot cluster",
                is_skypilot=True,
            )
        elif flavor == "azureml":
            config["subscription_id"] = Prompt.ask(
                "Enter the subscription ID:"
            )
            config["resource_group"] = Prompt.ask("Enter the resource group:")
            config["workspace"] = Prompt.ask("Enter the workspace name:")
        elif flavor == "vertex":
            config["location"] = query_region(
                StackDeploymentProvider.GCP, "Vertex AI job"
            )
        service_connector_resource_id = selected_orchestrator[1]
    elif component_type == "container_registry":
        selected_registry_idx = cli_utils.multi_choice_prompt(
            object_type=f"{cloud_provider.upper()} registries",
            choices=choices,
            headers=["Container Registry Type", "Container Registry"],
            prompt_text="Please choose one of the registries for the new container registry:",
        )
        if selected_registry_idx is None:
            cli_utils.error("No container registry selected.")
        selected_registry = choices[selected_registry_idx]
        flavor = selected_registry[0]
        config = {"uri": selected_registry[1]}
        service_connector_resource_id = selected_registry[1]
    else:
        raise ValueError(f"Unknown component type {component_type}")

    return ComponentInfo(
        flavor=flavor,
        configuration=config,
        service_connector_index=service_connector_index,
        service_connector_resource_id=service_connector_resource_id,
    )


@stack.command(
    name="export-requirements", help="Export the stack requirements."
)
@click.argument(
    "stack_name_or_id",
    type=click.STRING,
    required=False,
)
@click.option(
    "--output-file",
    "-o",
    "output_file",
    type=str,
    required=False,
    help="File to which to export the stack requirements. If not "
    "provided, the requirements will be printed to stdout instead.",
)
@click.option(
    "--overwrite",
    "-ov",
    "overwrite",
    type=bool,
    required=False,
    is_flag=True,
    help="Overwrite the output file if it already exists. This option is "
    "only valid if the output file is provided.",
)
def export_requirements(
    stack_name_or_id: Optional[str] = None,
    output_file: Optional[str] = None,
    overwrite: bool = False,
) -> None:
    """Exports stack requirements so they can be installed using pip.

    Args:
        stack_name_or_id: Stack name or ID. If not given, the active stack will
            be used.
        output_file: Optional path to the requirements output file.
        overwrite: Overwrite the output file if it already exists. This option
            is only valid if the output file is provided.
    """
    try:
        stack_model: "StackResponse" = Client().get_stack(
            name_id_or_prefix=stack_name_or_id
        )
    except KeyError as err:
        cli_utils.error(str(err))

    requirements, _ = requirements_utils.get_requirements_for_stack(
        stack_model
    )

    if not requirements:
        cli_utils.declare(f"Stack `{stack_model.name}` has no requirements.")
        return

    if output_file:
        try:
            with open(output_file, "x") as f:
                f.write("\n".join(requirements))
        except FileExistsError:
            if overwrite or cli_utils.confirmation(
                "A file already exists at the specified path. "
                "Would you like to overwrite it?"
            ):
                with open(output_file, "w") as f:
                    f.write("\n".join(requirements))
        cli_utils.declare(
            f"Requirements for stack `{stack_model.name}` exported to {output_file}."
        )
    else:
        click.echo(" ".join(requirements), nl=False)
