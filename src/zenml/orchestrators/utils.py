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
"""Utility functions for the orchestrator."""

from typing import TYPE_CHECKING, Optional

from tfx.orchestration.portable import data_types

from zenml.logger import get_logger

if TYPE_CHECKING:
    pass


logger = get_logger(__name__)


def get_cache_status(
    execution_info: Optional[data_types.ExecutionInfo],
) -> bool:
    """Returns whether a cached execution was used or not.

    Args:
        execution_info: The execution info.

    Returns:
        `True` if the execution was cached, `False` otherwise.
    """
    # An execution output URI is only provided if the step needs to be
    # executed (= is not cached)
    if execution_info and execution_info.execution_output_uri is None:
        return True
    else:
        return False
