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

from zenml.models.base_models import BaseResponseModel, ListBaseModel
from zenml.zen_stores.schemas.base_schemas import BaseSchema

T = TypeVar("T", bound=BaseSchema)
B = TypeVar("B", bound=BaseResponseModel)


@dataclass
class RawParams:
    limit: int
    offset: int


class Params(BaseModel):
    page: int = Query(1, ge=1, description="Page number")
    size: int = Query(50, ge=1, le=100, description="Page size")

    def to_raw_params(self) -> RawParams:
        return RawParams(
            limit=self.size,
            offset=self.size * (self.page - 1),
        )


params_value: ContextVar[Params] = ContextVar("params_value")


def resolve_params(params: Optional[Params] = None) -> Params:
    if params is None:
        try:
            return params_value.get()
        except LookupError:
            raise RuntimeError("Use params or add_pagination")

    return params


class Page(GenericModel, Generic[B]):
    page: conint(ge=1)  # type: ignore
    size: conint(ge=1)  # type: ignore
    total_pages: conint(ge=0)  # type: ignore
    total: conint(ge=0)  # type: ignore
    items: Sequence[B]

    __params_type__ = ListBaseModel

    @classmethod
    def create(
        cls,
        items: Sequence[B],
        total: int,
        total_pages: int,
        params: ListBaseModel,
    ) -> Page[B]:

        if not isinstance(params, ListBaseModel):
            raise ValueError("Page should be used with Params")

        return cls(
            total=total,
            total_pages=total_pages,
            items=items,
            page=params.page,
            size=params.size,
        )

    @classmethod
    def paginate(
        cls,
        session: Session,
        query: Union[T, Select[T], SelectOfScalar[T]],
        params: Optional[Params] = None,
    ) -> Page[B]:
        """Given a query, select the range defined in params and return a Page instance with a list of Domain Models.

        Args:
            session: The SQLModel Session
            query: The query to execute
            params: The params to use for pagination

        Returns:
            The Domain Model representation of the DB resource
        """
        params = resolve_params(params)
        raw_params = params.get_pagination_params()

        if not isinstance(query, (Select, SelectOfScalar)):
            query = select(query)

        total = session.scalar(
            select(func.count("*")).select_from(
                query.order_by(None).options(noload("*")).subquery()
            )
        )

        total_pages = math.ceil(total / raw_params.limit)

        items: List[T] = (
            session.exec(
                query.limit(raw_params.limit).offset(raw_params.offset)
            )
            .unique()
            .all()
        )

        items: List[B] = [i.to_model() for i in items]

        return cls.create(items, total, total_pages, params)

