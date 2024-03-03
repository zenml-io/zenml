#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Class for resolving settings."""

from typing import TYPE_CHECKING, Type, TypeVar

from pydantic import ValidationError

from zenml.exceptions import SettingsResolvingError
from zenml.utils import settings_utils

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.stack import Stack

    T = TypeVar("T", bound="BaseSettings")


class SettingsResolver:
    """Class for resolving settings.

    This class converts a `BaseSettings` instance to the correct subclass
    depending on the key for which these settings were specified.
    """

    def __init__(self, key: str, settings: "BaseSettings"):
        """Checks if the settings key is valid.

        Args:
            key: Settings key.
            settings: The settings.

        Raises:
            ValueError: If the settings key is invalid.
        """
        if not settings_utils.is_valid_setting_key(key):
            raise ValueError(
                f"Invalid setting key `{key}`. Setting keys can either refer "
                "to general settings (available keys: "
                f"{set(settings_utils.get_general_settings())}) or stack "
                "component specific settings. Stack component specific keys "
                "are of the format "
                "`<STACK_COMPONENT_TYPE>.<STACK_COMPONENT_FLAVOR>`."
            )

        self._key = key
        self._settings = settings

    def resolve(self, stack: "Stack") -> "BaseSettings":
        """Resolves settings for the given stack.

        Args:
            stack: The stack for which to resolve the settings.

        Returns:
            The resolved settings.
        """
        if settings_utils.is_general_setting_key(self._key):
            target_class = self._resolve_general_settings_class()
        else:
            target_class = self._resolve_stack_component_setting_class(
                stack=stack
            )

        return self._convert_settings(target_class=target_class)

    def _resolve_general_settings_class(
        self,
    ) -> Type["BaseSettings"]:
        """Resolves general settings.

        Returns:
            The resolved settings.
        """
        return settings_utils.get_general_settings()[self._key]

    def _resolve_stack_component_setting_class(
        self, stack: "Stack"
    ) -> Type["BaseSettings"]:
        """Resolves stack component settings with the given stack.

        Args:
            stack: The stack to use for resolving.

        Raises:
            KeyError: If the stack contains no settings for the key.

        Returns:
            The resolved settings.
        """
        settings_class = stack.setting_classes.get(self._key)
        if not settings_class:
            raise KeyError(
                f"Failed to resolve settings for key {self._key}: "
                "No settings for this key exist in the stack. "
                "Available settings: "
                f"{set(stack.setting_classes)}"
            )

        return settings_class

    def _convert_settings(self, target_class: Type["T"]) -> "T":
        """Converts the settings to their correct class.

        Args:
            target_class: The correct settings class.

        Raises:
            SettingsResolvingError: If the conversion failed.

        Returns:
            The converted settings.
        """
        settings_dict = self._settings.dict()
        try:
            return target_class(**settings_dict)
        except ValidationError:
            raise SettingsResolvingError(
                f"Failed to convert settings `{settings_dict}` to expected "
                f"class {target_class}."
            )
