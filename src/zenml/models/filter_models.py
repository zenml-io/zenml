from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Type, Union, List, Optional, ClassVar, get_args
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, validator, root_validator, PrivateAttr, Field
from sqlmodel import SQLModel

from zenml.utils.enum_utils import StrEnum
from zenml.logger import get_logger

logger = get_logger(__name__)

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
    value: Any

    def generate_query_conditions(
        self,
        table: Type[SQLModel],
    ):
        if self.operation == GenericFilterOps.EQUALS:
            return getattr(table, self.column) == self.value
        elif self.operation == GenericFilterOps.CONTAINS:
            return getattr(table, self.column).like(f"%{self.value}%")
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
    list_of_filters: List[Filter] = Field(None, exclude=True)

    sort_by: str = Query("created")

    page: int = Query(1, ge=1, description="Page number")
    size: int = Query(50, ge=1, le=100, description="Page size")

    id: UUID = Query(None, description="Id for this resource")
    created: Union[datetime, str] = Query(None, description="Created")
    updated: datetime = Query(None, description="Updated")

    class Config:
        extras = False
        fields = {'list_of_filters': {'exclude': True}}

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

    @root_validator(pre=True)
    def filter_ops(cls, values):
        list_of_filters = []

        # These 3 fields do not represent filter fields
        exclude_fields = {"sort_by", "page", "size"}

        for key, value in values.items():
            if key in exclude_fields:
                pass
            elif value:
                if isinstance(value, str):
                    split_value = value.split(":", 1)
                    if (
                        len(split_value) == 2
                        and split_value[0] in GenericFilterOps.values()
                    ):
                        # Parse out the operation from the input string
                        if issubclass(datetime, get_args(cls.__fields__[key].type_)):
                            typed_value = datetime.strptime(split_value[1],
                                                            '%y-%m-%d %H:%M:%S')
                        elif issubclass(UUID, get_args(cls.__fields__[key].type_)):
                            typed_value = UUID(split_value[1])
                        elif issubclass(str, get_args(cls.__fields__[key].type_)):
                            typed_value = split_value[1]
                        elif issubclass(int, get_args(cls.__fields__[key].type_)):
                            typed_value = int(split_value[1])
                        elif issubclass(bool, get_args(cls.__fields__[key].type_)):
                            typed_value = bool(split_value[1])
                        else:
                            logger.warning("The Datatype "
                                           "cls.__fields__[key].type_ might "
                                           "not be supported for filtering ")
                            typed_value = str(split_value[1])

                        # TODO: actually convert the value into the correct
                        #  datatype
                        list_of_filters.append(
                            Filter(
                                operation=GenericFilterOps(split_value[0]),
                                column=key,
                                value=typed_value,
                            )
                        )
                    else:
                        list_of_filters.append(
                            Filter(
                                operation=GenericFilterOps("equals"),
                                column=key,
                                value=value,
                            )
                        )
                else:
                    list_of_filters.append(
                        Filter(
                            operation=GenericFilterOps("equals"),
                            column=key,
                            value=value,
                        )
                    )
        values["list_of_filters"] = list_of_filters
        return values

    def get_pagination_params(self) -> RawParams:
        return RawParams(
            limit=self.size,
            offset=self.size * (self.page - 1),
        )

    def generate_filter(self, table: Type[SQLModel]):
        ands = []
        for column_filter in self.list_of_filters:
            ands.append(column_filter.generate_query_conditions(table=table))

        return ands

    @classmethod
    def click_list_options(cls):
        import click

        options = list()
        for k, v in cls.__fields__.items():
            if k not in ["list_of_filters"]:
                options.append(
                    click.option(
                        f"--{k}",
                        type=str,
                        default=v.default,
                        required=False,
                    )
                )

        def wrapper(function):
            for option in reversed(options):
                function = option(function)
            return function

        return wrapper
