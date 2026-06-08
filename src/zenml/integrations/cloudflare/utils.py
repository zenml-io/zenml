#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Utility methods for the Cloudflare R2 artifact store."""

from typing import Tuple

R2_SCHEME = "r2://"


def split_r2_path(r2_path: str) -> Tuple[str, str]:
    """Split an R2 URI into bucket and key.

    Args:
        r2_path: R2 URI (e.g. "r2://bucket/path").

    Returns:
        A tuple of bucket and key. For "r2://bucket/path/path2" it returns
        ("bucket", "path/path2").

    Raises:
        ValueError: If the R2 URI is invalid.
    """
    if not r2_path.startswith(R2_SCHEME):
        raise ValueError(
            f"Invalid R2 URI given: {r2_path}. It should start with `{R2_SCHEME}`."
        )
    path_parts = r2_path[len(R2_SCHEME) :].split("/")
    bucket = path_parts.pop(0)
    key = "/".join(path_parts)
    return bucket, key


def strip_r2_scheme(path: str) -> str:
    """Remove the `r2://` scheme prefix from a path if present.

    The underlying ``s3fs`` filesystem only understands the ``s3://`` scheme,
    so R2 paths must be reduced to plain ``bucket/key`` form before they are
    handed to it.

    Args:
        path: The path to normalize.

    Returns:
        The path without the `r2://` prefix.
    """
    if path.startswith(R2_SCHEME):
        return path[len(R2_SCHEME) :]
    return path
