#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Module for centralized WarningController implementation."""

import logging
from collections import Counter
from typing import Any

from zenml.enums import LoggingLevels
from zenml.utils.singleton import SingletonMetaClass
from zenml.utils.warnings.base import WarningConfig, WarningVerbosity
from zenml.utils.warnings.registry import WarningCodes

logger = logging.getLogger(__name__)


class WarningController(metaclass=SingletonMetaClass):
    """Class responsible for centralized handling of warning messages."""

    def __init__(self) -> None:
        """WarningController constructor."""
        self._warning_configs: dict[str, WarningConfig] = {}
        self._warning_statistics: dict[str, int] = Counter()

    def register(self, warning_configs: dict[str, WarningConfig]) -> None:
        """Register a warning config collection to the controller.

        Args:
            warning_configs: Configs to be registered. Key should be the warning code.
        """
        self._warning_configs.update(warning_configs)

    @staticmethod
    def _resolve_call_details() -> tuple[str, int]:
        import inspect

        frame = inspect.stack()[3]  # public methods -> _log -> _resolve
        module = inspect.getmodule(frame[0])
        module_name = module.__name__ if module else "<unknown module>"
        line_number = frame.lineno

        return module_name, line_number

    @staticmethod
    def _get_display_message(
        message: str,
        module_name: str,
        line_number: int,
        config: WarningConfig,
    ) -> str:
        """Helper method to build the warning message string.

        Args:
            message: The warning message.
            module_name: The module that the warning call originated from.
            line_number: The line number that the warning call originated from.
            config: The warning configuration.

        Returns:
            A warning message containing extra fields/info based on warning config.
        """
        display = f"[{config.code}]({config.category}) - {message}"

        if config.verbosity == WarningVerbosity.MEDIUM:
            display = f"{module_name}:{line_number} {display}"

        if config.verbosity == WarningVerbosity.HIGH:
            display = f"{display}\n{config.description}"

        return display

    def _log(
        self,
        warning_code: WarningCodes,
        message: str,
        level: LoggingLevels,
        **kwargs: dict[str, Any],
    ) -> None:
        """Core function for warning handling.

        Args:
            warning_code: The code of the warning configuration.
            message: The warning message.
            level: The level of the warning.
            **kwargs: Keyword arguments (for formatted messages).

        """
        warning_config = self._warning_configs.get(warning_code)

        # resolves the module and line number of the warning call.
        module_name, line_number = self._resolve_call_details()

        if not warning_config:
            # If no config is available just follow default behavior:
            logger.warning(f"{module_name}:{line_number} - {message}")
            return

        if warning_config.is_throttled:
            if warning_code in self._warning_statistics:
                # Throttled code has already appeared - skip.
                return

        display_message = self._get_display_message(
            message=message,
            module_name=module_name,
            line_number=line_number,
            config=warning_config,
        )

        self._warning_statistics[warning_code] += 1

        if level == LoggingLevels.INFO:
            logger.info(display_message.format(**kwargs))
        else:
            # Assumes warning level is the default if an invalid option is passed.
            logger.warning(display_message.format(**kwargs))

    def warn(
        self, *, warning_code: WarningCodes, message: str, **kwargs: Any
    ) -> None:
        """Method to execute warning handling logic with warning log level.

        Args:
            warning_code: The code of the warning (see WarningCodes enum)
            message: The message to display.
            **kwargs: Keyword arguments (for formatted messages).
        """
        self._log(warning_code, message, LoggingLevels.WARNING, **kwargs)

    def info(
        self, *, warning_code: WarningCodes, message: str, **kwargs: Any
    ) -> None:
        """Method to execute warning handling logic with info log level.

        Args:
            warning_code: The code of the warning (see WarningCodes enum)
            message: The message to display.
            **kwargs: Keyword arguments (for formatted messages).
        """
        self._log(warning_code, message, LoggingLevels.INFO, **kwargs)

    @staticmethod
    def create() -> "WarningController":
        """Factory function for WarningController.

        Creates a new warning controller and registers system warning configs.

        Returns:
            A warning controller instance.
        """
        from zenml.utils.warnings.registry import WARNING_CONFIG_REGISTRY

        registry = WarningController()

        registry.register(warning_configs=WARNING_CONFIG_REGISTRY)

        return registry
