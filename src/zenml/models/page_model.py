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

The code contained within this file has been heavily inspired by the
fastapi-pagination library: https://github.com/uriyyo/fastapi-pagination
"""
from __future__ import annotations

import math
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Generic, List, Optional, Sequence, TypeVar, Union

from fastapi import Query
from pydantic import BaseModel
from pydantic.generics import GenericModel
from pydantic.types import conint
from sqlalchemy.orm import noload
from sqlmodel import Session, func, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from zenml.models.base_models import BaseResponseModel
from zenml.models.filter_models import FilterBaseModel
from zenml.zen_stores.schemas.base_schemas import BaseSchema

T = TypeVar("T", bound=BaseSchema)
B = TypeVar("B", bound=BaseResponseModel)


class Page(GenericModel, Generic[B]):
    page: conint(ge=1)  # type: ignore
    size: conint(ge=1)  # type: ignore
    total_pages: conint(ge=0)  # type: ignore
    total: conint(ge=0)  # type: ignore
    items: Sequence[B]

    class Config:
        extra = "allow"

    __params_type__ = FilterBaseModel

    @classmethod
    def create(
        cls,
        items: Sequence[B],
        total: int,
        total_pages: int,
        filter_model: FilterBaseModel,
    ) -> Page[B]:

        if not isinstance(filter_model, FilterBaseModel):
            raise ValueError("Page should be used with filter models")

        return cls(
            total=total,
            total_pages=total_pages,
            items=items,
            page=filter_model.page,
            size=filter_model.size,
        )
