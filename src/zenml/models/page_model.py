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
from __future__ import annotations

from typing import Generic, Sequence, TypeVar

from pydantic.generics import GenericModel
from pydantic.types import NonNegativeInt, PositiveInt

from zenml.models.base_models import BaseResponseModel
from zenml.models.filter_models import BaseFilterModel

B = TypeVar("B", bound=BaseResponseModel)


class Page(GenericModel, Generic[B]):
    """Return Model for List Models to accommodate pagination."""

    page: PositiveInt

    # TODO: this should be called max_size or max_items instead, and size should
    # return the actual size of the page (len(self.items))
    size: PositiveInt
    total_pages: NonNegativeInt
    total: NonNegativeInt
    items: Sequence[B]

    __params_type__ = BaseFilterModel

    def __len__(self) -> int:
        """Return the length of the page."""
        return len(self.items)

    def __getitem__(self, index: int) -> B:
        """Return the item at the given index."""
        return self.items[index]

    def __contains__(self, item: B) -> bool:
        """Returns whether the page contains a specific item."""
        return item in self.items
