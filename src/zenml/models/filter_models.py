from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Type, Dict, TypeVar
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, validator, root_validator
from sqlmodel import SQLModel

from zenml.utils.enum_utils import StrEnum


# ------------------ #
# QUERY PARAM MODELS #
# ------------------ #


@dataclass
class RawParams:
    limit: int
    offset: int


class GenericFilterOps(StrEnum):
    """Ops for all filters for string values on list methods"""

    EQUALS = "equals"
    CONTAINS = "contains"
    GTE = "gte"
    GT = "gt"
    LTE = "lte"
    LT = "lt"


class Filter(BaseModel):
    operation: GenericFilterOps
    value: str

    def generate_query_condition(
        self,
        table: Type[SQLModel],
        column: str,
    ):
        if self.operation == GenericFilterOps.EQUALS:
            return getattr(table, column) == self.value
        elif self.operation == GenericFilterOps.CONTAINS:
            return getattr(table, column).like(f'%{self.value}%')
        elif self.operation == GenericFilterOps.GTE:
            return getattr(table, column) >= self.value
        elif self.operation == GenericFilterOps.GT:
            return getattr(table, column) > self.value
        elif self.operation == GenericFilterOps.LTE:
            return getattr(table, column) <= self.value
        elif self.operation == GenericFilterOps.LT:
            return getattr(table, column) < self.value


class ListBaseModel(BaseModel):
    """Class to unify all filter, paginate and sort request parameters in one place.

    """
    dict_of_filters: Dict[str, Filter] = {}
    sort_by: str = Query("created")

    page: int = Query(1, ge=1, description="Page number")
    size: int = Query(50, ge=1, le=100, description="Page size")

    id: UUID = Query(None, description="Id for this resource")
    created: datetime = Query(None, description="Created")
    updated: datetime = Query(None, description="Updated")

    def get_pagination_params(self) -> RawParams:
        return RawParams(
            limit=self.size,
            offset=self.size * (self.page - 1),
        )

    @validator("sort_by", pre=True)
    def sort_column(cls, v):
        if v in ["sort_by", "dict_of_filters", "page", "size"]:
            raise ValueError(
                f"This resource can not be sorted by this field: '{v}'"
            )
        elif v in cls.__fields__:
            return v
        else:
            raise ValueError(
                "You can only sort by valid fields of this resource"
            )

    @root_validator()
    def interpret_filter_operations(cls, values):
        values["dict_of_filters"] = {}

        for key, value in values.items():
            if key not in ["sort_by", "dict_of_filters", "page", "size"] and value:
                if isinstance(value, str):
                    for op in GenericFilterOps.values():
                        if value.startswith(f"{op}:"):
                            values["dict_of_filters"][key] = Filter(
                                operation=op, value=value.lstrip(op)
                            )
                    else:
                        values["dict_of_filters"][key] = Filter(
                            operation=GenericFilterOps("equals"), value=value
                        )
                else:
                    values["dict_of_filters"][key] = Filter(
                        operation=GenericFilterOps("equals"), value=value
                    )
        return values
