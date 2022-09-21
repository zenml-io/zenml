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
    """Class for resolving settings."""

    def __init__(self, key: str, options: "BaseSettings"):
        """Checks if the settings key is valid.

        Args:
            key: settings key.
            options: The settings.

        Raises:
            SettingsResolvingError: If the settings key is invalid.
        """
        if not settings_utils.is_valid_setting_key(key):
            raise SettingsResolvingError(f"Invalid settings key: {key}.")

        self._key = key
        self._options = options

    def resolve(self, stack: "Stack") -> "BaseSettings":
        """Resolves settings for the given stack.

        Args:
            stack: The stack for which to resolve the settings.

        Returns:
            The resolved settings.
        """
        if settings_utils.is_universal_setting_key(self._key):
            target_class = self._resolve_universal_settings_class()
        else:
            target_class = self._resolve_stack_component_setting_class(
                stack=stack
            )

        return self._convert_settings(target_class=target_class)

    def _resolve_universal_settings_class(
        self,
    ) -> Type["BaseSettings"]:
        """Resolves universal settings.

        Returns:
            The resolved settings.
        """
        return settings_utils.get_universal_settings()[self._key]

    def _resolve_stack_component_setting_class(
        self, stack: "Stack"
    ) -> Type["BaseSettings"]:
        """Resolves stack component settings with the given stack.

        Args:
            stack: The stack to use for resolving.

        Raises:
            SettingsResolvingError: If the resolving failed.

        Returns:
            The resolved settings.
        """
        settings_class = stack.setting_classes.get(self._key)
        if not settings_class:
            raise SettingsResolvingError(
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
        options_dict = self._options.dict()
        try:
            return target_class(**options_dict)
        except ValidationError:
            raise SettingsResolvingError(
                f"Failed to convert options `{options_dict}` to expected class "
                f"{target_class}."
            )
