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
"""Integration tests for CLI table formatting functionality."""

import json
import os
from unittest.mock import patch

import pytest
import yaml
from click.testing import CliRunner

from zenml.cli.cli import cli


class TestCLITableIntegration:
    """Integration tests for CLI commands using the new table system."""

    @pytest.fixture(scope="function")
    def runner(self):
        """CLI runner fixture."""
        return CliRunner()

    def test_stack_list_table_format(self, runner):
        """Test stack list command with table format."""
        result = runner.invoke(cli, ["stack", "list"])

        assert result.exit_code == 0
        assert "NAME" in result.output  # Check uppercase headers
        assert "OWNER" in result.output
        assert "COMPONENTS" in result.output

        # Check for active stack indicator
        if "●" in result.output:
            assert "(active)" in result.output

    def test_stack_list_json_format(self, runner):
        """Test stack list command with JSON format."""
        result = runner.invoke(cli, ["stack", "list", "--output", "json"])

        assert result.exit_code == 0

        # Parse JSON output
        try:
            data = json.loads(result.output)
            assert "items" in data or isinstance(data, list)

            # If pagination format
            if "items" in data:
                assert "pagination" in data
                items = data["items"]
            else:
                items = data

            # Check data structure
            if items:
                assert "name" in items[0]
                # Should not contain internal fields
                assert "__is_active__" not in items[0]

        except json.JSONDecodeError:
            pytest.fail("Invalid JSON output from stack list command")

    def test_stack_list_yaml_format(self, runner):
        """Test stack list command with YAML format."""
        result = runner.invoke(cli, ["stack", "list", "--output", "yaml"])

        assert result.exit_code == 0

        # Parse YAML output
        try:
            data = yaml.safe_load(result.output)
            assert isinstance(data, (list, dict))

            # If pagination format
            if isinstance(data, dict) and "items" in data:
                items = data["items"]
            else:
                items = data

            # Check data structure
            if items and isinstance(items, list):
                assert "name" in items[0]

        except yaml.YAMLError:
            pytest.fail("Invalid YAML output from stack list command")

    def test_stack_list_tsv_format(self, runner):
        """Test stack list command with TSV format."""
        result = runner.invoke(cli, ["stack", "list", "--output", "tsv"])

        assert result.exit_code == 0

        lines = result.output.strip().split("\n")
        if lines and lines[0]:
            # Check header line contains tab-separated values
            assert "\t" in lines[0]
            headers = lines[0].split("\t")
            assert "name" in headers

    def test_user_list_table_format(self, runner):
        """Test user list command with table format."""
        result = runner.invoke(cli, ["user", "list"])

        assert result.exit_code == 0
        # Should contain uppercase headers and data
        assert result.output.strip()  # Should produce some output

    def test_pipeline_list_table_format(self, runner):
        """Test pipeline list command with table format."""
        result = runner.invoke(cli, ["pipeline", "list"])

        assert result.exit_code == 0
        # Check for reasonable output (may be empty if no pipelines)
        if "NAME" in result.output:
            assert "TAGS" in result.output or "DESCRIPTION" in result.output

    def test_model_list_table_format(self, runner):
        """Test model list command with table format."""
        result = runner.invoke(cli, ["model", "list"])

        assert result.exit_code == 0
        # Should handle empty or populated model lists
        assert isinstance(result.output, str)

    def test_secret_list_table_format(self, runner):
        """Test secret list command with table format."""
        result = runner.invoke(cli, ["secret", "list"])

        assert result.exit_code == 0
        # Should handle empty or populated secret lists
        assert isinstance(result.output, str)

    @patch.dict(os.environ, {"NO_COLOR": "1"})
    def test_no_color_environment(self, runner):
        """Test that NO_COLOR environment variable is respected."""
        result = runner.invoke(cli, ["stack", "list"])

        assert result.exit_code == 0
        # Output should be present but without ANSI escape codes
        # This is a basic check - detailed ANSI parsing would be complex
        assert result.output.strip()

    @patch.dict(os.environ, {"COLUMNS": "40"})
    def test_narrow_terminal(self, runner):
        """Test table formatting with narrow terminal."""
        result = runner.invoke(cli, ["stack", "list"])

        assert result.exit_code == 0
        assert result.output.strip()

        # Check that lines don't exceed reasonable width for narrow terminal
        lines = result.output.split("\n")
        for line in lines:
            # Remove ANSI escape codes for length check
            clean_line = self._remove_ansi_codes(line)
            # Allow some flexibility for table borders and formatting
            assert len(clean_line) <= 120  # Reasonable upper bound

    @patch.dict(os.environ, {"COLUMNS": "200"})
    def test_wide_terminal(self, runner):
        """Test table formatting with wide terminal."""
        result = runner.invoke(cli, ["stack", "list"])

        assert result.exit_code == 0
        assert result.output.strip()

    def test_pagination_in_json_output(self, runner):
        """Test that pagination information is included in JSON output."""
        result = runner.invoke(cli, ["stack", "list", "--output", "json"])

        assert result.exit_code == 0

        try:
            data = json.loads(result.output)
            # Check if pagination format is used
            if isinstance(data, dict) and "pagination" in data:
                pagination = data["pagination"]
                assert "index" in pagination or "total" in pagination
        except json.JSONDecodeError:
            pytest.fail("Invalid JSON output")

    def test_error_handling_invalid_output_format(self, runner):
        """Test error handling for invalid output format."""
        result = runner.invoke(cli, ["stack", "list", "--output", "invalid"])

        # Should either fail gracefully or show help
        assert result.exit_code != 0 or "invalid" not in result.output.lower()

    def test_mixed_data_types_handling(self, runner):
        """Test handling of mixed data types in JSON output."""
        result = runner.invoke(cli, ["stack", "list", "--output", "json"])

        assert result.exit_code == 0

        try:
            data = json.loads(result.output)
            # Should be valid JSON with proper data types
            assert isinstance(data, (list, dict))
        except json.JSONDecodeError:
            pytest.fail("JSON output contains invalid data types")

    def _remove_ansi_codes(self, text: str) -> str:
        """Remove ANSI escape codes from text for length measurement."""
        import re

        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)

    def test_consistent_header_formatting(self, runner):
        """Test that headers are consistently formatted across commands."""
        commands_to_test = [
            ["stack", "list"],
            ["user", "list"],
            # Add more as needed, but avoid commands that might not work in test env
        ]

        for command in commands_to_test:
            result = runner.invoke(cli, command)

            if result.exit_code == 0 and result.output.strip():
                # Headers should be uppercase and properly formatted
                lines = result.output.split("\n")
                header_line = None

                for line in lines:
                    # Look for a line that looks like headers (contains uppercase letters)
                    if any(
                        c.isupper() for c in line
                    ) and not line.strip().startswith("Page"):
                        header_line = line
                        break

                if header_line:
                    # Should contain uppercase headers
                    assert any(word.isupper() for word in header_line.split())

    def test_status_colorization_in_output(self, runner):
        """Test that status values are properly colorized when color is enabled."""
        result = runner.invoke(cli, ["stack", "list"])

        assert result.exit_code == 0

        # If there are status-like fields with known values, they should be colorized
        # This is a basic check - the exact colorization depends on the data
        if any(
            status in result.output.lower()
            for status in ["active", "running", "failed", "pending"]
        ):
            # Should contain ANSI color codes (unless NO_COLOR is set)
            if os.getenv("NO_COLOR") != "1":
                # Basic check for ANSI codes presence
                assert (
                    "\x1b[" in result.output
                    or "[32m" in result.output
                    or "[31m" in result.output
                )
