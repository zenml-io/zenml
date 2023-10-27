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
from typing import Dict, List

ENV_VAR_CHUNK_SUFFIX = "_CHUNK_"


def split_environment_variables(
    env: Dict[str, str],
    size_limit: int,
) -> Dict[str, str]:
    """Split long environment variables into chunks.

    Splits the input environment variables with values that exceed the supplied
    maximum length into individual components.

    Args:
        env: Input environment variables.
        size_limit: Maximum length of an environment variable value.

    Returns:
        The updated environment variables.

    Raises:
        RuntimeError: If an environment variable value is too large and requires
            more than 10 chunks.
    """
    updated_env = env.copy()
    for key, value in env.items():
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

        updated_env.pop(key)

        # Split the environment variable into chunks
        chunks = [
            value[i : i + size_limit] for i in range(0, len(value), size_limit)
        ]
        for i, chunk in enumerate(chunks):
            updated_env[f"{key}{ENV_VAR_CHUNK_SUFFIX}{i}"] = chunk

    return updated_env


def reconstruct_environment_variables() -> None:
    """Reconstruct environment variables that were split into chunks.

    Reconstructs the environment variables with values that were split into
    individual chunks because they were too large.
    """
    chunks: Dict[str, List[str]] = {}
    for key in os.environ.keys():
        if not key[:-1].endswith(ENV_VAR_CHUNK_SUFFIX):
            continue

        # Collect all chunks of the same environment variable
        original_key = key[: -(len(ENV_VAR_CHUNK_SUFFIX) + 1)]
        chunks.setdefault(original_key, [])
        chunks[original_key].append(key)

    # Reconstruct the environment variables from their chunks
    for key, chunk_keys in chunks.items():
        chunk_keys.sort()
        value = "".join([os.environ[key] for key in chunk_keys])
        os.environ[key] = value

        # Remove the chunk environment variables
        for key in chunk_keys:
            os.environ.pop(key)
