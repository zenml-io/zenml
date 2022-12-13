from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, ClassVar, List, Type, Union, get_args
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, Field, PrivateAttr, root_validator, validator
from sqlmodel import SQLModel

from zenml.constants import (
    FILTERING_DATETIME_FORMAT,
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAXIMUM,
    PAGINATION_STARTING_PAGE,
)
from zenml.enums import GenericFilterOps, LogicalOperators
from zenml.logger import get_logger

logger = get_logger(__name__)


# -------------- #
# FILTER CLASSES #
# ---------------#


class Filter(BaseModel, ABC):
    """Filter for all fields."""

    operation: GenericFilterOps
    column: str
    value: Any

    @abstractmethod
    def generate_query_conditions(
        self,
        table: Type[SQLModel],
    ):
        """Generate the query conditions for the database.

        Args:
            table: The SQLModel table to use for the query creation

        Returns:
            A list of conditions that will be combined using the `and` operation
        """


class BoolFilter(Filter):
    ALLOWED_OPS: ClassVar[List[str]] = [
        GenericFilterOps.EQUALS,
    ]

    def generate_query_conditions(
        self,
        table: Type[SQLModel],
    ):
        """Generate the query conditions for the database.

        Args:
            table: The SQLModel table to use for the query creation

        Returns:
            A list of conditions that will be combined using the `and` operation
        """
        if self.operation == GenericFilterOps.EQUALS:
            return getattr(table, self.column) == self.value


class StrFilter(Filter):
    """Filter for all string fields."""

    ALLOWED_OPS: ClassVar[List[str]] = [
        GenericFilterOps.EQUALS,
        GenericFilterOps.STARTSWITH,
        GenericFilterOps.CONTAINS,
        GenericFilterOps.ENDSWITH,
    ]

    def generate_query_conditions(
        self,
        table: Type[SQLModel],
    ):
        """Generate the query conditions for the database.

        Args:
            table: The SQLModel table to use for the query creation

        Returns:
            A list of conditions that will be combined using the `and` operation
        """
        if self.operation == GenericFilterOps.EQUALS:
            return getattr(table, self.column) == self.value
        elif self.operation == GenericFilterOps.CONTAINS:
            return getattr(table, self.column).like(f"%{self.value}%")
        elif self.operation == GenericFilterOps.STARTSWITH:
            return getattr(table, self.column).startswith(f"%{self.value}%")
        elif self.operation == GenericFilterOps.CONTAINS:
            return getattr(table, self.column).endswith(f"%{self.value}%")


class UUIDFilter(Filter):
    """Filter for all uuid fields which are mostly treated like strings."""

    ALLOWED_OPS: ClassVar[List[str]] = [
        GenericFilterOps.EQUALS,
        GenericFilterOps.STARTSWITH,
        GenericFilterOps.CONTAINS,
        GenericFilterOps.ENDSWITH,
    ]

    def generate_query_conditions(
        self,
        table: Type[SQLModel],
    ):
        """Generate the query conditions for the database.

        Args:
            table: The SQLModel table to use for the query creation

        Returns:
            A list of conditions that will be combined using the `and` operation
        """
        import sqlalchemy
        from sqlalchemy_utils.functions import cast_if

        if self.operation == GenericFilterOps.EQUALS:
            return getattr(table, self.column) == self.value
        elif self.operation == GenericFilterOps.CONTAINS:
            return cast_if(getattr(table, self.column), sqlalchemy.String).like(
                f"%{self.value}%"
            )
        elif self.operation == GenericFilterOps.STARTSWITH:
            return cast_if(
                getattr(table, self.column), sqlalchemy.String
            ).startswith(f"%{self.value}%")
        elif self.operation == GenericFilterOps.CONTAINS:
            return cast_if(
                getattr(table, self.column), sqlalchemy.String
            ).endswith(f"%{self.value}%")


class NumericFilter(Filter):
    """Filter for all numeric fields."""

    ALLOWED_OPS: ClassVar[List[str]] = [
        GenericFilterOps.EQUALS,
        GenericFilterOps.GT,
        GenericFilterOps.GTE,
        GenericFilterOps.LT,
        GenericFilterOps.LTE,
    ]

    def generate_query_conditions(
        self,
        table: Type[SQLModel],
    ):
        """Generate the query conditions for the database.

        Args:
            table: The SQLModel table to use for the query creation

        Returns:
            A list of conditions that will be combined using the `and` operation
        """
        if self.operation == GenericFilterOps.EQUALS:
            return getattr(table, self.column) == self.value
        elif self.operation == GenericFilterOps.GTE:
            return getattr(table, self.column) >= self.value
        elif self.operation == GenericFilterOps.GT:
            return getattr(table, self.column) > self.value
        elif self.operation == GenericFilterOps.LTE:
            return getattr(table, self.column) <= self.value
        elif self.operation == GenericFilterOps.LT:
            return getattr(table, self.column) < self.value


# ---------------- #
# PAGINATION PARAM #
# -----------------#


class FilterBaseModel(BaseModel):
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

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        "sort_by",
        "list_of_filters",
        "_scope_user",
        "_scope_project",
        "page",
        "size",
        "logical_operator",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        "list_of_filters",
        "_scope_user",
        "_scope_project",
    ]

    list_of_filters: List["Filter"] = Field(None, exclude=True)

    sort_by: str = Query("created")
    logical_operator: LogicalOperators = "and"

    page: int = Query(PAGINATION_STARTING_PAGE, ge=1, description="Page number")
    size: int = Query(
        PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAXIMUM, description="Page size"
    )

    id: Union[UUID, str] = Query(None, description="Id for this resource")
    created: Union[datetime, str] = Query(None, description="Created")
    updated: Union[datetime, str] = Query(None, description="Updated")

    class Config:
        """Configure all Filter Models."""

        extras = False
        fields = {"list_of_filters": {"exclude": True}}

    @validator("sort_by", pre=True)
    def sort_column(cls, v):
        """Validate that the sort_column is a valid filter field."""
        if v in cls.FILTER_EXCLUDE_FIELDS:
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
        """Parse incoming filters to extract the operations on each value."""
        list_of_filters = []

        for key, value in values.items():
            if key in cls.FILTER_EXCLUDE_FIELDS:
                pass
            elif value:
                operator = GenericFilterOps.EQUALS

                if isinstance(value, str):
                    split_value = value.split(":", 1)
                    if (
                        len(split_value) == 2
                        and split_value[0] in GenericFilterOps.values()
                    ):
                        value = split_value[1]
                        operator = GenericFilterOps(split_value[0])

                if cls.is_datatime_field(key):
                    try:
                        datetime_value = datetime.strptime(
                            value, FILTERING_DATETIME_FORMAT
                        )
                    except ValueError as e:
                        raise ValueError(
                            "The datetime filter only works with "
                            "value in the following format is "
                            "expected: `{supported_format}`"
                        ) from e

                    list_of_filters.append(
                        NumericFilter(
                            operation=GenericFilterOps(operator),
                            column=key,
                            value=datetime_value,
                        )
                    )
                elif cls.is_uuid_field(key):
                    if operator == GenericFilterOps.EQUALS and not isinstance(
                        value, UUID
                    ):
                        try:
                            value = UUID(value)
                        except ValueError:
                            raise ValueError(
                                "Invalid value passed as UUID as "
                                "query parameter."
                            ) from 3
                    elif operator != GenericFilterOps.EQUALS:
                        value = str(value)

                    list_of_filters.append(
                        UUIDFilter(
                            operation=GenericFilterOps(operator),
                            column=key,
                            value=value,
                        )
                    )
                elif cls.is_int_field(key):
                    list_of_filters.append(
                        NumericFilter(
                            operation=GenericFilterOps(operator),
                            column=key,
                            value=int(value),
                        )
                    )
                elif cls.is_bool_field(key):
                    if GenericFilterOps(operator) != GenericFilterOps.EQUALS:
                        logger.warning(
                            "Boolean filters do not support any"
                            "operation except for equals. Defaulting"
                            "to an `equals` comparison"
                        )
                    list_of_filters.append(
                        BoolFilter(
                            operation=GenericFilterOps.EQUALS,
                            column=key,
                            value=bool(value),
                        )
                    )
                elif cls.is_str_field(key):
                    list_of_filters.append(
                        StrFilter(
                            operation=GenericFilterOps(operator),
                            column=key,
                            value=value,
                        )
                    )
                else:
                    logger.warning(
                        "The Datatype "
                        "cls.__fields__[key].type_ might "
                        "not be supported for filtering "
                    )
                    list_of_filters.append(
                        StrFilter(
                            operation=GenericFilterOps(operator),
                            column=key,
                            value=str(value),
                        )
                    )

        values["list_of_filters"] = list_of_filters
        return values

    @classmethod
    def is_datatime_field(cls, k: str) -> bool:
        return issubclass(datetime, get_args(cls.__fields__[k].type_))

    @classmethod
    def is_uuid_field(cls, k: str) -> bool:
        return issubclass(UUID, get_args(cls.__fields__[k].type_))

    @classmethod
    def is_int_field(cls, k: str) -> bool:
        return issubclass(int, get_args(cls.__fields__[k].type_))

    @classmethod
    def is_bool_field(cls, k: str) -> bool:
        return issubclass(bool, get_args(cls.__fields__[k].type_))

    @classmethod
    def is_str_field(cls, k: str) -> bool:
        return (
            issubclass(str, get_args(cls.__fields__[k].type_))
            or cls.__fields__[k].type_ == str
        )

    @property
    def offset(self):
        """Returns the offset needed for the query on the data persistence layer."""
        return self.size * (self.page - 1)

    def _base_filter(self, table: Type[SQLModel]):
        from sqlalchemy import and_
        from sqlmodel import or_

        filters = []
        for column_filter in self.list_of_filters:
            filters.append(column_filter.generate_query_conditions(table=table))
        if self.logical_operator == LogicalOperators.OR:
            return or_(*filters)
        elif self.logical_operator == LogicalOperators.AND:
            return and_(*filters)
        else:
            logger.debug(
                "No valid logical operator was supplied. Defaulting to"
                "use conjunction."
            )
            return filters

    def _scope_filter(self, table: Type[SQLModel]):
        return None

    def generate_filter(self, table: Type[SQLModel]):
        """Concatenate all filters together with the chosen operator."""
        from sqlalchemy import and_

        user_created_filter = self._base_filter(table=table)
        scope_filter = self._scope_filter(table=table)
        if scope_filter is not None:
            return and_(user_created_filter, scope_filter)
        else:
            return user_created_filter


class ProjectScopedFilterModel(FilterBaseModel):
    """Model to enable advanced scoping with project."""

    _scope_project: UUID = PrivateAttr(None)

    def set_scope_project(self, project_id: UUID):
        """Set the project to scope this response."""
        self._scope_project = project_id

    def _scope_filter(self, table: Type["SQLModel"]):
        """Scope by project.

        Args:
            table: The Table that is being queried from.

        Returns:
            A list of all scope filters that will be conjuncted with the other
                filters
        """
        if self._scope_project:
            return getattr(table, "project_id") == self._scope_project
        else:
            return None


class ShareableProjectScopedFilterModel(ProjectScopedFilterModel):
    """Model to enable advanced scoping with project and user scoped shareable things."""

    _scope_user: UUID = PrivateAttr(None)

    def set_scope_user(self, user_id: UUID):
        """Set the user that is performing the filtering to scope the response."""
        self._scope_user = user_id

    def _scope_filter(self, table: Type["SQLModel"]):
        """A User is only allowed to list the stacks that either belong to them or that are shared.

        The resulting filter from this method will be the union of the scoping
        filter (owned by user OR shared) with the user provided filters.

        Args:
            table: The Table that is being queried from.

        Returns:
            A list of all scope filters that will be conjuncted with the other
                filters
        """
        from sqlalchemy import and_
        from sqlmodel import or_

        scope_filter = []
        if self._scope_user:
            scope_filter.append(
                or_(
                    getattr(table, "user_id") == self._scope_user,
                    getattr(table, "is_shared") is True,
                )
            )
        if self._scope_project:
            scope_filter.append(
                getattr(table, "project_id") == self._scope_project
            )

        if scope_filter:
            return and_(*scope_filter)
        else:
            return None
