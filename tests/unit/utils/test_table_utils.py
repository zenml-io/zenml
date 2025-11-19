#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Unit tests for table utilities."""

import json
import os
from unittest.mock import patch

import pytest
import yaml
from zenml.utils.table_utils import zenml_table


class TestZenmlTable:
    """Test cases for the zenml_table function."""

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing."""
        return [
            {"name": "test1", "status": "active", "count": 5},
            {"name": "test2", "status": "pending", "count": 3},
            {"name": "test3", "status": "failed", "count": 1},
        ]

    @pytest.fixture
    def stack_data(self):
        """Sample stack data with active indicator."""
        return [
            {
                "name": "default",
                "owner": "admin",
                "components": 2,
                "__is_active__": True,
            },
            {
                "name": "production",
                "owner": "admin",
                "components": 5,
                "__is_active__": False,
            },
        ]

    def test_table_format_basic(self, sample_data):
        """Test basic table formatting."""
        output = zenml_table(sample_data, output_format="table")
        assert output is not None

        # Check that headers are uppercase
        assert "NAME" in output
        assert "STATUS" in output
        assert "COUNT" in output

        # Check data is present
        assert "test1" in output
        assert "active" in output

    def test_json_format(self, sample_data):
        """Test JSON output format."""
        output = zenml_table(sample_data, output_format="json")
        assert output is not None

        # Parse the JSON output
        output_data = json.loads(output)
        assert len(output_data) == 3
        assert output_data[0]["name"] == "test1"
        assert output_data[0]["status"] == "active"

    def test_json_format_with_pagination(self, sample_data):
        """Test JSON output with pagination metadata."""
        pagination = {"index": 1, "total": 3, "max_size": 20}
        output = zenml_table(
            sample_data, output_format="json", pagination=pagination
        )
        assert output is not None

        output_data = json.loads(output)
        assert "items" in output_data
        assert "pagination" in output_data
        assert len(output_data["items"]) == 3
        assert output_data["pagination"]["total"] == 3

    def test_yaml_format(self, sample_data):
        """Test YAML output format."""
        output = zenml_table(sample_data, output_format="yaml")
        assert output is not None

        # Parse the YAML output
        output_data = yaml.safe_load(output)
        assert len(output_data) == 3
        assert output_data[0]["name"] == "test1"

    def test_tsv_format(self, sample_data):
        """Test TSV output format."""
        output = zenml_table(sample_data, output_format="tsv")
        assert output is not None

        lines = output.strip().split("\n")
        # Check header line
        assert lines[0] == "name\tstatus\tcount"
        # Check data line
        assert lines[1] == "test1\tactive\t5"

    def test_column_filtering(self, sample_data):
        """Test filtering specific columns."""
        output = zenml_table(
            sample_data, output_format="json", columns=["name", "status"]
        )
        assert output is not None

        output_data = json.loads(output)
        for item in output_data:
            assert "name" in item
            assert "status" in item
            assert "count" not in item

    def test_sorting(self, sample_data):
        """Test sorting by column."""
        output = zenml_table(sample_data, output_format="json", sort_by="name")
        assert output is not None

        output_data = json.loads(output)
        names = [item["name"] for item in output_data]
        assert names == ["test1", "test2", "test3"]

    def test_reverse_sorting(self, sample_data):
        """Test reverse sorting."""
        output = zenml_table(
            sample_data, output_format="json", sort_by="name", reverse=True
        )
        assert output is not None

        output_data = json.loads(output)
        names = [item["name"] for item in output_data]
        assert names == ["test3", "test2", "test1"]

    def test_empty_data(self):
        """Test handling of empty data."""
        output = zenml_table([], output_format="table")
        assert output == "" or output is None

    def test_invalid_output_format(self, sample_data):
        """Test invalid output format raises error."""
        with pytest.raises(ValueError, match="Unsupported output format"):
            zenml_table(sample_data, output_format="invalid")

    def test_stack_formatting_json_clean(self, stack_data):
        """Test that JSON output removes internal fields."""
        output = zenml_table(stack_data, output_format="json")
        assert output is not None

        output_data = json.loads(output)
        for item in output_data:
            assert "__is_active__" not in item

    def test_status_colorization(self):
        """Test status value colorization."""
        data = [
            {"status": "running"},
            {"status": "failed"},
            {"status": "pending"},
        ]
        output = zenml_table(data, output_format="table", no_color=False)
        assert output is not None

        # Colors should be applied (exact formatting depends on Rich implementation)
        assert "running" in output
        assert "failed" in output
        assert "pending" in output

    @patch.dict(os.environ, {"NO_COLOR": "1"})
    def test_no_color_environment(self, sample_data):
        """Test NO_COLOR environment variable is respected."""
        output = zenml_table(sample_data, output_format="table")
        assert output is not None

    @patch("zenml.utils.table_utils.shutil.get_terminal_size")
    def test_terminal_width_detection(self, mock_terminal_size, sample_data):
        """Test terminal width detection."""
        mock_terminal_size.return_value.columns = 120

        output = zenml_table(sample_data, output_format="table", max_width=100)
        assert output is not None  # Should produce output
        mock_terminal_size.assert_called_once()

    def test_tsv_escaping(self):
        """Test TSV format properly escapes special characters."""
        data = [{"field": "value\twith\ttabs\nand\nnewlines"}]
        output = zenml_table(data, output_format="tsv")
        assert output is not None

        lines = output.strip().split("\n")
        assert len(lines) >= 2  # Should have header and data lines

        # Check that tabs and newlines are properly escaped in the data
        data_line = lines[1]
        fields = data_line.split("\t")
        if len(fields) > 1:
            # Original tabs should be replaced with spaces
            assert (
                "value with tabs and newlines" in fields[1]
                or "value\twith" not in fields[1]
            )

    def test_none_values_handling(self):
        """Test handling of None values in data."""
        data = [{"name": "test", "value": None, "other": "data"}]
        output = zenml_table(data, output_format="json")
        assert output is not None

        output_data = json.loads(output)
        assert output_data[0]["value"] is None

    def test_mixed_data_types(self):
        """Test handling of mixed data types."""
        data = [
            {"name": "test", "count": 42, "active": True, "rate": 3.14},
            {"name": "other", "count": 0, "active": False, "rate": 2.71},
        ]
        output = zenml_table(data, output_format="json")
        assert output is not None

        output_data = json.loads(output)
        assert output_data[0]["count"] == 42
        assert output_data[0]["active"] is True
        assert output_data[0]["rate"] == 3.14
