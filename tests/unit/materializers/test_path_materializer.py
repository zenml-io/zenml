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

import tarfile
import tempfile
from pathlib import Path

from tests.unit.test_general import _test_materializer
from zenml.materializers.path_materializer import (
    PathMaterializer,
    _is_safe_tar_member,
)


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


def test_is_safe_tar_member_regular_files():
    """Test that regular files are validated correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Safe regular file
        safe_file = tarfile.TarInfo("safe_file.txt")
        safe_file.type = tarfile.REGTYPE
        assert _is_safe_tar_member(safe_file, temp_dir)

        # Unsafe regular file with path traversal
        unsafe_file = tarfile.TarInfo("../../../etc/passwd")
        unsafe_file.type = tarfile.REGTYPE
        assert not _is_safe_tar_member(unsafe_file, temp_dir)

        # Safe nested file
        nested_file = tarfile.TarInfo("subdir/nested_file.txt")
        nested_file.type = tarfile.REGTYPE
        assert _is_safe_tar_member(nested_file, temp_dir)


def test_is_safe_tar_member_symbolic_links():
    """Test that symbolic links are validated correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Safe symbolic link pointing within directory
        safe_symlink = tarfile.TarInfo("safe_symlink.txt")
        safe_symlink.type = tarfile.SYMTYPE
        safe_symlink.linkname = "target_file.txt"
        assert _is_safe_tar_member(safe_symlink, temp_dir)

        # Safe symbolic link pointing to subdirectory file
        safe_nested_symlink = tarfile.TarInfo("safe_nested_symlink.txt")
        safe_nested_symlink.type = tarfile.SYMTYPE
        safe_nested_symlink.linkname = "subdir/target.txt"
        assert _is_safe_tar_member(safe_nested_symlink, temp_dir)

        # Unsafe symbolic link pointing outside directory
        unsafe_symlink = tarfile.TarInfo("unsafe_symlink.txt")
        unsafe_symlink.type = tarfile.SYMTYPE
        unsafe_symlink.linkname = "../../../etc/passwd"
        assert not _is_safe_tar_member(unsafe_symlink, temp_dir)

        # Unsafe symbolic link with absolute path
        absolute_symlink = tarfile.TarInfo("absolute_symlink.txt")
        absolute_symlink.type = tarfile.SYMTYPE
        absolute_symlink.linkname = "/etc/passwd"
        assert not _is_safe_tar_member(absolute_symlink, temp_dir)


def test_is_safe_tar_member_hard_links():
    """Test that hard links are validated correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Safe hard link pointing within directory
        safe_hardlink = tarfile.TarInfo("safe_hardlink.txt")
        safe_hardlink.type = tarfile.LNKTYPE
        safe_hardlink.linkname = "target_file.txt"
        assert _is_safe_tar_member(safe_hardlink, temp_dir)

        # Safe hard link pointing to subdirectory file
        safe_nested_hardlink = tarfile.TarInfo("safe_nested_hardlink.txt")
        safe_nested_hardlink.type = tarfile.LNKTYPE
        safe_nested_hardlink.linkname = "subdir/target.txt"
        assert _is_safe_tar_member(safe_nested_hardlink, temp_dir)

        # Unsafe hard link pointing outside directory
        unsafe_hardlink = tarfile.TarInfo("unsafe_hardlink.txt")
        unsafe_hardlink.type = tarfile.LNKTYPE
        unsafe_hardlink.linkname = "../../../etc/passwd"
        assert not _is_safe_tar_member(unsafe_hardlink, temp_dir)

        # Unsafe hard link with absolute path
        absolute_hardlink = tarfile.TarInfo("absolute_hardlink.txt")
        absolute_hardlink.type = tarfile.LNKTYPE
        absolute_hardlink.linkname = "/etc/passwd"
        assert not _is_safe_tar_member(absolute_hardlink, temp_dir)


def test_is_safe_tar_member_mixed_scenarios():
    """Test edge cases and mixed scenarios."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # File with safe name but unsafe symlink name should be rejected
        mixed_unsafe = tarfile.TarInfo("../unsafe_name.txt")
        mixed_unsafe.type = tarfile.SYMTYPE
        mixed_unsafe.linkname = "safe_target.txt"
        assert not _is_safe_tar_member(mixed_unsafe, temp_dir)

        # File with safe name but unsafe hardlink target should be rejected
        safe_name_unsafe_target = tarfile.TarInfo("safe_name.txt")
        safe_name_unsafe_target.type = tarfile.LNKTYPE
        safe_name_unsafe_target.linkname = "../unsafe_target.txt"
        assert not _is_safe_tar_member(safe_name_unsafe_target, temp_dir)

        # Directory entry should be safe if name is safe
        safe_directory = tarfile.TarInfo("safe_dir/")
        safe_directory.type = tarfile.DIRTYPE
        assert _is_safe_tar_member(safe_directory, temp_dir)
