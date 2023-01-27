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
    Tuple,
    Type,
    Union,
)
from uuid import UUID

from pydantic import BaseModel, Field, root_validator, validator
from pydantic.typing import get_args
from sqlmodel import SQLModel

from zenml.constants import (
    FILTERING_DATETIME_FORMAT,
    PAGE_SIZE_DEFAULT,
    PAGE_SIZE_MAXIMUM,
    PAGINATION_STARTING_PAGE,
)
from zenml.enums import GenericFilterOps, LogicalOperators, SorterOps
from zenml.exceptions import ValidationError
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
        if self.operation == GenericFilterOps.ENDSWITH:
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

        # For equality checks, compare the UUID directly
        if self.operation == GenericFilterOps.EQUALS:
            return column == self.value

        # For all other operations, cast and handle the column as string
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


class BaseFilterModel(BaseModel):
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

    # List of fields that cannot be used as filters.
    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        "sort_by",
        "page",
        "size",
        "logical_operator",
    ]

    # List of fields that are not even mentioned as options in the CLI.
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = []

    sort_by: str = Field("created", description="Which column to sort by.")
    logical_operator: LogicalOperators = Field(
        LogicalOperators.AND,
        description="Which logical operator to use between all filters "
        "['and', 'or']",
    )
    page: int = Field(
        PAGINATION_STARTING_PAGE, ge=1, description="Page number"
    )
    size: int = Field(
        PAGE_SIZE_DEFAULT, ge=1, le=PAGE_SIZE_MAXIMUM, description="Page size"
    )

    id: Union[UUID, str] = Field(None, description="Id for this resource")
    created: Union[datetime, str] = Field(None, description="Created")
    updated: Union[datetime, str] = Field(None, description="Updated")

    @validator("sort_by", pre=True)
    def validate_sort_by(cls, v: str) -> str:
        """Validate that the sort_column is a valid column with a valid operand."""
        # Somehow pydantic allows you to pass in int values, which will be
        #  interpreted as string, however within the validator they are still
        #  integers, which don't have a .split() method
        if not isinstance(v, str):
            raise ValidationError(
                f"str type expected for the sort_by field. "
                f"Received a {type(v)}"
            )
        column = v
        split_value = v.split(":", 1)
        if len(split_value) == 2:
            column = split_value[1]

            if split_value[0] not in SorterOps.values():
                logger.warning(
                    "Invalid operand used for column sorting. "
                    "Only the following operands are supported `%s`. "
                    "Defaulting to 'asc' on column `%s`.",
                    SorterOps.values(),
                    column,
                )
                v = column

        if column in cls.FILTER_EXCLUDE_FIELDS:
            raise ValueError(
                f"This resource can not be sorted by this field: '{v}'"
            )
        elif column in cls.__fields__:
            return v
        else:
            raise ValueError(
                "You can only sort by valid fields of this resource"
            )

    @root_validator(pre=True)
    def filter_ops(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Parse incoming filters to ensure all filters are legal."""
        cls._generate_filter_list(values)
        return values

    @property
    def list_of_filters(self) -> List[Filter]:
        """Converts the class variables into a list of usable Filter Models."""
        return self._generate_filter_list(
            {key: getattr(self, key) for key in self.__fields__}
        )

    @property
    def sorting_params(self) -> Tuple[str, SorterOps]:
        """Converts the class variables into a list of usable Filter Models."""
        column = self.sort_by
        # The default sorting operand is asc
        operator = SorterOps.ASCENDING

        # Check if user explicitly set an operand
        split_value = self.sort_by.split(":", 1)
        if len(split_value) == 2:
            column = split_value[1]
            operator = SorterOps(split_value[0])

        return column, operator

    @classmethod
    def _generate_filter_list(cls, values: Dict[str, Any]) -> List[Filter]:
        """Create a list of filters from a (column, value) dictionary.

        Args:
            values: A dictionary of column names and values to filter on.

        Returns:
            A list of filters.
        """
        list_of_filters: List[Filter] = []

        for key, value in values.items():

            # Ignore excluded filters
            if key in cls.FILTER_EXCLUDE_FIELDS:
                continue

            # Skip filtering for None values
            if value is None:
                continue

            # Determine the operator and filter value
            value, operator = cls._resolve_operator(value)

            # Define the filter
            filter = cls._define_filter(
                column=key, value=value, operator=operator
            )
            list_of_filters.append(filter)

        return list_of_filters

    @staticmethod
    def _resolve_operator(value: Any) -> Tuple[Any, GenericFilterOps]:
        """Determine the operator and filter value from a user-provided value.

        If the user-provided value is a string of the form "operator:value",
        then the operator is extracted and the value is returned. Otherwise,
        `GenericFilterOps.EQUALS` is used as default operator and the value
        is returned as-is.

        Args:
            value: The user-provided value.

        Returns:
            A tuple of the filter value and the operator.
        """
        operator = GenericFilterOps.EQUALS  # Default operator
        if isinstance(value, str):
            split_value = value.split(":", 1)
            if (
                len(split_value) == 2
                and split_value[0] in GenericFilterOps.values()
            ):
                value = split_value[1]
                operator = GenericFilterOps(split_value[0])
        return value, operator

    @classmethod
    def _define_filter(
        cls, column: str, value: Any, operator: GenericFilterOps
    ) -> Filter:
        """Define a filter for a given column.

        Args:
            column: The column to filter on.
            value: The value by which to filter.
            operator: The operator to use for filtering.

        Returns:
            A Filter object.
        """
        # Create datetime filters
        if cls.is_datetime_field(column):
            return cls._define_datetime_filter(
                column=column,
                value=value,
                operator=operator,
            )

        # Create UUID filters
        if cls.is_uuid_field(column):
            return cls._define_uuid_filter(
                column=column,
                value=value,
                operator=operator,
            )

        # Create int filters
        if cls.is_int_field(column):
            return NumericFilter(
                operation=GenericFilterOps(operator),
                column=column,
                value=int(value),
            )

        # Create bool filters
        if cls.is_bool_field(column):
            return cls._define_bool_filter(
                column=column,
                value=value,
                operator=operator,
            )

        # Create str filters
        if cls.is_str_field(column):
            return StrFilter(
                operation=GenericFilterOps(operator),
                column=column,
                value=value,
            )

        # Handle unsupported datatypes
        logger.warning(
            f"The Datatype {cls.__fields__[column].type_} might not be "
            "supported for filtering. Defaulting to a string filter."
        )
        return StrFilter(
            operation=GenericFilterOps(operator),
            column=column,
            value=str(value),
        )

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

    @staticmethod
    def _define_datetime_filter(
        column: str, value: Any, operator: GenericFilterOps
    ) -> NumericFilter:
        """Define a datetime filter for a given column.

        Args:
            column: The column to filter on.
            value: The datetime value by which to filter.
            operator: The operator to use for filtering.

        Returns:
            A Filter object.

        Raises:
            ValueError: If the value is not a valid datetime.
        """
        try:
            if isinstance(value, datetime):
                datetime_value = value
            else:
                datetime_value = datetime.strptime(
                    value, FILTERING_DATETIME_FORMAT
                )
        except ValueError as e:
            raise ValueError(
                "The datetime filter only works with values in the following "
                f"format: {FILTERING_DATETIME_FORMAT}"
            ) from e
        datetime_filter = NumericFilter(
            operation=GenericFilterOps(operator),
            column=column,
            value=datetime_value,
        )
        return datetime_filter

    @staticmethod
    def _define_uuid_filter(
        column: str, value: Any, operator: GenericFilterOps
    ) -> UUIDFilter:
        """Define a UUID filter for a given column.

        Args:
            column: The column to filter on.
            value: The UUID value by which to filter.
            operator: The operator to use for filtering.

        Returns:
            A Filter object.

        Raises:
            ValueError: If the value is not a valid UUID.
        """
        # For equality checks, ensure that the value is a valid UUID.
        if operator == GenericFilterOps.EQUALS and not isinstance(value, UUID):
            try:
                UUID(value)
            except ValueError as e:
                raise ValueError(
                    "Invalid value passed as UUID query parameter."
                ) from e

        # Cast the value to string for further comparisons.
        value = str(value)

        # Generate the filter.
        uuid_filter = UUIDFilter(
            operation=GenericFilterOps(operator),
            column=column,
            value=value,
        )
        return uuid_filter

    @staticmethod
    def _define_bool_filter(
        column: str, value: Any, operator: GenericFilterOps
    ) -> BoolFilter:
        """Define a bool filter for a given column.

        Args:
            column: The column to filter on.
            value: The bool value by which to filter.
            operator: The operator to use for filtering.

        Returns:
            A Filter object.
        """
        if GenericFilterOps(operator) != GenericFilterOps.EQUALS:
            logger.warning(
                "Boolean filters do not support any"
                "operation except for equals. Defaulting"
                "to an `equals` comparison."
            )
        return BoolFilter(
            operation=GenericFilterOps.EQUALS,
            column=column,
            value=bool(value),
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
            return or_(False, *filters)
        elif self.logical_operator == LogicalOperators.AND:
            return and_(True, *filters)
        else:
            raise RuntimeError("No valid logical operator was supplied.")


class ProjectScopedFilterModel(BaseFilterModel):
    """Model to enable advanced scoping with project."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilterModel.FILTER_EXCLUDE_FIELDS,
        "scope_project",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *BaseFilterModel.CLI_EXCLUDE_FIELDS,
        "scope_project",
    ]
    scope_project: Optional[UUID] = Field(
        None,
        description="The project to scope this query to.",
    )

    def set_scope_project(self, project_id: UUID) -> None:
        """Set the project to scope this response."""
        self.scope_project = project_id

    def generate_filter(
        self, table: Type["SQLModel"]
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
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
        if self.scope_project:
            project_filter = getattr(table, "project_id") == self.scope_project
            return and_(base_filter, project_filter)
        return base_filter


class ShareableProjectScopedFilterModel(ProjectScopedFilterModel):
    """Model to enable advanced scoping with project and user scoped shareable things."""

    FILTER_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilterModel.FILTER_EXCLUDE_FIELDS,
        "scope_user",
    ]
    CLI_EXCLUDE_FIELDS: ClassVar[List[str]] = [
        *ProjectScopedFilterModel.CLI_EXCLUDE_FIELDS,
        "scope_user",
    ]
    scope_user: Optional[UUID] = Field(
        None,
        description="The user to scope this query to.",
    )

    def set_scope_user(self, user_id: UUID) -> None:
        """Set the user that is performing the filtering to scope the response."""
        self.scope_user = user_id

    def generate_filter(
        self, table: Type["SQLModel"]
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
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
        if self.scope_user:
            user_filter = or_(
                getattr(table, "user_id") == self.scope_user,
                getattr(table, "is_shared").is_(True),
            )
            return and_(base_filter, user_filter)
        return base_filter
