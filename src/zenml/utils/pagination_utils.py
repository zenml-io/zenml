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
"""Pagination utilities."""

from typing import Callable, List, TypeVar

from zenml.models import BaseIdentifiedResponse, Page

AnyResponse = TypeVar("AnyResponse", bound=BaseIdentifiedResponse)  # type: ignore[type-arg]


def depaginate(
    list_method: Callable[..., Page[AnyResponse]],
) -> List[AnyResponse]:
    """Depaginate the results from a client or store method that returns pages.

    Args:
        list_method: The list method to wrap around.

    Returns:
        A list of the corresponding Response Models.
    """
    page = list_method()
    items = list(page.items)
    while page.index < page.total_pages:
        page = list_method(page=page.index + 1)
        items += list(page.items)

    return items
