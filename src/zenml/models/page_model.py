# MIT License
#
# Copyright (c) 2020 Yurii Karabas
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
"""Model implementation for easy pagination for Lists of ZenML Domain Models.

The code contained within this file has been inspired by the
fastapi-pagination library: https://github.com/uriyyo/fastapi-pagination
"""
from typing import Generator, Generic, List, TypeVar

from pydantic import SecretStr
from pydantic.generics import GenericModel
from pydantic.types import NonNegativeInt, PositiveInt

from zenml.models.base_models import BaseResponseModel
from zenml.models.filter_models import BaseFilterModel

B = TypeVar("B", bound=BaseResponseModel)


class Page(GenericModel, Generic[B]):
    """Return Model for List Models to accommodate pagination."""

    index: PositiveInt
    max_size: PositiveInt
    total_pages: NonNegativeInt
    total: NonNegativeInt
    items: List[B]

    __params_type__ = BaseFilterModel

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

    class Config:
        """Pydantic configuration class."""

        # This is needed to allow the REST API server to unpack SecretStr
        # values correctly before sending them to the client.
        json_encoders = {
            SecretStr: lambda v: v.get_secret_value() if v else None
        }
