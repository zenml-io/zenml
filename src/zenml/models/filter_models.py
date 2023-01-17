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

    ALLOWED_OPS: ClassVar[List[str]] = [
        GenericFilterOps.EQUALS,
    ]

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

    @abstractmethod
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


class BoolFilter(Filter):
    """Filter for all Boolean fields."""

    def generate_query_conditions(
        self,
        table: Type[SQLModel],
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
        """Generate the query conditions for the database.

        Args:
            table: The SQLModel table to use for the query creation

        Returns:
            A list of conditions that will be combined using the `and` operation
        """
        return (  # type:ignore[no-any-return]
            getattr(table, self.column) == self.value
        )


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
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
        """Generate the query conditions for the database.

        Args:
            table: The SQLModel table to use for the query creation

        Returns:
            A list of conditions that will be combined using the `and` operation
        """
        if self.operation == GenericFilterOps.CONTAINS:
            return getattr(  # type:ignore[no-any-return]
                table, self.column
            ).like(f"%{self.value}%")
        elif self.operation == GenericFilterOps.STARTSWITH:
            return getattr(  # type:ignore[no-any-return]
                table, self.column
            ).startswith(f"%{self.value}%")
        elif self.operation == GenericFilterOps.CONTAINS:
            return getattr(  # type:ignore[no-any-return]
                table, self.column
            ).endswith(f"%{self.value}%")
        else:
            return (  # type:ignore[no-any-return]
                getattr(table, self.column) == self.value
            )


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
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
        """Generate the query conditions for the database.

        Args:
            table: The SQLModel table to use for the query creation

        Returns:
            A list of conditions that will be combined using the `and` operation
        """
        import sqlalchemy
        from sqlalchemy_utils.functions import cast_if

        if self.operation == GenericFilterOps.CONTAINS:
            return cast_if(  # type:ignore[no-any-return]
                getattr(table, self.column), sqlalchemy.String
            ).like(f"%{self.value}%")
        elif self.operation == GenericFilterOps.STARTSWITH:
            return cast_if(  # type:ignore[no-any-return]
                getattr(table, self.column), sqlalchemy.String
            ).startswith(f"%{self.value}%")
        elif self.operation == GenericFilterOps.CONTAINS:
            return cast_if(  # type:ignore[no-any-return]
                getattr(table, self.column), sqlalchemy.String
            ).endswith(f"%{self.value}%")
        else:
            return (  # type:ignore[no-any-return]
                getattr(table, self.column) == self.value
            )


class NumericFilter(Filter):
    """Filter for all numeric fields."""

    value: float

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
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
        """Generate the query conditions for the database.

        Args:
            table: The SQLModel table to use for the query creation

        Returns:
            A list of conditions that will be combined using the `and` operation
        """
        if self.operation == GenericFilterOps.GTE:
            return (  # type:ignore[no-any-return]
                getattr(table, self.column) >= self.value
            )
        elif self.operation == GenericFilterOps.GT:
            return (  # type:ignore[no-any-return]
                getattr(table, self.column) > self.value
            )
        elif self.operation == GenericFilterOps.LTE:
            return (  # type:ignore[no-any-return]
                getattr(table, self.column) <= self.value
            )
        elif self.operation == GenericFilterOps.LT:
            return (  # type:ignore[no-any-return]
                getattr(table, self.column) < self.value
            )
        else:
            return (  # type:ignore[no-any-return]
                getattr(table, self.column) == self.value
            )


class DatetimeFilter(Filter):
    """Filter for all Boolean fields."""

    value: datetime

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
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
        """Generate the query conditions for the database.

        Args:
            table: The SQLModel table to use for the query creation

        Returns:
            A list of conditions that will be combined using the `and` operation
        """
        if self.operation == GenericFilterOps.GTE:
            return (  # type:ignore[no-any-return]
                getattr(table, self.column) >= self.value
            )
        elif self.operation == GenericFilterOps.GT:
            return (  # type:ignore[no-any-return]
                getattr(table, self.column) > self.value
            )
        elif self.operation == GenericFilterOps.LTE:
            return (  # type:ignore[no-any-return]
                getattr(table, self.column) <= self.value
            )
        elif self.operation == GenericFilterOps.LT:
            return (  # type:ignore[no-any-return]
                getattr(table, self.column) < self.value
            )
        else:
            return (  # type:ignore[no-any-return]
                getattr(table, self.column) == self.value
            )


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

    class Config:
        """Configure all Filter Models."""

        extras = False
        fields = {"list_of_filters": {"exclude": True}}

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

                    DatetimeFilter(
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
                            DatetimeFilter(
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

    def _base_filter(
        self, table: Type[SQLModel]
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
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

    def _scope_filter(
        self, table: Type[SQLModel]
    ) -> Optional[Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]]:
        return None

    def generate_filter(
        self, table: Type[SQLModel]
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
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

    def set_scope_project(self, project_id: UUID) -> None:
        """Set the project to scope this response."""
        self._scope_project = project_id

    def _scope_filter(
        self, table: Type["SQLModel"]
    ) -> Optional[Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]]:
        """Scope by project.

        Args:
            table: The Table that is being queried from.

        Returns:
            A list of all scope filters that will be conjuncted with the other
                filters
        """
        if self._scope_project:
            return (  # type:ignore[no-any-return]
                getattr(table, "project_id") == self._scope_project
            )
        else:
            return None


class ShareableProjectScopedFilterModel(ProjectScopedFilterModel):
    """Model to enable advanced scoping with project and user scoped shareable things."""

    _scope_user: UUID = PrivateAttr(None)

    def set_scope_user(self, user_id: UUID) -> None:
        """Set the user that is performing the filtering to scope the response."""
        self._scope_user = user_id

    def _scope_filter(
        self, table: Type["SQLModel"]
    ) -> Optional[Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]]:
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
