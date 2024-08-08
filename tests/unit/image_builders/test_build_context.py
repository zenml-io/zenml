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
import os

from zenml.image_builders import BuildContext


def test_adding_extra_files(tmp_path):
    """Tests adding extra files to the build context."""
    build_context = BuildContext()

    build_context.add_file("file content as string", destination="direct")

    extra_file_path = tmp_path / "extra_file"
    extra_file_path.write_text("file content in file")

    build_context.add_file(str(extra_file_path), destination="indirect")

    extra_files = build_context.get_extra_files()
    assert extra_files["direct"] == "file content as string"
    assert extra_files["indirect"] == "file content in file"


def test_adding_extra_directory(tmp_path):
    """Tests adding extra directories to the build context."""
    (tmp_path / "1").write_text("file 1")
    (tmp_path / "2").write_text("file 2")

    build_context = BuildContext()
    build_context.add_directory(str(tmp_path), destination="dir")

    extra_files = build_context.get_extra_files()
    assert extra_files["dir/1"] == "file 1"
    assert extra_files["dir/2"] == "file 2"


def test_build_context_includes_and_excludes(tmp_path):
    """Tests that the build context correctly includes and excludes files."""
    root = tmp_path / "root"
    root.mkdir()
    (root / "1").write_text("file 1")
    (root / "2").write_text("file 2")

    build_context = BuildContext(root=str(root))
    assert build_context.dockerignore_file is None
    assert build_context._get_exclude_patterns() == []
    assert build_context.get_files() == {
        "1": str(root / "1"),
        "2": str(root / "2"),
    }

    custom_dockerignore = tmp_path / "custom_dockerignore"
    custom_dockerignore.write_text("/1")
    build_context = BuildContext(
        root=str(root), dockerignore_file=str(custom_dockerignore)
    )
    build_context.dockerignore_file == str(custom_dockerignore)
    assert build_context._get_exclude_patterns() == ["/1", "!/.zen"]
    assert build_context.get_files() == {"2": str(root / "2")}

    zen_repo = root / ".zen" / "config.yaml"
    zen_repo.parent.mkdir()
    zen_repo.touch()
    default_dockerignore = root / ".dockerignore"
    default_dockerignore.write_text("*")
    build_context = BuildContext(root=str(root))
    build_context.dockerignore_file == str(default_dockerignore)
    assert build_context._get_exclude_patterns() == ["*", "!/.zen"]
    assert build_context.get_files() == {
        ".dockerignore": str(default_dockerignore),
        ".zen": str(root / ".zen"),
        os.path.join(".zen", "config.yaml"): str(zen_repo),
    }
