#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Utility methods for S3."""

from typing import Tuple


def split_s3_path(s3_path: str) -> Tuple[str, str]:
    """Split S3 URI into bucket and key.

    Args:
        s3_path: S3 URI (e.g. "s3://bucket/path")

    Returns:
        A tuple of bucket and key, for "s3://bucket/path/path2"
            it will return ("bucket","path/path2")

    Raises:
        ValueError: if the S3 URI is invalid
    """
    if not s3_path.startswith("s3://"):
        raise ValueError(
            f"Invalid S3 URI given: {s3_path}. "
            "It should start with `s3://`."
        )
    path_parts = s3_path.replace("s3://", "").split("/")
    bucket = path_parts.pop(0)
    key = "/".join(path_parts)
    return bucket, key
