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
import traceback
from typing import TYPE_CHECKING, Optional

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.logger import get_logger
from zenml.models import (
    ExceptionInfo,
)

if TYPE_CHECKING:
    from zenml.steps import BaseStep

logger = get_logger(__name__)


def collect_exception_information(
    exception: BaseException, step_instance: Optional["BaseStep"] = None
) -> ExceptionInfo:
    """Collects the exception information.

    Args:
        exception: The exception to collect information from.
        step_instance: The step instance that is currently running.

    Returns:
        The exception information.
    """
    tb = traceback.format_tb(exception.__traceback__)
    line_number = None
    start_index = None

    if step_instance and (
        source_file := inspect.getsourcefile(step_instance.entrypoint)
    ):
        try:
            source_file = os.path.abspath(source_file)

            lines, start_line = inspect.getsourcelines(
                step_instance.entrypoint
            )
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
            logger.debug("Failed to detect step code line: %s", e)

    if start_index is not None:
        # If the code failed while executing user code, we remove the initial
        # part of the traceback that is happening in the ZenML code.
        tb = tb[start_index:]

    tb_bytes = "\n".join(tb).encode()
    tb_bytes = tb_bytes[:MEDIUMTEXT_MAX_LENGTH]

    return ExceptionInfo(
        # Ignore errors when decoding in case we cut off in the middle of an
        # encoded character.
        traceback=tb_bytes.decode(errors="ignore"),
        step_code_line=line_number,
    )
