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

import pandas

from tests.unit.test_general import _test_materializer
from zenml.materializers.pandas_materializer import PandasMaterializer


def test_pandas_materializer():

    dataframe = pandas.DataFrame(
        [0, 1, 2, 3], columns=['column_test']
    )
    series = pandas.Series([0, 1, 2, 3])

    for type_, example in [
        (pandas.DataFrame, dataframe),
        (pandas.Series, series),
    ]:
        result = _test_materializer(step_output_type=type_, materializer_class=PandasMaterializer, step_output=example)
        assert example.equals(result)
