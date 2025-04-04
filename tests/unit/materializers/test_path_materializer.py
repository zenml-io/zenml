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
            expected_metadata_size=6,  # path, file_count, directory_count, total_size_bytes, file_extensions, storage_size
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


def test_path_materializer_metadata():
    """Test the metadata extraction of the Path materializer."""
    # Create a temporary directory with some test files
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create the test directory
        test_path = Path(temp_dir) / "test_dir_metadata"
        test_path.mkdir()

        # Create some test files with different extensions
        test_file_1 = test_path / "test1.txt"
        test_file_1.write_text("This is a test file")

        test_file_2 = test_path / "test2.py"
        test_file_2.write_text("print('Hello, world!')")

        test_file_3 = test_path / "test3.py"
        test_file_3.write_text("print('Another Python file')")

        # Create a materializer and extract metadata
        materializer = PathMaterializer("test_uri")
        metadata = materializer.extract_metadata(test_path)

        # Verify metadata
        assert metadata["path"] == str(test_path)
        assert metadata["file_count"] == 3
        assert metadata["directory_count"] == 0  # No subdirectories created

        # Check file extensions
        assert ".txt" in metadata["file_extensions"]
        assert metadata["file_extensions"][".txt"] == 1
        assert ".py" in metadata["file_extensions"]
        assert metadata["file_extensions"][".py"] == 2

        # Verify total size is correct
        expected_size = sum(
            f.stat().st_size for f in [test_file_1, test_file_2, test_file_3]
        )
        assert metadata["total_size_bytes"] == expected_size


def test_is_text_file():
    """Test the _is_text_file method."""
    materializer = PathMaterializer("test_uri")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)

        # Create text files with different extensions
        text_file = temp_dir_path / "text.txt"
        text_file.write_text("This is plain text")

        py_file = temp_dir_path / "script.py"
        py_file.write_text("print('hello')")

        # Create a binary file
        bin_file = temp_dir_path / "binary.bin"
        with open(bin_file, "wb") as f:
            f.write(b"\x00\x01\x02\x03\xff\xfe")

        # Test the method
        assert materializer._is_text_file(text_file) is True
        assert materializer._is_text_file(py_file) is True
        assert materializer._is_text_file(bin_file) is False
