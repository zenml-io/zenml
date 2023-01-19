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
"""Base filter model definitions."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Type,
    Union,
    get_args,
)
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel, PrivateAttr, root_validator, validator
from sqlmodel import SQLModel

from zenml.constants import (
    FILTERING_DATETIME_FORMAT,
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAXIMUM,
    PAGINATION_STARTING_PAGE,
)
from zenml.enums import GenericFilterOps, LogicalOperators
from zenml.logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import BinaryExpression, BooleanClauseList

logger = get_logger(__name__)


# -------------- #
# FILTER CLASSES #
# ---------------#


class Filter(BaseModel, ABC):
    """Filter for all fields.

    A Filter is a combination of a column, a value that the user uses to
    filter on this column and an operation to use. The easiest example
    would be `user equals aria` with column=`user`, value=`aria` and the
    operation=`equals`.

    All subclasses of this class will support different sets of operations.
    This operation set is defined in the ALLOWED_OPS class variable.
    """

    ALLOWED_OPS: ClassVar[List[str]] = []

    operation: GenericFilterOps
    column: str
    value: Any

    @validator("operation", pre=True)
    def validate_operation(cls, op: str) -> str:
        """Validate that the operation is a valid op for the field type.

        Args:
            op: The operation of this filter.
        """
        if op not in cls.ALLOWED_OPS:
            raise ValueError(
                f"This datatype can not be filtered using this operation: "
                f"'{op}'. The allowed operations are: {cls.ALLOWED_OPS}"
            )
        else:
            return op

    def generate_query_conditions(
        self,
        table: Type[SQLModel],
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
        """Generate the query conditions for the database.

        This method converts the Filter class into an appropriate SQLModel
        query condition, to be used when filtering on the Database.

        Args:
            table: The SQLModel table to use for the query creation

        Returns:
            A list of conditions that will be combined using the `and` operation
        """
        column = getattr(table, self.column)
        conditions = self.generate_query_conditions_from_column(column)
        return conditions  # type:ignore[no-any-return]

    @abstractmethod
    def generate_query_conditions_from_column(self, column: Any) -> Any:
        """Generate query conditions given the corresponding database column.

        This method should be overridden by subclasses to define how each
        supported operation in `self.ALLOWED_OPS` can be used to filter the
        given column by `self.value`.

        Args:
            column: The column of an SQLModel table on which to filter.

        Returns:
            A list of query conditions.
        """


class BoolFilter(Filter):
    """Filter for all Boolean fields."""

    ALLOWED_OPS: ClassVar[List[str]] = [GenericFilterOps.EQUALS]

    def generate_query_conditions_from_column(self, column: Any) -> Any:
        """Generate query conditions for a boolean column.

        Args:
            column: The boolean column of an SQLModel table on which to filter.

        Returns:
            A list of query conditions.
        """
        return column == self.value


class StrFilter(Filter):
    """Filter for all string fields."""

    ALLOWED_OPS: ClassVar[List[str]] = [
        GenericFilterOps.EQUALS,
        GenericFilterOps.STARTSWITH,
        GenericFilterOps.CONTAINS,
        GenericFilterOps.ENDSWITH,
    ]

    def generate_query_conditions_from_column(self, column: Any) -> Any:
        """Generate query conditions for a string column.

        Args:
            column: The string column of an SQLModel table on which to filter.

        Returns:
            A list of query conditions.
        """
        if self.operation == GenericFilterOps.CONTAINS:
            return column.like(f"%{self.value}%")
        if self.operation == GenericFilterOps.STARTSWITH:
            return column.startswith(f"%{self.value}%")
        if self.operation == GenericFilterOps.CONTAINS:
            return column.endswith(f"%{self.value}%")
        return column == self.value


class UUIDFilter(StrFilter):
    """Filter for all uuid fields which are mostly treated like strings."""

    def generate_query_conditions_from_column(self, column: Any) -> Any:
        """Generate query conditions for a UUID column.

        Args:
            column: The UUID column of an SQLModel table on which to filter.

        Returns:
            A list of query conditions.
        """
        import sqlalchemy
        from sqlalchemy_utils.functions import cast_if

        return super().generate_query_conditions_from_column(
            column=cast_if(column, sqlalchemy.String)
        )


class NumericFilter(Filter):
    """Filter for all numeric fields."""

    value: Union[float, datetime]

    ALLOWED_OPS: ClassVar[List[str]] = [
        GenericFilterOps.EQUALS,
        GenericFilterOps.GT,
        GenericFilterOps.GTE,
        GenericFilterOps.LT,
        GenericFilterOps.LTE,
    ]

    def generate_query_conditions_from_column(self, column: Any) -> Any:
        """Generate query conditions for a UUID column.

        Args:
            column: The UUID column of an SQLModel table on which to filter.

        Returns:
            A list of query conditions.
        """
        if self.operation == GenericFilterOps.GTE:
            return column >= self.value
        if self.operation == GenericFilterOps.GT:
            return column > self.value
        if self.operation == GenericFilterOps.LTE:
            return column <= self.value
        if self.operation == GenericFilterOps.LT:
            return column < self.value
        return column == self.value


# ---------------- #
# PAGINATION PARAM #
# -----------------#


class FilterBaseModel(BaseModel):
    """Class to unify all filter, paginate and sort request parameters.

    This Model allows fine-grained filtering, sorting and pagination of
    resources.

    Usage example for subclasses of this class:
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
        "_scope_user",
        "_scope_project",
        "page",
        "size",
        "logical_operator",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        "_scope_user",
        "_scope_project",
    ]

    sort_by: str = Query("created", description="Which column to sort by.")
    logical_operator: str = Query(
        LogicalOperators.AND,
        description="Which logical operator to use between all filters "
        "['and', 'or']",
    )

    page: int = Query(
        PAGINATION_STARTING_PAGE, ge=1, description="Page number"
    )
    size: int = Query(
        PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAXIMUM, description="Page size"
    )

    id: Union[UUID, str] = Query(None, description="Id for this resource")
    created: Union[datetime, str] = Query(None, description="Created")
    updated: Union[datetime, str] = Query(None, description="Updated")

    @validator("sort_by", pre=True)
    def sort_column(cls, v: str) -> str:
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
    def filter_ops(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Parse incoming filters to ensure all filters are legal."""
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

                if cls.is_datetime_field(key):
                    try:
                        if isinstance(value, datetime):
                            datetime_value = value
                        else:
                            datetime_value = datetime.strptime(
                                value, FILTERING_DATETIME_FORMAT
                            )
                    except ValueError as e:
                        raise ValueError(
                            "The datetime filter only works with "
                            "value in the following format is "
                            "expected: `{supported_format}`"
                        ) from e

                    NumericFilter(
                        operation=GenericFilterOps(operator),
                        column=key,
                        value=datetime_value,
                    )
                elif cls.is_uuid_field(key):
                    if operator == GenericFilterOps.EQUALS and not isinstance(
                        value, UUID
                    ):
                        try:
                            value = UUID(value)
                        except ValueError as e:
                            raise ValueError(
                                "Invalid value passed as UUID as "
                                "query parameter."
                            ) from e
                    elif operator != GenericFilterOps.EQUALS:
                        value = str(value)

                    UUIDFilter(
                        operation=GenericFilterOps(operator),
                        column=key,
                        value=value,
                    )
                elif cls.is_int_field(key):
                    NumericFilter(
                        operation=GenericFilterOps(operator),
                        column=key,
                        value=int(value),
                    )

                elif cls.is_bool_field(key):
                    if GenericFilterOps(operator) != GenericFilterOps.EQUALS:
                        logger.warning(
                            "Boolean filters do not support any"
                            "operation except for equals. Defaulting"
                            "to an `equals` comparison"
                        )
                    BoolFilter(
                        operation=GenericFilterOps.EQUALS,
                        column=key,
                        value=bool(value),
                    )
                elif cls.is_str_field(key):
                    StrFilter(
                        operation=GenericFilterOps(operator),
                        column=key,
                        value=value,
                    )
                else:
                    logger.warning(
                        "The Datatype "
                        "cls.__fields__[key].type_ might "
                        "not be supported for filtering "
                    )
                    StrFilter(
                        operation=GenericFilterOps(operator),
                        column=key,
                        value=str(value),
                    )

        return values

    @property
    def list_of_filters(self) -> List[Filter]:
        """Converts the class variables into a list of usable Filter Models."""
        list_of_filters: List[Filter] = []

        for key in self.__fields__:
            if key in self.FILTER_EXCLUDE_FIELDS:
                pass
            else:
                value = getattr(self, key)
                if value:
                    operator = GenericFilterOps.EQUALS

                    if isinstance(value, str):
                        split_value = value.split(":", 1)
                        if (
                            len(split_value) == 2
                            and split_value[0] in GenericFilterOps.values()
                        ):
                            value = split_value[1]
                            operator = GenericFilterOps(split_value[0])

                    if self.is_datetime_field(key):
                        try:
                            if isinstance(value, datetime):
                                datetime_value = value
                            else:
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
                    elif self.is_uuid_field(key):
                        if (
                            operator == GenericFilterOps.EQUALS
                            and not isinstance(value, UUID)
                        ):
                            try:
                                value = UUID(value)
                            except ValueError as e:
                                raise ValueError(
                                    "Invalid value passed as UUID as "
                                    "query parameter."
                                ) from e
                        elif operator != GenericFilterOps.EQUALS:
                            value = str(value)

                        list_of_filters.append(
                            UUIDFilter(
                                operation=GenericFilterOps(operator),
                                column=key,
                                value=value,
                            )
                        )
                    elif self.is_int_field(key):
                        list_of_filters.append(
                            NumericFilter(
                                operation=GenericFilterOps(operator),
                                column=key,
                                value=int(value),
                            )
                        )
                    elif self.is_bool_field(key):
                        if (
                            GenericFilterOps(operator)
                            != GenericFilterOps.EQUALS
                        ):
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
                    elif self.is_str_field(key):
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
                            f"{self.__fields__[key]}.type_ might "
                            "not be supported for filtering "
                        )
                        list_of_filters.append(
                            StrFilter(
                                operation=GenericFilterOps(operator),
                                column=key,
                                value=str(value),
                            )
                        )
        return list_of_filters

    @classmethod
    def is_datetime_field(cls, k: str) -> bool:
        """Checks if it's a datetime field."""
        return issubclass(datetime, get_args(cls.__fields__[k].type_))

    @classmethod
    def is_uuid_field(cls, k: str) -> bool:
        """Checks if it's a uuid field."""
        return issubclass(UUID, get_args(cls.__fields__[k].type_))

    @classmethod
    def is_int_field(cls, k: str) -> bool:
        """Checks if it's a int field."""
        return issubclass(int, get_args(cls.__fields__[k].type_))

    @classmethod
    def is_bool_field(cls, k: str) -> bool:
        """Checks if it's a bool field."""
        return issubclass(bool, get_args(cls.__fields__[k].type_))

    @classmethod
    def is_str_field(cls, k: str) -> bool:
        """Checks if it's a string field."""
        return (
            issubclass(str, get_args(cls.__fields__[k].type_))
            or cls.__fields__[k].type_ == str
        )

    @property
    def offset(self) -> int:
        """Returns the offset needed for the query on the data persistence layer."""
        return self.size * (self.page - 1)

    def generate_filter(
        self, table: Type[SQLModel]
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
        """Generate the filter for the query.

        Args:
            table: The Table that is being queried from.

        Returns:
            The filter expression for the query.
        """
        from sqlalchemy import and_
        from sqlmodel import or_

        filters = []
        for column_filter in self.list_of_filters:
            filters.append(
                column_filter.generate_query_conditions(table=table)
            )
        if self.logical_operator == LogicalOperators.OR:
            return or_(*filters)
        elif self.logical_operator == LogicalOperators.AND:
            return and_(*filters)
        else:
            raise RuntimeError("No valid logical operator was supplied.")


class ProjectScopedFilterModel(FilterBaseModel):
    """Model to enable advanced scoping with project."""

    _scope_project: UUID = PrivateAttr(None)

    def set_scope_project(self, project_id: UUID) -> None:
        """Set the project to scope this response."""
        self._scope_project = project_id

    def generate_filter(
        self, table: Type["SQLModel"]
    ) -> Optional[Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]]:
        """Generate the filter for the query.

        Many resources are scoped by project, in which case only the resources
        belonging to the active project should be returned.

        Args:
            table: The Table that is being queried from.

        Returns:
            The filter expression for the query.
        """
        from sqlalchemy import and_

        base_filter = super().generate_filter(table)
        if self._scope_project:
            project_filter = (
                getattr(table, "project_id") == self._scope_project
            )
            return and_(base_filter, project_filter)
        return base_filter


class ShareableProjectScopedFilterModel(ProjectScopedFilterModel):
    """Model to enable advanced scoping with project and user scoped shareable things."""

    _scope_user: UUID = PrivateAttr(None)

    def set_scope_user(self, user_id: UUID) -> None:
        """Set the user that is performing the filtering to scope the response."""
        self._scope_user = user_id

    def generate_filter(
        self, table: Type["SQLModel"]
    ) -> Optional[Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]]:
        """Generate the filter for the query.

        A user is only allowed to list the resources that either belong to them
        or that are shared.

        Args:
            table: The Table that is being queried from.

        Returns:
            The filter expression for the query.
        """
        from sqlalchemy import and_
        from sqlmodel import or_

        base_filter = super().generate_filter(table)
        if self._scope_user:
            user_filter = or_(
                getattr(table, "user_id") == self._scope_user,
                getattr(table, "is_shared") is True,
            )
            return and_(base_filter, user_filter)
        return base_filter
