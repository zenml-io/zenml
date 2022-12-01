from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Type, Dict, TypeVar, List, Callable
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
    column: str
    value: str

    def generate_query_condition(
        self,
        table: Type[SQLModel],
    ):
        if self.operation == GenericFilterOps.EQUALS:
            return getattr(table, self.column) == self.value
        elif self.operation == GenericFilterOps.CONTAINS:
            return getattr(table, self.column).like(f'%{self.value}%')
        elif self.operation == GenericFilterOps.GTE:
            return getattr(table, self.column) >= self.value
        elif self.operation == GenericFilterOps.GT:
            return getattr(table, self.column) > self.value
        elif self.operation == GenericFilterOps.LTE:
            return getattr(table, self.column) <= self.value
        elif self.operation == GenericFilterOps.LT:
            return getattr(table, self.column) < self.value


class ListBaseModel(BaseModel):
    """Class to unify all filter, paginate and sort request parameters in one place.

    This Model allows fine-grained filtering, sorting and pagination of
    resources.

    Usage for a given Child of this class:
    ```
    ResourceListModel(
        name="contains:default",
        project="default"
        count_steps="gte:5"
        sort_by="created",
        page=2,
        size=50
    )
    ```
    """
    _list_of_filters: List[Filter] = []
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

    def get_filters(self) -> List[Filter]:
        return self._list_of_filters

    @validator("sort_by", pre=True)
    def sort_column(cls, v):
        if v in ["sort_by", "_list_of_filters", "page", "size"]:
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
        values["_list_of_filters"] = []

        for key, value in values.items():
            # These 4 fields do not represent filter fields
            if key in ["sort_by", "_list_of_filters", "page", "size"]:
                pass
            elif value:
                if isinstance(value, str):
                    split_value = value.split(':', 1)
                    if (len(split_value) == 2
                            and split_value[0] in GenericFilterOps.values()):
                        # Parse out the operation from the input string
                        values["_list_of_filters"].append(Filter(
                            operation=GenericFilterOps(split_value[0]),
                            column=key,
                            value=split_value[1]
                        ))
                    else:
                        #
                        values["_list_of_filters"].append(Filter(
                            operation=GenericFilterOps("equals"),
                            column=key,
                            value=value
                        ))
                else:
                    values["_list_of_filters"].append(Filter(
                        operation=GenericFilterOps("equals"),
                        column=key,
                        value=value
                    ))
        return values

    @classmethod
    def click_list_options(cls):
        import click

        options = list()
        for k, v in cls.__fields__.items():
            if k not in ["_list_of_filters"]:
                options.append(click.option(
                    f"--{k}", type=v.type_, default=v.default, required=False)
                )

        def wrapper(function):
            for option in reversed(options):
                function = option(function)
            return function
        return wrapper
