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
"""Utils for schemas."""

import math
from typing import List, Type, TypeVar

from zenml.models.v2.base.base import BaseResponse
from zenml.models.v2.base.page import Page
from zenml.zen_stores.schemas.base_schemas import BaseSchema

S = TypeVar("S", bound=BaseSchema)


def get_page_from_list(
    items_list: List[S],
    response_model: Type[BaseResponse],  # type: ignore[type-arg]
    size: int = 5,
    page: int = 1,
    include_resources: bool = False,
    include_metadata: bool = False,
) -> Page[BaseResponse]:  # type: ignore[type-arg]
    """Converts list of schemas into page of response models.

    Args:
        items_list: List of schemas
        response_model: Response model
        size: Page size
        page: Page number
        include_metadata: Whether metadata should be included in response models
        include_resources: Whether resources should be included in response models

    Returns:
        A page of list items.
    """
    total = len(items_list)
    if total == 0:
        total_pages = 1
    else:
        total_pages = math.ceil(total / size)

    start = (page - 1) * size
    end = start + size

    page_items = [
        item.to_model(
            include_metadata=include_metadata,
            include_resources=include_resources,
        )
        for item in items_list[start:end]
    ]
    return Page[response_model](  # type: ignore[valid-type]
        index=page,
        max_size=size,
        total_pages=total_pages,
        total=total,
        items=page_items,
    )
