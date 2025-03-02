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
"""Utilities for stack."""

import contextlib
from typing import (
    TYPE_CHECKING,
    Iterator,
    Union,
)

if TYPE_CHECKING:
    from uuid import UUID

    from zenml.stack import Stack


@contextlib.contextmanager
def temporary_active_stack(
    stack_name_or_id: Union["UUID", str, None] = None,
) -> Iterator["Stack"]:
    """Contextmanager to temporarily activate a stack.

    Args:
        stack_name_or_id: The name or ID of the stack to activate. If not given,
            this contextmanager will not do anything.

    Yields:
        The active stack.
    """
    from zenml.client import Client

    try:
        if stack_name_or_id:
            old_stack_id = Client().active_stack_model.id
            Client().activate_stack(stack_name_or_id)
        else:
            old_stack_id = None
        yield Client().active_stack
    finally:
        if old_stack_id:
            Client().activate_stack(old_stack_id)
