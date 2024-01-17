#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Base implementation of the event source configuration."""
from abc import ABC
from typing import Any, ClassVar, Dict, Tuple, Type, cast

from pydantic import BaseModel, Extra

from zenml.actions.action_flavor_registry import action_flavor_registry


class ActionPlanConfig(BaseModel, ABC):
    """Allows configuring the action configuration."""

    class Config:
        """Pydantic configuration class."""

        # public attributes are immutable
        allow_mutation = False
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True
        # prevent extra attributes during model initialization
        extra = Extra.forbid


class BaseActionFlavorMeta(type):
    """Metaclass responsible for registering different `BaseActionFlavor` subclasses."""

    def __new__(
        mcs, name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any]
    ) -> "BaseActionFlavor":
        """Creates a ActionConfiguration class and registers it at the `ActionConfigurationRegistry`.

        Args:
            name: The name of the class.
            bases: The base classes of the class.
            dct: The dictionary of the class.

        Returns:
            The BaseMaterializerMeta class.

        Raises:
            MaterializerInterfaceError: If the class was improperly defined.
        """
        cls = cast(
            Type["BaseActionFlavor"], super().__new__(mcs, name, bases, dct)
        )

        # Skip the following validation and registration for base classes.
        if cls.SKIP_REGISTRATION:
            # Reset the flag so subclasses don't have it set automatically.
            cls.SKIP_REGISTRATION = False
            return cls

        # TODO: Validate that the class is properly defined.

        # Register the action configuration.
        action_flavor_registry.register_action_flavor(cls.EVENT_FLAVOR, cls)

        return cls


class BaseActionFlavor(metaclass=BaseActionFlavorMeta):
    """Base Action Flavor to register Action Plan Configurations."""

    ACTION_FLAVOR: ClassVar[str]

    # `SKIP_REGISTRATION` can be set to True to not register the class
    # in the event source configuration registry. This is primarily useful
    # for defining base classes. Subclasses will automatically have this
    # set to False unless they override it themselves.
    SKIP_REGISTRATION: ClassVar[bool] = True

    config: ActionPlanConfig
