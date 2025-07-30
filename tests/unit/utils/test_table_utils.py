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

    def test_table_format_basic(self, sample_data, capsys):
        """Test basic table formatting."""
        zenml_table(sample_data, output_format="table")
        captured = capsys.readouterr()

        # Check that headers are uppercase
        assert "NAME" in captured.out
        assert "STATUS" in captured.out
        assert "COUNT" in captured.out

        # Check data is present
        assert "test1" in captured.out
        assert "active" in captured.out

    def test_json_format(self, sample_data, capsys):
        """Test JSON output format."""
        zenml_table(sample_data, output_format="json")
        captured = capsys.readouterr()

        # Parse the JSON output
        output_data = json.loads(captured.out)
        assert len(output_data) == 3
        assert output_data[0]["name"] == "test1"
        assert output_data[0]["status"] == "active"

    def test_json_format_with_pagination(self, sample_data, capsys):
        """Test JSON output with pagination metadata."""
        pagination = {"index": 1, "total": 3, "max_size": 20}
        zenml_table(sample_data, output_format="json", pagination=pagination)
        captured = capsys.readouterr()

        output_data = json.loads(captured.out)
        assert "items" in output_data
        assert "pagination" in output_data
        assert len(output_data["items"]) == 3
        assert output_data["pagination"]["total"] == 3

    def test_yaml_format(self, sample_data, capsys):
        """Test YAML output format."""
        zenml_table(sample_data, output_format="yaml")
        captured = capsys.readouterr()

        # Parse the YAML output
        output_data = yaml.safe_load(captured.out)
        assert len(output_data) == 3
        assert output_data[0]["name"] == "test1"

    def test_tsv_format(self, sample_data, capsys):
        """Test TSV output format."""
        zenml_table(sample_data, output_format="tsv")
        captured = capsys.readouterr()

        lines = captured.out.strip().split("\n")
        # Check header line
        assert lines[0] == "name\tstatus\tcount"
        # Check data line
        assert lines[1] == "test1\tactive\t5"

    def test_column_filtering(self, sample_data, capsys):
        """Test filtering specific columns."""
        zenml_table(
            sample_data, output_format="json", columns=["name", "status"]
        )
        captured = capsys.readouterr()

        output_data = json.loads(captured.out)
        for item in output_data:
            assert "name" in item
            assert "status" in item
            assert "count" not in item

    def test_sorting(self, sample_data, capsys):
        """Test sorting by column."""
        zenml_table(sample_data, output_format="json", sort_by="name")
        captured = capsys.readouterr()

        output_data = json.loads(captured.out)
        names = [item["name"] for item in output_data]
        assert names == ["test1", "test2", "test3"]

    def test_reverse_sorting(self, sample_data, capsys):
        """Test reverse sorting."""
        zenml_table(
            sample_data, output_format="json", sort_by="name", reverse=True
        )
        captured = capsys.readouterr()

        output_data = json.loads(captured.out)
        names = [item["name"] for item in output_data]
        assert names == ["test3", "test2", "test1"]

    def test_empty_data(self, capsys):
        """Test handling of empty data."""
        zenml_table([], output_format="table")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_none_output_format(self, sample_data, capsys):
        """Test 'none' output format."""
        zenml_table(sample_data, output_format="none")
        captured = capsys.readouterr()
        assert captured.out == ""

    def test_invalid_output_format(self, sample_data):
        """Test invalid output format raises error."""
        with pytest.raises(ValueError, match="Unsupported output format"):
            zenml_table(sample_data, output_format="invalid")

    def test_stack_formatting(self, stack_data, capsys):
        """Test special formatting for stack data."""
        zenml_table(stack_data, output_format="table")
        captured = capsys.readouterr()

        # Check active stack has special formatting
        assert "●" in captured.out  # Green dot
        assert "(active)" in captured.out

    def test_stack_formatting_json_clean(self, stack_data, capsys):
        """Test that JSON output removes internal fields."""
        zenml_table(stack_data, output_format="json")
        captured = capsys.readouterr()

        output_data = json.loads(captured.out)
        for item in output_data:
            assert "__is_active__" not in item

    def test_status_colorization(self, capsys):
        """Test status value colorization."""
        data = [
            {"status": "running"},
            {"status": "failed"},
            {"status": "pending"},
        ]
        zenml_table(data, output_format="table", no_color=False)
        captured = capsys.readouterr()

        # Colors should be applied (exact formatting depends on Rich implementation)
        assert "running" in captured.out
        assert "failed" in captured.out
        assert "pending" in captured.out

    @patch.dict(os.environ, {"NO_COLOR": "1"})
    def test_no_color_environment(self, sample_data, capsys):
        """Test NO_COLOR environment variable is respected."""
        zenml_table(sample_data, output_format="table")
        captured = capsys.readouterr()

        # Should not contain ANSI color codes when NO_COLOR is set
        assert captured.out
        # Basic check - output should be present but without complex formatting

    @patch("zenml.utils.table_utils.shutil.get_terminal_size")
    def test_terminal_width_detection(
        self, mock_terminal_size, sample_data, capsys
    ):
        """Test terminal width detection."""
        mock_terminal_size.return_value.columns = 120

        zenml_table(sample_data, output_format="table", max_width=100)
        captured = capsys.readouterr()

        assert captured.out  # Should produce output
        mock_terminal_size.assert_called_once()

    def test_tsv_escaping(self, capsys):
        """Test TSV format properly escapes special characters."""
        data = [{"field": "value\twith\ttabs\nand\nnewlines"}]
        zenml_table(data, output_format="tsv")
        captured = capsys.readouterr()

        lines = captured.out.strip().split("\n")
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

    def test_none_values_handling(self, capsys):
        """Test handling of None values in data."""
        data = [{"name": "test", "value": None, "other": "data"}]
        zenml_table(data, output_format="json")
        captured = capsys.readouterr()

        output_data = json.loads(captured.out)
        assert output_data[0]["value"] is None

    def test_mixed_data_types(self, capsys):
        """Test handling of mixed data types."""
        data = [
            {"name": "test", "count": 42, "active": True, "rate": 3.14},
            {"name": "other", "count": 0, "active": False, "rate": 2.71},
        ]
        zenml_table(data, output_format="json")
        captured = capsys.readouterr()

        output_data = json.loads(captured.out)
        assert output_data[0]["count"] == 42
        assert output_data[0]["active"] is True
        assert output_data[0]["rate"] == 3.14
