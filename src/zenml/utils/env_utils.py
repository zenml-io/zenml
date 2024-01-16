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
"""Utility functions for handling environment variables."""
import os
from typing import Dict, List, Optional, cast

ENV_VAR_CHUNK_SUFFIX = "_CHUNK_"


def split_environment_variables(
    size_limit: int,
    env: Optional[Dict[str, str]] = None,
) -> None:
    """Split long environment variables into chunks.

    Splits the input environment variables with values that exceed the supplied
    maximum length into individual components. The input environment variables
    are modified in-place.

    Args:
        size_limit: Maximum length of an environment variable value.
        env: Input environment variables dictionary. If not supplied, the
            OS environment variables are used.

    Raises:
        RuntimeError: If an environment variable value is too large and requires
            more than 10 chunks.
    """
    if env is None:
        env = cast(Dict[str, str], os.environ)

    for key, value in env.copy().items():
        if len(value) <= size_limit:
            continue

        # We keep the number of chunks to a maximum of 10 to avoid generating
        # too many environment variables chunks and also to make the
        # reconstruction easier to implement
        if len(value) > size_limit * 10:
            raise RuntimeError(
                f"Environment variable {key} exceeds the maximum length of "
                f"{size_limit * 10} characters."
            )

        env.pop(key)

        # Split the environment variable into chunks
        chunks = [
            value[i : i + size_limit] for i in range(0, len(value), size_limit)
        ]
        for i, chunk in enumerate(chunks):
            env[f"{key}{ENV_VAR_CHUNK_SUFFIX}{i}"] = chunk


def reconstruct_environment_variables(
    env: Optional[Dict[str, str]] = None,
) -> None:
    """Reconstruct environment variables that were split into chunks.

    Reconstructs the environment variables with values that were split into
    individual chunks because they were too large. The input environment
    variables are modified in-place.

    Args:
        env: Input environment variables dictionary. If not supplied, the OS
            environment variables are used.
    """
    if env is None:
        env = cast(Dict[str, str], os.environ)

    chunks: Dict[str, List[str]] = {}
    for key in env.keys():
        if not key[:-1].endswith(ENV_VAR_CHUNK_SUFFIX):
            continue

        # Collect all chunks of the same environment variable
        original_key = key[: -(len(ENV_VAR_CHUNK_SUFFIX) + 1)]
        chunks.setdefault(original_key, [])
        chunks[original_key].append(key)

    # Reconstruct the environment variables from their chunks
    for key, chunk_keys in chunks.items():
        chunk_keys.sort()
        value = "".join([env[key] for key in chunk_keys])
        env[key] = value

        # Remove the chunk environment variables
        for key in chunk_keys:
            env.pop(key)
