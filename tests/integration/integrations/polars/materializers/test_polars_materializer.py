#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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


import polars
from polars import testing as polars_testing

from tests.unit.test_general import _test_materializer
from zenml.integrations.polars.materializers.dataframe_materializer import (
    PolarsMaterializer,
)


def test_polars_materializer():
    """Test the polars materializer."""
    dataframe = polars.DataFrame([0, 1, 2, 3], schema=["column_test"])
    series = polars.Series([0, 1, 2, 3])

    for type_, example in [
        (polars.DataFrame, dataframe),
        (polars.Series, series),
    ]:
        result = _test_materializer(
            step_output_type=type_,
            materializer_class=PolarsMaterializer,
            step_output=example,
            assert_visualization_exists=False,
        )

        # Use different assertion given type, since Polars implements
        # these differently.
        if type_ == polars.DataFrame:
            polars_testing.assert_frame_equal(example, result)
        else:
            polars_testing.assert_series_equal(example, result)
