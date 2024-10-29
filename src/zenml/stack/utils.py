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
"""Util functions for handling stacks, components, and flavors."""

from typing import Any, Dict, Optional, Type

from zenml.client import Client
from zenml.enums import StackComponentType, StoreType
from zenml.logger import get_logger
from zenml.models import FlavorFilter, FlavorResponse
from zenml.stack.flavor import Flavor
from zenml.stack.stack_component import StackComponentConfig
from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)


def validate_stack_component_config(
    configuration_dict: Dict[str, Any],
    flavor_name: str,
    component_type: StackComponentType,
    zen_store: Optional[BaseZenStore] = None,
    validate_custom_flavors: bool = True,
) -> Optional[StackComponentConfig]:
    """Validate the configuration of a stack component.

    Args:
        configuration_dict: The stack component configuration to validate.
        flavor_name: The name of the flavor of the stack component.
        component_type: The type of the stack component.
        zen_store: An optional ZenStore in which to look for the flavor. If not
            provided, the flavor will be fetched via the regular ZenML Client.
            This is mainly useful for checks running inside the ZenML server.
        validate_custom_flavors: When loading custom flavors from the local
            environment, this flag decides whether the import failures are
            raised or an empty value is returned.

    Returns:
        The validated stack component configuration or None, if the
        flavor is a custom flavor that could not be imported from the local
        environment and the `validate_custom_flavors` flag is set to False.

    Raises:
        ValueError: If the configuration is invalid.
        ImportError: If the flavor class could not be imported.
        ModuleNotFoundError: If the flavor class could not be imported.
    """
    if zen_store:
        flavor_model = get_flavor_by_name_and_type_from_zen_store(
            zen_store=zen_store,
            flavor_name=flavor_name,
            component_type=component_type,
        )
    else:
        flavor_model = Client().get_flavor_by_name_and_type(
            name=flavor_name,
            component_type=component_type,
        )
    try:
        flavor_class = Flavor.from_model(flavor_model)
    except (ImportError, ModuleNotFoundError):
        # The flavor class couldn't be loaded.
        if flavor_model.is_custom and not validate_custom_flavors:
            return None
        raise

    config_class = flavor_class.config_class
    # Make sure extras are forbidden for the config class. Due to inheritance
    # order, some config classes allow extras by accident which we patch here.
    validation_config_class: Type[StackComponentConfig] = type(
        config_class.__name__,
        (config_class,),
        {"model_config": {"extra": "forbid"}},
    )
    configuration = validation_config_class(**configuration_dict)

    if not configuration.is_valid:
        raise ValueError(
            f"Invalid stack component configuration. Please verify "
            f"the configurations set for {component_type}."
        )
    return configuration


def warn_if_config_server_mismatch(
    configuration: StackComponentConfig,
) -> None:
    """Warn if a component configuration is mismatched with the ZenML server.

    Args:
        configuration: The component configuration to check.
    """
    zen_store = Client().zen_store
    if configuration.is_remote and zen_store.is_local_store():
        if zen_store.type == StoreType.REST:
            logger.warning(
                "You are configuring a stack component that is running "
                "remotely while using a local ZenML server. The component "
                "may not be able to reach the local ZenML server and will "
                "therefore not be functional. Please consider deploying "
                "and/or using a remote ZenML server instead."
            )
        else:
            logger.warning(
                "You are configuring a stack component that is running "
                "remotely while connected to the local database. The component "
                "will not be able to reach the local database and will "
                "therefore not be functional. Please consider deploying "
                "and/or using a remote ZenML server instead."
            )
    elif configuration.is_local and not zen_store.is_local_store():
        logger.warning(
            "You are configuring a stack component that is using "
            "local resources while connected to a remote ZenML server. The "
            "stack component may not be usable from other hosts or by "
            "other users. You should consider using a non-local stack "
            "component alternative instead."
        )


def get_flavor_by_name_and_type_from_zen_store(
    zen_store: BaseZenStore,
    flavor_name: str,
    component_type: StackComponentType,
) -> FlavorResponse:
    """Get a stack component flavor by name and type from a ZenStore.

    Args:
        zen_store: The ZenStore to query.
        flavor_name: The name of a stack component flavor.
        component_type: The type of the stack component.

    Returns:
        The flavor model.

    Raises:
        KeyError: If no flavor with the given name and type exists.
    """
    flavors = zen_store.list_flavors(
        FlavorFilter(name=flavor_name, type=component_type)
    )
    if not flavors:
        raise KeyError(
            f"No flavor with name '{flavor_name}' and type "
            f"'{component_type}' exists."
        )
    return flavors[0]
