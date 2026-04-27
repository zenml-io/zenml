#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Tests for ZenML logger behavior."""

import builtins
import logging
from typing import Any

from zenml import logger as logger_module


def test_zenml_logging_handler_reports_non_circular_import_errors(
    mocker: Any,
) -> None:
    """Tests genuine logging utility import errors are surfaced."""
    original_import = builtins.__import__

    def fail_logging_utils_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "zenml.utils.logging_utils":
            raise RuntimeError("unexpected import failure")

        return original_import(name, *args, **kwargs)

    handler = logger_module.ZenMLLoggingHandler()
    handle_error_mock = mocker.patch.object(handler, "handleError")
    mocker.patch.object(builtins, "__import__", fail_logging_utils_import)

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="message",
        args=(),
        exc_info=None,
    )

    handler.emit(record)

    handle_error_mock.assert_called_once_with(record)


def test_zenml_logging_handler_suppresses_circular_import_errors(
    mocker: Any,
) -> None:
    """Tests logger keeps suppressing import-cycle initialization failures."""
    original_import = builtins.__import__

    def fail_logging_utils_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "zenml.utils.logging_utils":
            raise ImportError(
                "cannot import name 'LoggingContext' from partially "
                "initialized module"
            )

        return original_import(name, *args, **kwargs)

    handler = logger_module.ZenMLLoggingHandler()
    handle_error_mock = mocker.patch.object(handler, "handleError")
    mocker.patch.object(
        logger_module,
        "_is_logging_utils_circular_import_error",
        return_value=True,
    )
    mocker.patch.object(builtins, "__import__", fail_logging_utils_import)

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="message",
        args=(),
        exc_info=None,
    )

    handler.emit(record)

    handle_error_mock.assert_not_called()
