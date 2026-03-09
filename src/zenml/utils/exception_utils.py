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
"""Exception utilities."""

import inspect
import os
import re
import textwrap
import traceback
from typing import Any, Callable, Optional, Type

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.logger import get_logger
from zenml.models import (
    ExceptionInfo,
)
from zenml.utils import source_utils

logger = get_logger(__name__)


def collect_exception_information(
    exception: BaseException, user_func: Optional[Callable[..., Any]] = None
) -> ExceptionInfo:
    """Collects the exception information.

    Args:
        exception: The exception to collect information from.
        user_func: The user function that was called.

    Returns:
        The exception information.
    """
    tb = traceback.format_tb(exception.__traceback__)
    line_number = None
    start_index = None

    if user_func and (source_file := inspect.getsourcefile(user_func)):
        try:
            source_file = os.path.abspath(source_file)

            lines, start_line = inspect.getsourcelines(user_func)
            end_line = start_line + len(lines)

            line_pattern = re.compile(
                rf'File "{re.escape(source_file)}", line (\d+),'
            )

            for index, line in enumerate(tb):
                match = line_pattern.search(line)
                if match:
                    potential_line_number = int(match.group(1))
                    if (
                        potential_line_number >= start_line
                        and potential_line_number <= end_line
                    ):
                        line_number = potential_line_number - start_line
                        start_index = index
                        break
        except Exception as e:
            logger.debug("Failed to detect code line: %s", e)

    if start_index is not None:
        # If the code failed while executing user code, we remove the initial
        # part of the traceback that is happening in the ZenML code.
        tb = tb[start_index:]

    tb_bytes = textwrap.dedent("\n".join(tb)).encode()
    tb_bytes = tb_bytes[:MEDIUMTEXT_MAX_LENGTH]

    source = None
    try:
        source = source_utils.resolve(type(exception)).import_path
    except Exception as e:
        logger.debug("Failed to resolve exception source: %s", e)

    message = str(exception) if str(exception) else None

    return ExceptionInfo(
        # Ignore errors when decoding in case we cut off in the middle of an
        # encoded character.
        traceback=tb_bytes.decode(errors="ignore"),
        source=source,
        message=message,
        user_code_line=line_number,
    )


def reconstruct_exception(
    exception_info: Optional[ExceptionInfo], fallback_message: str
) -> BaseException:
    """Reconstruct an exception.

    Args:
        exception_info: Exception information.
        fallback_message: Message to use if the exception cannot be
            reconstructed.

    Returns:
        The reconstructed exception if possible, otherwise a RuntimeError.
    """
    if not exception_info:
        return RuntimeError(fallback_message)

    message = exception_info.message or fallback_message
    source = exception_info.source
    if not source:
        return RuntimeError(message)

    try:
        exception_class: Type[BaseException] = (
            source_utils.load_and_validate_class(
                source=source, expected_class=BaseException
            )
        )
    except Exception as e:
        logger.warning("Failed to load exception source `%s`: %s", source, e)
        return RuntimeError(message)

    try:
        return exception_class(message)
    except Exception as e:
        logger.warning(
            "Failed to instantiate exception `%s` with message `%s`: %s",
            source,
            message,
            e,
        )
        try:
            return exception_class()
        except Exception as e:
            logger.warning(
                "Failed to instantiate exception `%s` without args: %s",
                source,
                e,
            )
            return RuntimeError(message)
