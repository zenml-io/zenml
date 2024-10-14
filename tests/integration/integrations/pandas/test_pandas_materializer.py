#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import datetime

import pandas

from tests.unit.test_general import _test_materializer
from zenml.integrations.pandas.materializers.pandas_materializer import (
    PandasMaterializer,
)


def test_pandas_materializer():
    """Test the pandas materializer."""
    dataframe = pandas.DataFrame([0, 1, 2, 3], columns=["column_test"])
    series = pandas.Series([0, 1, 2, 3])

    for type_, example in [
        (pandas.DataFrame, dataframe),
        (pandas.Series, series),
    ]:
        result = _test_materializer(
            step_output_type=type_,
            materializer_class=PandasMaterializer,
            step_output=example,
            expected_metadata_size=7,
            assert_visualization_exists=True,
        )
        assert example.equals(result)


def test_pandas_materializer_with_index():
    """Test the pandas Dataframe materializer with indices."""
    # Test with a DataFrame with a string index
    df_string_indexed = pandas.DataFrame(
        {"A": [1, 2, 3], "B": [4, 5, 6]}, index=["a", "b", "c"]
    )
    result = _test_materializer(
        step_output_type=pandas.DataFrame,
        materializer_class=PandasMaterializer,
        step_output=df_string_indexed,
        expected_metadata_size=7,
        assert_visualization_exists=True,
    )
    assert df_string_indexed.equals(result)

    # Test with a Series with a string index
    series_string_indexed = pandas.Series([1, 2, 3], index=["a", "b", "c"])
    result = _test_materializer(
        step_output_type=pandas.Series,
        materializer_class=PandasMaterializer,
        step_output=series_string_indexed,
        expected_metadata_size=7,
        assert_visualization_exists=True,
    )
    assert series_string_indexed.equals(result)

    # Test with a Series with a datetime index
    series_datetime_indexed = pandas.Series(
        [1, 2, 3],
        index=[
            datetime.datetime(2022, 1, 1),
            datetime.datetime(2022, 1, 2),
            datetime.datetime(2022, 1, 3),
        ],
    )
    result = _test_materializer(
        step_output_type=pandas.Series,
        materializer_class=PandasMaterializer,
        step_output=series_datetime_indexed,
        expected_metadata_size=7,
        assert_visualization_exists=True,
    )
    assert series_datetime_indexed.equals(result)

    # Test with a DataFrame with a datetime index
    df_datetime_indexed = pandas.DataFrame(
        {"A": [1, 2, 3], "B": [4, 5, 6]},
        index=[
            datetime.datetime(2022, 1, 1),
            datetime.datetime(2022, 1, 2),
            datetime.datetime(2022, 1, 3),
        ],
    )
    result = _test_materializer(
        step_output_type=pandas.DataFrame,
        materializer_class=PandasMaterializer,
        step_output=df_datetime_indexed,
        expected_metadata_size=7,
        assert_visualization_exists=True,
    )
    assert df_datetime_indexed.equals(result)
