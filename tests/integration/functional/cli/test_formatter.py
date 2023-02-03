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

from zenml.cli.formatter import ZenFormatter, measure_table


def test_write_zen_dl() -> None:
    """
    Test the write_zen_dl function.
    """
    custom_formatter = ZenFormatter(indent_increment=2)
    custom_formatter.indent()
    rows = [("a", "b", "c"), ("d", "e", "f")]
    custom_formatter.write_dl(rows, col_max=30, col_spacing=2)
    assert custom_formatter.buffer == [
        "\n",
        "[#431d93]  a:[/#431d93]\n",
        "    ",
        "  b",
        "      ",
        "c\n",
        "\n",
        "[#431d93]  d:[/#431d93]\n",
        "    ",
        "  e",
        "      ",
        "f\n",
    ]


def test_measure_table() -> None:
    """
    Test the measure_table function.
    """
    rows = [("a", "b", "c"), ("d", "e", "f")]
    assert measure_table(rows) == (1, 1, 1)
    rows = [("a", "b"), ("cd", "efg")]
    assert measure_table(rows) == (2, 3)
