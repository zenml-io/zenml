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
from typing import Any, Optional, Union
from uuid import UUID

import pytest
from pydantic.error_wrappers import ValidationError

from zenml.constants import FILTERING_DATETIME_FORMAT
from zenml.enums import GenericFilterOps
from zenml.models import FilterBaseModel
from zenml.models.filter_models import (
    NumericFilter,
    StrFilter,
    UUIDFilter,
)


class TestFilterModel(FilterBaseModel):

    uuid_field: Optional[Union[UUID, str]]
    datetime_field: Optional[Union[datetime, str]]
    int_field: Optional[Union[int, str]]
    str_field: Optional[str]


@pytest.mark.parametrize("wrong_page_value", [0, -4, 0.21, "catfood"])
def test_filter_model_page_not_int_gte1_fails(wrong_page_value: Any):
    """Test that the filter model page field enforces int >= 1"""
    with pytest.raises(ValidationError):
        FilterBaseModel(page=wrong_page_value)


@pytest.mark.parametrize("wrong_page_value", [0, -4, 0.21, "catfood"])
def test_filter_model_size_not_int_gte1_fails(wrong_page_value: Any):
    """Test that the filter model size field enforces int >= 1"""
    with pytest.raises(ValidationError):
        FilterBaseModel(size=wrong_page_value)


@pytest.mark.parametrize(
    "correct_sortable_column", ["created", "updated", "id"]
)
def test_filter_model_sort_by_for_existing_field_succeeds(
    correct_sortable_column: Any,
):
    """Test that the filter model sort_by field enforces valid filter fields"""
    FilterBaseModel(sort_by=correct_sortable_column)
    assert FilterBaseModel(sort_by=correct_sortable_column).sort_by


@pytest.mark.parametrize(
    "correct_sortable_column", ["catastic_column", "zenml", "page", 1]
)
def test_filter_model_sort_by_for_non_filter_fields_fails(
    correct_sortable_column: Any,
):
    """Test that the filter model sort_by field enforces valid filter fields"""
    with pytest.raises(ValidationError):
        FilterBaseModel(sort_by=correct_sortable_column)


def test_filter_model_datetime_fields_accept_correct_filter_ops():
    """Test that the flavor base model fails with long names."""
    for filter_op in GenericFilterOps.values():
        if filter_op in NumericFilter.ALLOWED_OPS:
            datetime_value = "22-12-12 08:00:00"
            model_instance = TestFilterModel(
                datetime_field=f"{filter_op}:{datetime_value}"
            )
            assert model_instance.list_of_filters[0]
            assert model_instance.list_of_filters[0].operation == filter_op
            assert model_instance.list_of_filters[
                0
            ].value == datetime.strptime(
                datetime_value, FILTERING_DATETIME_FORMAT
            )
            assert model_instance.list_of_filters[0].column == "datetime_field"
        else:
            # Fail if wrong filter ops are used (e.g. contains)
            datetime_value = "22-12-12 08:00:00"
            with pytest.raises(ValueError):
                TestFilterModel(datetime_field=f"{filter_op}:{datetime_value}")


@pytest.mark.parametrize(
    "false_format_datetime", ["2022/12/12 12-12-12", "notadate", 1]
)
def test_filter_model_datetime_with_wrong_format_fails(
    false_format_datetime: str,
):
    """Test that the flavor base model fails with long names."""
    with pytest.raises(ValueError):
        TestFilterModel(datetime_field=false_format_datetime)
    for filter_op in GenericFilterOps.values():
        with pytest.raises(ValueError):
            TestFilterModel(
                datetime_field=f"{filter_op}:{false_format_datetime}"
            )


def test_filter_model_int_fields_accept_correct_filter_ops():
    """Test that the flavor base model fails with long names."""
    for filter_op in GenericFilterOps.values():
        if filter_op in NumericFilter.ALLOWED_OPS:
            int_value = 3
            model_instance = TestFilterModel(
                int_field=f"{filter_op}:{int_value}"
            )
            assert model_instance.list_of_filters[0]
            assert model_instance.list_of_filters[0].operation == filter_op
            assert model_instance.list_of_filters[0].value == int_value
            assert model_instance.list_of_filters[0].column == "int_field"
        else:
            # Fail if wrong filter ops are used (e.g. contains)
            int_value = 3
            with pytest.raises(ValueError):
                TestFilterModel(int_field=f"{filter_op}:{int_value}")


def test_filter_model_uuid_fields_accept_correct_filter_ops():
    """Test that the flavor base model fails with long names."""

    for filter_op in GenericFilterOps.values():
        if filter_op in UUIDFilter.ALLOWED_OPS:
            if filter_op == GenericFilterOps.EQUALS:
                uuid_value = uuid.uuid4()
                model_instance = TestFilterModel(
                    uuid_field=f"{filter_op}:{uuid_value}"
                )
            else:
                uuid_value = "a92k34"
                model_instance = TestFilterModel(
                    uuid_field=f"{filter_op}:{uuid_value}"
                )
            assert model_instance.list_of_filters[0]
            assert model_instance.list_of_filters[0].operation == filter_op
            assert model_instance.list_of_filters[0].value == uuid_value
            assert model_instance.list_of_filters[0].column == "uuid_field"
        else:
            # Fail if wrong filter_ops are used (e.g. LTE)
            with pytest.raises(ValueError):
                uuid_value = "a92k34"
                TestFilterModel(uuid_field=f"{filter_op}:{uuid_value}")


def test_filter_model_uuid_fields_equality_with_invalid_uuid_fails():
    """Test filtering for equality with invalid UUID fails."""

    with pytest.raises(ValueError):
        uuid_value = "a92k34"
        TestFilterModel(uuid_field=f"{GenericFilterOps.EQUALS}:{uuid_value}")


def test_filter_model_string_fields_accept_correct_filter_ops():
    """Test that the flavor base model fails with long names."""

    class StrFilterModel(FilterBaseModel):
        str_field: str

    for filter_op in GenericFilterOps.values():
        if filter_op in StrFilter.ALLOWED_OPS:
            str_value = "a_random_string"
            model_instance = StrFilterModel(
                str_field=f"{filter_op}:{str_value}"
            )
            assert model_instance.list_of_filters[0]
            assert model_instance.list_of_filters[0].operation == filter_op
            assert model_instance.list_of_filters[0].value == str_value
            assert model_instance.list_of_filters[0].column == "str_field"
        else:
            # Fail if wrong filter_ops are used (e.g. LTE)
            with pytest.raises(ValueError):
                str_value = "a_random_string"
                TestFilterModel(str_field=f"{filter_op}:{str_value}")
