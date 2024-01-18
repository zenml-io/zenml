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

from abc import ABC, abstractmethod
from datetime import datetime
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
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

    from zenml.zen_stores.schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

logger = get_logger(__name__)


AnyQuery = TypeVar("AnyQuery", bound=Any)


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

        Returns:
            The operation if it is valid.

        Raises:
            ValueError: If the operation is not valid for this field type.
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
            return column.startswith(f"{self.value}")
        if self.operation == GenericFilterOps.ENDSWITH:
            return column.endswith(f"{self.value}")
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


class BaseFilter(BaseModel):
    """Class to unify all filter, paginate and sort request parameters.

    This Model allows fine-grained filtering, sorting and pagination of
    resources.

    Usage example for subclasses of this class:
    ```
    ResourceListModel(
        name="contains:default",
        workspace="default"
        count_steps="gte:5"
        sort_by="created",
        page=2,
        size=20
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

    # List of fields that are wrapped with `fastapi.Query(default)` in API.
    API_MULTI_INPUT_PARAMS: ClassVar[List[str]] = []

    sort_by: str = Field(
        default="created", description="Which column to sort by."
    )
    logical_operator: LogicalOperators = Field(
        default=LogicalOperators.AND,
        description="Which logical operator to use between all filters "
        "['and', 'or']",
    )
    page: int = Field(
        default=PAGINATION_STARTING_PAGE, ge=1, description="Page number"
    )
    size: int = Field(
        default=PAGE_SIZE_DEFAULT,
        ge=1,
        le=PAGE_SIZE_MAXIMUM,
        description="Page size",
    )

    id: Optional[Union[UUID, str]] = Field(
        default=None, description="Id for this resource"
    )
    created: Optional[Union[datetime, str]] = Field(
        default=None, description="Created"
    )
    updated: Optional[Union[datetime, str]] = Field(
        default=None, description="Updated"
    )

    _rbac_configuration: Optional[
        Tuple[UUID, Dict[str, Optional[Set[UUID]]]]
    ] = None

    @validator("sort_by", pre=True)
    def validate_sort_by(cls, v: str) -> str:
        """Validate that the sort_column is a valid column with a valid operand.

        Args:
            v: The sort_by field value.

        Returns:
            The validated sort_by field value.

        Raises:
            ValidationError: If the sort_by field is not a string.
            ValueError: If the resource can't be sorted by this field.
        """
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
        """Parse incoming filters to ensure all filters are legal.

        Args:
            values: The values of the class.

        Returns:
            The values of the class.
        """
        cls._generate_filter_list(values)
        return values

    @property
    def list_of_filters(self) -> List[Filter]:
        """Converts the class variables into a list of usable Filter Models.

        Returns:
            A list of Filter models.
        """
        return self._generate_filter_list(
            {key: getattr(self, key) for key in self.__fields__}
        )

    @property
    def sorting_params(self) -> Tuple[str, SorterOps]:
        """Converts the class variables into a list of usable Filter Models.

        Returns:
            A tuple of the column to sort by and the sorting operand.
        """
        column = self.sort_by
        # The default sorting operand is asc
        operator = SorterOps.ASCENDING

        # Check if user explicitly set an operand
        split_value = self.sort_by.split(":", 1)
        if len(split_value) == 2:
            column = split_value[1]
            operator = SorterOps(split_value[0])

        return column, operator

    def configure_rbac(
        self,
        authenticated_user_id: UUID,
        **column_allowed_ids: Optional[Set[UUID]],
    ) -> None:
        """Configure RBAC allowed column values.

        Args:
            authenticated_user_id: ID of the authenticated user. All entities
                owned by this user will be included.
            column_allowed_ids: Set of IDs per column to limit the query to.
                If given, the remaining filters will be applied to entities
                within this set only. If `None`, the remaining filters will
                applied to all entries in the table.
        """
        self._rbac_configuration = (authenticated_user_id, column_allowed_ids)

    def generate_rbac_filter(
        self,
        table: Type["AnySchema"],
    ) -> Optional["BooleanClauseList[Any]"]:
        """Generates an optional RBAC filter.

        Args:
            table: The query table.

        Returns:
            The RBAC filter.
        """
        from sqlmodel import or_

        if not self._rbac_configuration:
            return None

        expressions = []

        for column_name, allowed_ids in self._rbac_configuration[1].items():
            if allowed_ids is not None:
                expression = getattr(table, column_name).in_(allowed_ids)
                expressions.append(expression)

        if expressions and hasattr(table, "user_id"):
            # If `expressions` is not empty, we do not have full access to all
            # rows of the table. In this case, we also include rows which the
            # user owns.

            # Unowned entities are considered server-owned and can be seen
            # by anyone
            expressions.append(getattr(table, "user_id").is_(None))
            # The authenticated user owns this entity
            expressions.append(
                getattr(table, "user_id") == self._rbac_configuration[0]
            )

        if expressions:
            return or_(*expressions)
        else:
            return None

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
        """Checks if it's a datetime field.

        Args:
            k: The key to check.

        Returns:
            True if the field is a datetime field, False otherwise.
        """
        return (
            issubclass(datetime, get_args(cls.__fields__[k].type_))
            or cls.__fields__[k].type_ is datetime
        )

    @classmethod
    def is_uuid_field(cls, k: str) -> bool:
        """Checks if it's a uuid field.

        Args:
            k: The key to check.

        Returns:
            True if the field is a uuid field, False otherwise.
        """
        return (
            issubclass(UUID, get_args(cls.__fields__[k].type_))
            or cls.__fields__[k].type_ is UUID
        )

    @classmethod
    def is_int_field(cls, k: str) -> bool:
        """Checks if it's a int field.

        Args:
            k: The key to check.

        Returns:
            True if the field is a int field, False otherwise.
        """
        return (
            issubclass(int, get_args(cls.__fields__[k].type_))
            or cls.__fields__[k].type_ is int
        )

    @classmethod
    def is_bool_field(cls, k: str) -> bool:
        """Checks if it's a bool field.

        Args:
            k: The key to check.

        Returns:
            True if the field is a bool field, False otherwise.
        """
        return (
            issubclass(bool, get_args(cls.__fields__[k].type_))
            or cls.__fields__[k].type_ is bool
        )

    @classmethod
    def is_str_field(cls, k: str) -> bool:
        """Checks if it's a string field.

        Args:
            k: The key to check.

        Returns:
            True if the field is a string field, False otherwise.
        """
        return (
            issubclass(str, get_args(cls.__fields__[k].type_))
            or cls.__fields__[k].type_ is str
        )

    @classmethod
    def is_sort_by_field(cls, k: str) -> bool:
        """Checks if it's a sort by field.

        Args:
            k: The key to check.

        Returns:
            True if the field is a sort by field, False otherwise.
        """
        return (
            issubclass(str, get_args(cls.__fields__[k].type_))
            or cls.__fields__[k].type_ == str
        ) and k == "sort_by"

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
        """Returns the offset needed for the query on the data persistence layer.

        Returns:
            The offset for the query.
        """
        return self.size * (self.page - 1)

    def generate_filter(
        self, table: Type[SQLModel]
    ) -> Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]:
        """Generate the filter for the query.

        Args:
            table: The Table that is being queried from.

        Returns:
            The filter expression for the query.

        Raises:
            RuntimeError: If a valid logical operator is not supplied.
        """
        from sqlalchemy import and_
        from sqlmodel import or_

        filters = []
        for column_filter in self.list_of_filters:
            filters.append(
                column_filter.generate_query_conditions(table=table)
            )
        for custom_filter in self.get_custom_filters():
            filters.append(custom_filter)
        if self.logical_operator == LogicalOperators.OR:
            return or_(False, *filters)
        elif self.logical_operator == LogicalOperators.AND:
            return and_(True, *filters)
        else:
            raise RuntimeError("No valid logical operator was supplied.")

    def get_custom_filters(
        self,
    ) -> List[Union["BinaryExpression[Any]", "BooleanClauseList[Any]"]]:
        """Get custom filters.

        This can be overridden by subclasses to define custom filters that are
        not based on the columns of the underlying table.

        Returns:
            A list of custom filters.
        """
        return []

    def apply_filter(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Applies the filter to a query.

        Args:
            query: The query to which to apply the filter.
            table: The query table.

        Returns:
            The query with filter applied.
        """
        rbac_filter = self.generate_rbac_filter(table=table)

        if rbac_filter is not None:
            query = query.where(rbac_filter)

        filters = self.generate_filter(table=table)

        if filters is not None:
            query = query.where(filters)

        return query

    class Config:
        """Pydantic configuration class."""

        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True
