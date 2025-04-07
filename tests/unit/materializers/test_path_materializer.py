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
"""Tests for the PathMaterializer."""

import tempfile
from pathlib import Path

from tests.unit.test_general import _test_materializer
from zenml.materializers.path_materializer import PathMaterializer


def test_path_materializer():
    """Test the Path materializer."""
    # Create a temporary directory with some test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create the test directory
        test_path = Path(temp_dir) / "test_dir"
        test_path.mkdir()

        # Create some test files
        test_file_1 = test_path / "test1.txt"
        test_file_1.write_text("This is a test file")

        test_file_2 = test_path / "test2.log"
        test_file_2.write_text("This is another test file")

        # Create a subdirectory with a file
        subdir = test_path / "subdir"
        subdir.mkdir()
        test_file_3 = subdir / "test3.py"
        test_file_3.write_text("print('Hello, world!')")

        # Test the materializer
        result = _test_materializer(
            step_output_type=Path,
            materializer_class=PathMaterializer,
            step_output=test_path,
            expected_metadata_size=1,  # Only storage_size remains
        )

        # Verify the result is a Path
        assert isinstance(result, Path)

        # Verify files were preserved
        assert (result / "test1.txt").exists()
        assert (result / "test2.log").exists()
        assert (result / "subdir" / "test3.py").exists()

        # Check file contents
        assert (result / "test1.txt").read_text() == "This is a test file"
        assert (
            result / "test2.log"
        ).read_text() == "This is another test file"
        assert (
            result / "subdir" / "test3.py"
        ).read_text() == "print('Hello, world!')"


def test_path_materializer_with_file():
    """Test the Path materializer with a single file."""
    # Create a temporary file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test file
        test_file = Path(temp_dir) / "single_file.txt"
        test_file.write_text("This is a single file test")

        # Test the materializer
        result = _test_materializer(
            step_output_type=Path,
            materializer_class=PathMaterializer,
            step_output=test_file,
            expected_metadata_size=1,  # Only storage_size remains
        )

        # Verify the result is a Path
        assert isinstance(result, Path)

        # Verify it's a file, not a directory
        assert result.is_file()

        # Check file content
        assert result.read_text() == "This is a single file test"


def test_path_materializer_with_binary_file():
    """Test the Path materializer with a binary file."""
    # Create a temporary binary file
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test binary file
        test_file = Path(temp_dir) / "binary_file.bin"
        with open(test_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe")

        # Test the materializer
        result = _test_materializer(
            step_output_type=Path,
            materializer_class=PathMaterializer,
            step_output=test_file,
            expected_metadata_size=1,  # Only storage_size remains
        )

        # Verify the result is a Path
        assert isinstance(result, Path)

        # Verify it's a file, not a directory
        assert result.is_file()

        # Check file content
        with open(result, "rb") as f:
            content = f.read()
        assert content == b"\x00\x01\x02\x03\xff\xfe"
