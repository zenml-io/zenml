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
import uuid
from datetime import datetime
from typing import Any, List, Optional, Type, Union
from uuid import UUID

import pytest
from pydantic.error_wrappers import ValidationError

import zenml.exceptions
from zenml.constants import FILTERING_DATETIME_FORMAT
from zenml.enums import GenericFilterOps, SorterOps
from zenml.models.v2.base.filter import (
    BaseFilter,
    DatetimeFilter,
    Filter,
    NumericFilter,
    StrFilter,
    UUIDFilter,
)


class SomeFilterModel(BaseFilter):
    """Test custom filter model with all supported field types."""

    uuid_field: Optional[Union[UUID, str]] = None
    datetime_field: Optional[Union[datetime, str]] = None
    int_field: Optional[Union[int, str]] = None
    str_field: Optional[str] = None


def _test_filter_model(
    filter_field: str,
    filter_class: Type[Filter],
    filter_value: Any,
    expected_value: Optional[Any] = None,
    ignore_operators: Optional[List[GenericFilterOps]] = None,
) -> None:
    """Test filter model creation.

    This creates a `TestFilterModel` with one of its fields set and checks that:
    - Model creation succeeds for compatible filter operations and attributes
        are correctly set afterward.
    - Model creation fails for incompatible filter operations.

    Args:
        filter_field: The field of `TestFilterModel` that should be set.
        filter_class: The `Filter` subclass whose operations are compatible with
            the type of `filter_field`.
        filter_value: The value that `filter_field` should be set to.
        expected_value: The expected value of `list_of_filters[0].value` after
            the model has been created, if different from `filter_value`.
        ignore_operators: Filter operators to ignore.
    """
    ignore_operators = ignore_operators or []
    if expected_value is None:
        expected_value = filter_value

    for filter_op in GenericFilterOps.values():
        if filter_op in ignore_operators:
            continue

        filter_str = f"{filter_op}:{filter_value}"
        filter_kwargs = {filter_field: filter_str}

        # Fail if incompatible filter operations are used.
        if filter_op not in filter_class.ALLOWED_OPS:
            with pytest.raises(ValueError):
                model_instance = SomeFilterModel(**filter_kwargs)
            continue

        # Succeed and correctly set filter attributes for compatible operations.
        model_instance = SomeFilterModel(**filter_kwargs)
        assert len(model_instance.list_of_filters) == 1
        model_filter = model_instance.list_of_filters[0]
        assert isinstance(model_filter, filter_class)
        assert model_filter.operation == filter_op
        assert model_filter.value == expected_value
        assert model_filter.column == filter_field


@pytest.mark.parametrize("wrong_page_value", [0, -4, 0.21, "catfood"])
def test_filter_model_page_not_int_gte1_fails(wrong_page_value: Any):
    """Test that the filter model page field enforces int >= 1"""
    with pytest.raises(ValidationError):
        BaseFilter(page=wrong_page_value)


@pytest.mark.parametrize("wrong_page_value", [0, -4, 0.21, "catfood"])
def test_filter_model_size_not_int_gte1_fails(wrong_page_value: Any):
    """Test that the filter model size field enforces int >= 1"""
    with pytest.raises(ValidationError):
        BaseFilter(size=wrong_page_value)


@pytest.mark.parametrize(
    "correct_sortable_column", ["created", "updated", "id"]
)
def test_filter_model_sort_by_for_existing_field_succeeds(
    correct_sortable_column: Any,
):
    """Test that the filter model sort_by field enforces valid filter fields"""
    filter_model = BaseFilter(sort_by=correct_sortable_column)
    assert filter_model.sort_by == correct_sortable_column
    assert filter_model.sorting_params[0] == correct_sortable_column
    # Assert that the default sorting order is ascending
    assert filter_model.sorting_params[1] == SorterOps.ASCENDING


@pytest.mark.parametrize(
    "correct_sortable_column",
    [
        (SorterOps.DESCENDING, "created"),
        (SorterOps.ASCENDING, "updated"),
        (SorterOps.DESCENDING, "id"),
    ],
)
def test_filter_model_sort_by_existing_field_with_order_succeeds(
    correct_sortable_column: Any,
):
    """Test that the filter model sort_by field enforces correct order"""
    built_query = f"{correct_sortable_column[0]}:{correct_sortable_column[1]}"
    filter_model = BaseFilter(sort_by=built_query)
    assert filter_model.sort_by == built_query
    assert filter_model.sorting_params[0] == correct_sortable_column[1]
    assert filter_model.sorting_params[1] == correct_sortable_column[0]


@pytest.mark.parametrize(
    "correct_sortable_column",
    [("pancakes", "created"), ("", "updated"), (1, "id")],
)
def test_filter_model_sort_by_existing_field_wrong_order_succeeds(
    correct_sortable_column: Any,
):
    """Test that the filter model sort_by field ignores invalid order args"""
    built_query = f"{correct_sortable_column[0]}:{correct_sortable_column[1]}"
    filter_model = BaseFilter(sort_by=built_query)
    assert filter_model.sort_by == correct_sortable_column[1]
    assert filter_model.sorting_params[0] == correct_sortable_column[1]
    assert filter_model.sorting_params[1] == SorterOps.ASCENDING


@pytest.mark.parametrize(
    "incorrect_sortable_column", ["catastic_column", "zenml", "page"]
)
def test_filter_model_sort_by_for_non_filter_fields_fails(
    incorrect_sortable_column: Any,
):
    """Test that the filter model sort_by field enforces valid filter fields"""
    with pytest.raises(ValidationError):
        BaseFilter(sort_by=incorrect_sortable_column)


@pytest.mark.parametrize("incorrect_sortable_column", [1, {1, 2, 3}, int])
def test_filter_model_sort_by_non_str_input_fails(
    incorrect_sortable_column: Any,
):
    """Test that the filter model sort_by field enforces valid filter fields"""
    with pytest.raises(zenml.exceptions.ValidationError):
        BaseFilter(sort_by=incorrect_sortable_column)


def test_datetime_filter_model():
    """Test Filter model creation for datetime fields."""
    filter_value = "2022-12-12 08:00:00"
    expected_value = datetime.strptime(filter_value, FILTERING_DATETIME_FORMAT)
    _test_filter_model(
        filter_field="datetime_field",
        filter_class=DatetimeFilter,
        filter_value=filter_value,
        expected_value=expected_value,
        ignore_operators=[GenericFilterOps.IN],
    )


def test_datetime_filter_in_operator_requires_two_values():
    """Test that the in operator requires two comma separated values."""
    filter_value = "2022-12-12 08:00:00"

    with pytest.raises(ValueError):
        SomeFilterModel(datetime_field=f"{GenericFilterOps.IN}:{filter_value}")

    SomeFilterModel(
        datetime_field=f"{GenericFilterOps.IN}:{filter_value},{filter_value}"
    )


@pytest.mark.parametrize(
    "false_format_datetime", ["2022/12/12 12-12-12", "notadate"]
)
def test_datetime_filter_model_fails_for_wrong_formats(
    false_format_datetime: str,
):
    """Test that filter model creation fails for incorrect datetime formats."""
    with pytest.raises(ValueError):
        SomeFilterModel(datetime_field=false_format_datetime)
    for filter_op in GenericFilterOps.values():
        with pytest.raises(ValueError):
            SomeFilterModel(
                datetime_field=f"{filter_op}:{false_format_datetime}"
            )


def test_int_filter_model():
    """Test Filter model creation for int fields."""
    _test_filter_model(
        filter_field="int_field",
        filter_class=NumericFilter,
        filter_value=3,
    )


def test_uuid_filter_model():
    """Test Filter model creation for UUID fields."""
    filter_value = uuid.uuid4()
    _test_filter_model(
        filter_field="uuid_field",
        filter_class=UUIDFilter,
        filter_value=filter_value,
        expected_value=str(filter_value).replace("-", ""),
    )


def test_uuid_filter_model_fails_for_invalid_uuids_on_equality():
    """Test filtering for equality with invalid UUID fails."""
    with pytest.raises(ValueError):
        uuid_value = "a92k34"
        SomeFilterModel(uuid_field=f"{GenericFilterOps.EQUALS}:{uuid_value}")


def test_uuid_filter_model_succeeds_for_invalid_uuid_on_non_equality():
    """Test filtering with other UUID operations is possible with non-UUIDs."""
    filter_value = "a92k34"
    for filter_op in UUIDFilter.ALLOWED_OPS:
        if filter_op == GenericFilterOps.EQUALS:
            continue
        filter_model = SomeFilterModel(
            uuid_field=f"{filter_op}:{filter_value}"
        )
        assert len(filter_model.list_of_filters) == 1
        model_filter = filter_model.list_of_filters[0]
        assert isinstance(model_filter, UUIDFilter)
        assert model_filter.operation == filter_op
        assert model_filter.value == filter_value
        assert model_filter.column == "uuid_field"


def test_string_filter_model():
    """Test Filter model creation for string fields."""
    _test_filter_model(
        filter_field="str_field",
        filter_class=StrFilter,
        filter_value="a_random_string",
    )
