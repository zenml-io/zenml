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

import json
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

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)
from sqlalchemy import Float, and_, asc, cast, desc
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
from zenml.utils.pydantic_utils import before_validator_handler
from zenml.utils.typing_utils import get_args

if TYPE_CHECKING:
    from sqlalchemy.sql.elements import ColumnElement

    from zenml.zen_stores.schemas import BaseSchema, NamedSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

logger = get_logger(__name__)


AnyQuery = TypeVar("AnyQuery", bound=Any)

ONEOF_ERROR = (
    "When you are using the 'oneof:' filtering make sure that the "
    "provided value is a json formatted list."
)


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
    value: Optional[Any] = None

    @field_validator("operation", mode="before")
    @classmethod
    def validate_operation(cls, value: Any) -> Any:
        """Validate that the operation is a valid op for the field type.

        Args:
            value: The operation of this filter.

        Returns:
            The operation if it is valid.

        Raises:
            ValueError: If the operation is not valid for this field type.
        """
        if value not in cls.ALLOWED_OPS:
            raise ValueError(
                f"This datatype can not be filtered using this operation: "
                f"'{value}'. The allowed operations are: {cls.ALLOWED_OPS}"
            )
        else:
            return value

    def generate_query_conditions(
        self,
        table: Type[SQLModel],
    ) -> Union["ColumnElement[bool]"]:
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

    ALLOWED_OPS: ClassVar[List[str]] = [
        GenericFilterOps.EQUALS,
        GenericFilterOps.NOT_EQUALS,
    ]

    def generate_query_conditions_from_column(self, column: Any) -> Any:
        """Generate query conditions for a boolean column.

        Args:
            column: The boolean column of an SQLModel table on which to filter.

        Returns:
            A list of query conditions.
        """
        if self.operation == GenericFilterOps.NOT_EQUALS:
            return column != self.value

        return column == self.value


class StrFilter(Filter):
    """Filter for all string fields."""

    ALLOWED_OPS: ClassVar[List[str]] = [
        GenericFilterOps.EQUALS,
        GenericFilterOps.NOT_EQUALS,
        GenericFilterOps.STARTSWITH,
        GenericFilterOps.CONTAINS,
        GenericFilterOps.ENDSWITH,
        GenericFilterOps.ONEOF,
        GenericFilterOps.GT,
        GenericFilterOps.GTE,
        GenericFilterOps.LT,
        GenericFilterOps.LTE,
    ]

    @model_validator(mode="after")
    def check_value_if_operation_oneof(self) -> "StrFilter":
        """Validator to check if value is a list if oneof operation is used.

        Raises:
            ValueError: If the value is not a list

        Returns:
            self
        """
        if self.operation == GenericFilterOps.ONEOF:
            if not isinstance(self.value, list):
                raise ValueError(ONEOF_ERROR)
        return self

    def generate_query_conditions_from_column(self, column: Any) -> Any:
        """Generate query conditions for a string column.

        Args:
            column: The string column of an SQLModel table on which to filter.

        Returns:
            A list of query conditions.

        Raises:
            ValueError: the comparison of the column to a numeric value fails.
        """
        if self.operation == GenericFilterOps.CONTAINS:
            return column.like(f"%{self.value}%")
        if self.operation == GenericFilterOps.STARTSWITH:
            return column.startswith(f"{self.value}")
        if self.operation == GenericFilterOps.ENDSWITH:
            return column.endswith(f"{self.value}")
        if self.operation == GenericFilterOps.NOT_EQUALS:
            return column != self.value
        if self.operation == GenericFilterOps.ONEOF:
            return column.in_(self.value)
        if self.operation in {
            GenericFilterOps.GT,
            GenericFilterOps.LT,
            GenericFilterOps.GTE,
            GenericFilterOps.LTE,
        }:
            try:
                numeric_column = cast(column, Float)

                assert self.value is not None

                if self.operation == GenericFilterOps.GT:
                    return and_(
                        numeric_column, numeric_column > float(self.value)
                    )
                if self.operation == GenericFilterOps.LT:
                    return and_(
                        numeric_column, numeric_column < float(self.value)
                    )
                if self.operation == GenericFilterOps.GTE:
                    return and_(
                        numeric_column, numeric_column >= float(self.value)
                    )
                if self.operation == GenericFilterOps.LTE:
                    return and_(
                        numeric_column, numeric_column <= float(self.value)
                    )
            except Exception as e:
                raise ValueError(
                    f"Failed to compare the column '{column}' to the "
                    f"value '{self.value}' (must be numeric): {e}"
                )

        return column == self.value


class UUIDFilter(StrFilter):
    """Filter for all uuid fields which are mostly treated like strings."""

    @field_validator("value", mode="before")
    @classmethod
    def _remove_hyphens_from_value(cls, value: Any) -> Any:
        """Remove hyphens from the value to enable string comparisons.

        Args:
            value: The filter value.

        Returns:
            The filter value with removed hyphens.
        """
        if isinstance(value, str):
            return value.replace("-", "")

        if isinstance(value, list):
            return [str(v).replace("-", "") for v in value]

        return value

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

        if self.operation == GenericFilterOps.NOT_EQUALS:
            return column != self.value

        # For all other operations, cast and handle the column as string
        return super().generate_query_conditions_from_column(
            column=cast_if(column, sqlalchemy.String)
        )


class NumericFilter(Filter):
    """Filter for all numeric fields."""

    value: Union[float, datetime] = Field(union_mode="left_to_right")

    ALLOWED_OPS: ClassVar[List[str]] = [
        GenericFilterOps.EQUALS,
        GenericFilterOps.NOT_EQUALS,
        GenericFilterOps.GT,
        GenericFilterOps.GTE,
        GenericFilterOps.LT,
        GenericFilterOps.LTE,
    ]

    def generate_query_conditions_from_column(self, column: Any) -> Any:
        """Generate query conditions for a numeric column.

        Args:
            column: The numeric column of an SQLModel table on which to filter.

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
        if self.operation == GenericFilterOps.NOT_EQUALS:
            return column != self.value
        return column == self.value


class DatetimeFilter(Filter):
    """Filter for all datetime fields."""

    value: Union[datetime, Tuple[datetime, datetime]] = Field(
        union_mode="left_to_right"
    )

    ALLOWED_OPS: ClassVar[List[str]] = [
        GenericFilterOps.EQUALS,
        GenericFilterOps.NOT_EQUALS,
        GenericFilterOps.GT,
        GenericFilterOps.GTE,
        GenericFilterOps.LT,
        GenericFilterOps.LTE,
        GenericFilterOps.IN,
    ]

    def generate_query_conditions_from_column(self, column: Any) -> Any:
        """Generate query conditions for a datetime column.

        Args:
            column: The datetime column of an SQLModel table on which to filter.

        Returns:
            A list of query conditions.
        """
        if self.operation == GenericFilterOps.IN:
            assert isinstance(self.value, tuple)
            lower_bound, upper_bound = self.value
            return column.between(lower_bound, upper_bound)

        assert isinstance(self.value, datetime)
        if self.operation == GenericFilterOps.GTE:
            return column >= self.value
        if self.operation == GenericFilterOps.GT:
            return column > self.value
        if self.operation == GenericFilterOps.LTE:
            return column <= self.value
        if self.operation == GenericFilterOps.LT:
            return column < self.value
        if self.operation == GenericFilterOps.NOT_EQUALS:
            return column != self.value
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
    CUSTOM_SORTING_OPTIONS: ClassVar[List[str]] = []

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
        default=None,
        description="Id for this resource",
        union_mode="left_to_right",
    )
    created: Optional[Union[datetime, str]] = Field(
        default=None, description="Created", union_mode="left_to_right"
    )
    updated: Optional[Union[datetime, str]] = Field(
        default=None, description="Updated", union_mode="left_to_right"
    )

    _rbac_configuration: Optional[
        Tuple[UUID, Dict[str, Optional[Set[UUID]]]]
    ] = None

    @field_validator("sort_by", mode="before")
    @classmethod
    def validate_sort_by(cls, value: Any) -> Any:
        """Validate that the sort_column is a valid column with a valid operand.

        Args:
            value: The sort_by field value.

        Returns:
            The validated sort_by field value.

        Raises:
            ValidationError: If the sort_by field is not a string.
            ValueError: If the resource can't be sorted by this field.
        """
        # Somehow pydantic allows you to pass in int values, which will be
        #  interpreted as string, however within the validator they are still
        #  integers, which don't have a .split() method
        if not isinstance(value, str):
            raise ValidationError(
                f"str type expected for the sort_by field. "
                f"Received a {type(value)}"
            )
        column = value
        split_value = value.split(":", 1)
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
                value = column

        if column in cls.CUSTOM_SORTING_OPTIONS:
            return value
        elif column in cls.FILTER_EXCLUDE_FIELDS:
            raise ValueError(
                f"This resource can not be sorted by this field: '{value}'"
            )
        if column in cls.model_fields:
            return value
        else:
            raise ValueError(
                "You can only sort by valid fields of this resource"
            )

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def filter_ops(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse incoming filters to ensure all filters are legal.

        Args:
            data: The values of the class.

        Returns:
            The values of the class.
        """
        cls._generate_filter_list(data)
        return data

    @property
    def list_of_filters(self) -> List[Filter]:
        """Converts the class variables into a list of usable Filter Models.

        Returns:
            A list of Filter models.
        """
        return self._generate_filter_list(
            {key: getattr(self, key) for key in self.model_fields}
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
                be applied to all entries in the table.
        """
        self._rbac_configuration = (authenticated_user_id, column_allowed_ids)

    def generate_rbac_filter(
        self,
        table: Type["AnySchema"],
    ) -> Optional["ColumnElement[bool]"]:
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
            filter = FilterGenerator(cls).define_filter(
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

        Raises:
            ValueError: when we try to use the `oneof` operator with the wrong
                value.
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

            if operator == operator.ONEOF:
                try:
                    value = json.loads(value)
                    if not isinstance(value, list):
                        raise ValueError
                except ValueError:
                    raise ValueError(ONEOF_ERROR)

        return value, operator

    def generate_name_or_id_query_conditions(
        self,
        value: Union[UUID, str],
        table: Type["NamedSchema"],
        additional_columns: Optional[List[str]] = None,
    ) -> "ColumnElement[bool]":
        """Generate filter conditions for name or id of a table.

        Args:
            value: The filter value.
            table: The table to filter.
            additional_columns: Additional table columns that should also
                filtered for the given value as part of the or condition.

        Returns:
            The query conditions.
        """
        from sqlmodel import or_

        value, operator = BaseFilter._resolve_operator(value)
        value = str(value)

        conditions = []

        try:
            filter_ = FilterGenerator(table).define_filter(
                column="id", value=value, operator=operator
            )
            conditions.append(filter_.generate_query_conditions(table=table))
        except ValueError:
            # UUID filter with equal operators and no full UUID fail with
            # a ValueError. In this case, we already know that the filter
            # will not produce any result and can simply ignore it.
            pass

        filter_ = FilterGenerator(table).define_filter(
            column="name", value=value, operator=operator
        )
        conditions.append(filter_.generate_query_conditions(table=table))

        for column in additional_columns or []:
            filter_ = FilterGenerator(table).define_filter(
                column=column, value=value, operator=operator
            )
            conditions.append(filter_.generate_query_conditions(table=table))

        return or_(*conditions)

    @staticmethod
    def generate_custom_query_conditions_for_column(
        value: Any,
        table: Type[SQLModel],
        column: str,
    ) -> "ColumnElement[bool]":
        """Generate custom filter conditions for a column of a table.

        Args:
            value: The filter value.
            table: The table which contains the column.
            column: The column name.

        Returns:
            The query conditions.
        """
        value, operator = BaseFilter._resolve_operator(value)
        filter_ = FilterGenerator(table).define_filter(
            column=column, value=value, operator=operator
        )
        return filter_.generate_query_conditions(table=table)

    @property
    def offset(self) -> int:
        """Returns the offset needed for the query on the data persistence layer.

        Returns:
            The offset for the query.
        """
        return self.size * (self.page - 1)

    def generate_filter(
        self, table: Type["AnySchema"]
    ) -> Union["ColumnElement[bool]"]:
        """Generate the filter for the query.

        Args:
            table: The Table that is being queried from.

        Returns:
            The filter expression for the query.

        Raises:
            RuntimeError: If a valid logical operator is not supplied.
        """
        from sqlmodel import and_, or_

        filters = []
        for column_filter in self.list_of_filters:
            filters.append(
                column_filter.generate_query_conditions(table=table)
            )
        for custom_filter in self.get_custom_filters(table):
            filters.append(custom_filter)
        if self.logical_operator == LogicalOperators.OR:
            return or_(False, *filters)
        elif self.logical_operator == LogicalOperators.AND:
            return and_(True, *filters)
        else:
            raise RuntimeError("No valid logical operator was supplied.")

    def get_custom_filters(
        self, table: Type["AnySchema"]
    ) -> List["ColumnElement[bool]"]:
        """Get custom filters.

        This can be overridden by subclasses to define custom filters that are
        not based on the columns of the underlying table.

        Args:
            table: The query table.

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

    def apply_sorting(
        self,
        query: AnyQuery,
        table: Type["AnySchema"],
    ) -> AnyQuery:
        """Apply sorting to the query.

        Args:
            query: The query to which to apply the sorting.
            table: The query table.

        Returns:
            The query with sorting applied.
        """
        column, operand = self.sorting_params

        if operand == SorterOps.DESCENDING:
            sort_clause = desc(getattr(table, column))  # type: ignore[var-annotated]
        else:
            sort_clause = asc(getattr(table, column))

        # We always add the `id` column as a tiebreaker to ensure a stable,
        # repeatable order of items, otherwise subsequent pages might contain
        # the same items.
        query = query.order_by(sort_clause, asc(table.id))  # type: ignore[arg-type]

        return query


class FilterGenerator:
    """Helper class to define filters for a class."""

    def __init__(self, model_class: Type[BaseModel]) -> None:
        """Initialize the object.

        Args:
            model_class: The model class for which to define filters.
        """
        self._model_class = model_class

    def define_filter(
        self, column: str, value: Any, operator: GenericFilterOps
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
        if self.is_datetime_field(column):
            return self._define_datetime_filter(
                column=column,
                value=value,
                operator=operator,
            )

        # Create UUID filters
        if self.is_uuid_field(column):
            return self._define_uuid_filter(
                column=column,
                value=value,
                operator=operator,
            )

        # Create int filters
        if self.is_int_field(column):
            return NumericFilter(
                operation=GenericFilterOps(operator),
                column=column,
                value=int(value),
            )

        # Create bool filters
        if self.is_bool_field(column):
            return self._define_bool_filter(
                column=column,
                value=value,
                operator=operator,
            )

        # Create str filters
        if self.is_str_field(column):
            return self._define_str_filter(
                operator=GenericFilterOps(operator),
                column=column,
                value=value,
            )

        # Handle unsupported datatypes
        logger.warning(
            f"The Datatype {self._model_class.model_fields[column].annotation} "
            "might not be supported for filtering. Defaulting to a string "
            "filter."
        )
        return StrFilter(
            operation=GenericFilterOps(operator),
            column=column,
            value=str(value),
        )

    def check_field_annotation(self, k: str, type_: Any) -> bool:
        """Checks whether a model field has a certain annotation.

        Args:
            k: The name of the field.
            type_: The type to check.

        Raises:
            ValueError: if the model field within does not have an annotation.

        Returns:
            True if the annotation of the field matches the given type, False
            otherwise.
        """
        try:
            annotation = self._model_class.model_fields[k].annotation

            if annotation is not None:
                return (
                    issubclass(type_, get_args(annotation))
                    or annotation is type_
                )
            else:
                raise ValueError(
                    f"The field '{k}' inside the model {self._model_class.__name__} "
                    "does not have an annotation."
                )
        except TypeError:
            return False

    def is_datetime_field(self, k: str) -> bool:
        """Checks if it's a datetime field.

        Args:
            k: The key to check.

        Returns:
            True if the field is a datetime field, False otherwise.
        """
        return self.check_field_annotation(k=k, type_=datetime)

    def is_uuid_field(self, k: str) -> bool:
        """Checks if it's a UUID field.

        Args:
            k: The key to check.

        Returns:
            True if the field is a UUID field, False otherwise.
        """
        return self.check_field_annotation(k=k, type_=UUID)

    def is_int_field(self, k: str) -> bool:
        """Checks if it's an int field.

        Args:
            k: The key to check.

        Returns:
            True if the field is an int field, False otherwise.
        """
        return self.check_field_annotation(k=k, type_=int)

    def is_bool_field(self, k: str) -> bool:
        """Checks if it's a bool field.

        Args:
            k: The key to check.

        Returns:
            True if the field is a bool field, False otherwise.
        """
        return self.check_field_annotation(k=k, type_=bool)

    def is_str_field(self, k: str) -> bool:
        """Checks if it's a string field.

        Args:
            k: The key to check.

        Returns:
            True if the field is a string field, False otherwise.
        """
        return self.check_field_annotation(k=k, type_=str)

    def is_sort_by_field(self, k: str) -> bool:
        """Checks if it's a sort by field.

        Args:
            k: The key to check.

        Returns:
            True if the field is a sort by field, False otherwise.
        """
        return self.check_field_annotation(k=k, type_=str) and k == "sort_by"

    @staticmethod
    def _define_datetime_filter(
        column: str, value: Any, operator: GenericFilterOps
    ) -> DatetimeFilter:
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
            filter_value: Union[datetime, Tuple[datetime, datetime]]
            if isinstance(value, datetime):
                filter_value = value
            elif "," in value:
                lower_bound, upper_bound = value.split(",", 1)
                filter_value = (
                    datetime.strptime(lower_bound, FILTERING_DATETIME_FORMAT),
                    datetime.strptime(upper_bound, FILTERING_DATETIME_FORMAT),
                )
            else:
                filter_value = datetime.strptime(
                    value, FILTERING_DATETIME_FORMAT
                )
        except ValueError as e:
            raise ValueError(
                "The datetime filter only works with values in the following "
                f"format: {FILTERING_DATETIME_FORMAT}"
            ) from e

        if operator == GenericFilterOps.IN and not isinstance(
            filter_value, tuple
        ):
            raise ValueError(
                "Two comma separated datetime values are required for the `in` "
                "operator."
            )

        if operator != GenericFilterOps.IN and not isinstance(
            filter_value, datetime
        ):
            raise ValueError(
                "Only a single datetime value is allowed for operator "
                f"{operator}."
            )

        datetime_filter = DatetimeFilter(
            operation=GenericFilterOps(operator),
            column=column,
            value=filter_value,
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

        # For equality checks, ensure that the value is a valid UUID.
        if operator == GenericFilterOps.ONEOF and not isinstance(value, list):
            raise ValueError(ONEOF_ERROR)

        # Generate the filter.
        uuid_filter = UUIDFilter(
            operation=GenericFilterOps(operator),
            column=column,
            value=value,
        )
        return uuid_filter

    @staticmethod
    def _define_str_filter(
        column: str, value: Any, operator: GenericFilterOps
    ) -> StrFilter:
        """Define a str filter for a given column.

        Args:
            column: The column to filter on.
            value: The UUID value by which to filter.
            operator: The operator to use for filtering.

        Returns:
            A Filter object.

        Raises:
            ValueError: If the value is not a proper value.
        """
        # For equality checks, ensure that the value is a valid UUID.
        if operator == GenericFilterOps.ONEOF and not isinstance(value, list):
            raise ValueError(
                "If you are using `oneof:` as a filtering op, the value needs "
                "to be a json formatted list string."
            )

        # Generate the filter.
        str_filter = StrFilter(
            operation=GenericFilterOps(operator),
            column=column,
            value=value,
        )
        return str_filter

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
