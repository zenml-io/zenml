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
"""Page model definitions."""

from typing import Generator, Generic, List, TypeVar

from pydantic import BaseModel
from pydantic.types import NonNegativeInt, PositiveInt

from zenml.models.v2.base.base import BaseResponse
from zenml.models.v2.base.filter import BaseFilter

B = TypeVar("B", bound=BaseResponse)  # type: ignore[type-arg]


class Page(BaseModel, Generic[B]):
    """Return Model for List Models to accommodate pagination."""

    index: PositiveInt
    max_size: PositiveInt
    total_pages: NonNegativeInt
    total: NonNegativeInt
    items: List[B]

    __params_type__ = BaseFilter

    @property
    def size(self) -> int:
        """Return the item count of the page.

        Returns:
            The amount of items in the page.
        """
        return len(self.items)

    def __len__(self) -> int:
        """Return the item count of the page.

        This enables `len(page)`.

        Returns:
            The amount of items in the page.
        """
        return len(self.items)

    def __getitem__(self, index: int) -> B:
        """Return the item at the given index.

        This enables `page[index]`.

        Args:
            index: The index to get the item from.

        Returns:
            The item at the given index.
        """
        return self.items[index]

    def __iter__(self) -> Generator[B, None, None]:  # type: ignore[override]
        """Return an iterator over the items in the page.

        This enables `for item in page` loops, but breaks `dict(page)`.

        Yields:
            An iterator over the items in the page.
        """
        for item in self.items.__iter__():
            yield item

    def __contains__(self, item: B) -> bool:
        """Returns whether the page contains a specific item.

        This enables `item in page` checks.

        Args:
            item: The item to check for.

        Returns:
            Whether the item is in the page.
        """
        return item in self.items
