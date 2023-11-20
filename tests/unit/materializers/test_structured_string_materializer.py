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
"""Unit tests for the `HTMLMarkdownMaterializer`."""

from tests.unit.test_general import _test_materializer
from zenml.materializers.structured_string_materializer import (
    StructuredStringMaterializer,
)
from zenml.types import CSVString, HTMLString, MarkdownString


def test_structured_string_materializer_for_csv_strings(clean_workspace):
    """Test the `StructuredStringMaterializer` for CSV strings."""

    _test_materializer(
        step_output=CSVString("a,b,c\n1,2,3"),
        materializer_class=StructuredStringMaterializer,
        assert_visualization_exists=True,
    )


def test_structured_string_materializer_for_html_strings(clean_workspace):
    """Test the `StructuredStringMaterializer` for HTML strings."""

    _test_materializer(
        step_output=HTMLString("<h1>ARIA</h1>"),
        materializer_class=StructuredStringMaterializer,
        assert_visualization_exists=True,
    )


def test_structured_string_materializer_for_markdown_strings(clean_workspace):
    """Test the `StructuredStringMaterializer` for Markdown strings."""

    _test_materializer(
        step_output=MarkdownString("# ARIA"),
        materializer_class=StructuredStringMaterializer,
        assert_visualization_exists=True,
    )
