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

from typing import Tuple

import pytest

from zenml.integrations.s3.utils import split_s3_path


@pytest.mark.parametrize(
    "path,expected",
    [
        ["s3://bucket/path", ("bucket", "path")],
        ["s3://bucket2/path/path2", ("bucket2", "path/path2")],
        [
            "s3://bucket3/path/path2/random.file",
            ("bucket3", "path/path2/random.file"),
        ],
        ["s3://bucket/", ("bucket", "")],
        ["s3://bucket2", ("bucket2", "")],
    ],
)
def test_split_s3_path_on_good_paths(
    path: str, expected: Tuple[str, str]
) -> None:
    """Test that paths are correctly parsed."""
    assert split_s3_path(path) == expected


@pytest.mark.parametrize(
    "path",
    [
        "s3:/bucket",
        "bucket2/path/path2",
        "s2://bucket/",
    ],
)
def test_split_s3_path_on_bad_paths(path: str) -> None:
    """Test that exception is raised for badly formatted paths."""
    with pytest.raises(ValueError):
        split_s3_path(path)
