#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
from pathlib import Path

import pytest

from zenml.client import Client


def test_files_outside_of_artifact_store_are_not_reachable_by_it(
    clean_client: "Client",
):
    """Tests that no operations outside of bounds of artifact store could happen."""
    a_s = clean_client.active_stack.artifact_store

    outside_dir = Path(a_s.path) / ".."
    outside_file = str(outside_dir / "tmp.file")
    try:
        # create a file outside of artifact store
        with open(outside_file, "w") as f:
            f.write("test")
        # try to open it via artifact store interface
        with pytest.raises(FileNotFoundError):
            a_s.open(outside_file, "r")
        # try to copy it via artifact store interface
        with pytest.raises(FileNotFoundError):
            a_s.copyfile(outside_file, ".", "r")
    except Exception as e:
        raise e
    finally:
        os.remove(outside_file)

    inside_file = str(Path(a_s.path) / "tmp.file")
    try:
        # create a file inside of artifact store
        with open(inside_file, "w") as f:
            f.write("test")
        # try to open it via artifact store interface
        assert a_s.open(inside_file, "r").read() == "test"
        # try to copy it via artifact store interface
        inside_file2 = str(Path(a_s.path) / "tmp2.file")
        a_s.copyfile(inside_file, inside_file2, "r")
        # try to open it via artifact store interface
        assert open(inside_file2, "r").read() == "test"
        # try to copy it via artifact store interface, but with target outside of bounds
        with pytest.raises(FileNotFoundError):
            a_s.copyfile(inside_file, ".", "r")
    except Exception as e:
        raise e
    finally:
        os.remove(inside_file)
        os.remove(inside_file2)
