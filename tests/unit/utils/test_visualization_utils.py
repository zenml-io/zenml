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

import pytest
from bs4 import BeautifulSoup

from zenml.utils.visualization_utils import format_csv_visualization_as_html


@pytest.mark.parametrize("num_rows", list(range(11)))
@pytest.mark.parametrize("num_cols", list(range(11)))
def test_format_small_csv_visualization_as_html(num_rows, num_cols):
    """Test that small CSVs are valid html and not cut off."""
    csv = "\n".join([",".join(["a"] * num_cols)] * num_rows)
    html = format_csv_visualization_as_html(csv)
    if num_rows == 0 or num_cols == 0:
        expected_html = "<table></table>"
    else:
        expected_row = "<tr>" + "<td>a</td>" * num_cols + "</tr>"
        expected_html = "<table>" + expected_row * num_rows + "</table>"
    assert html == expected_html
    BeautifulSoup(html, "html.parser")  # will fail if not valid html


@pytest.mark.parametrize("num_rows", [3, 8, 12, 17])
@pytest.mark.parametrize("num_cols", [3, 8, 12, 17])
@pytest.mark.parametrize("max_rows", [5, 10])
@pytest.mark.parametrize("max_cols", [5, 10])
def test_format_large_csv_visualization_as_html(
    num_rows, num_cols, max_rows, max_cols
):
    """Test that large CSVs are cut off but valid html."""
    csv = "\n".join([",".join(["a"] * num_cols)] * num_rows)
    html = format_csv_visualization_as_html(
        csv, max_rows=max_rows, max_cols=max_cols
    )
    if num_cols > max_cols:
        expected_row = (
            "<tr>" + "<td>a</td>" * max_cols + "<td>...</td>" + "</tr>"
        )
    else:
        expected_row = "<tr>" + "<td>a</td>" * num_cols + "</tr>"

    if num_rows > max_rows:
        expected_html = (
            "<table>"
            + expected_row * (max_rows // 2)
            + "<tr><td>...</td></tr>"
            + expected_row * (max_rows // 2)
            + "</table>"
        )
    else:
        expected_html = "<table>" + expected_row * num_rows + "</table>"
    assert html == expected_html
    BeautifulSoup(html, "html.parser")  # will fail if not valid html
