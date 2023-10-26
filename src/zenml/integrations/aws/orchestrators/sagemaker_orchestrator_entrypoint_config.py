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
"""Entrypoint configuration for ZenML Sagemaker pipeline steps."""
import os
from typing import Dict, List

from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)

ENV_VAR_CHUNK_SUFFIX = "_CHUNK_"


class SagemakerEntrypointConfiguration(StepEntrypointConfiguration):
    """Entrypoint configuration for ZenML Sagemaker pipeline steps.

    The only purpose of this entrypoint configuration is to reconstruct the
    environment variables that exceed the maximum length of 256 characters
    from their individual components.
    """

    def run(self) -> None:
        """Runs the step."""
        # Reconstruct the environment variables that exceed the maximum length
        # of 256 characters from their individual chunks
        self.reconstruct_environment_variables()

        # Run the step
        super().run()

    @staticmethod
    def split_environment_variables(
        env: Dict[str, str],
    ) -> Dict[str, str]:
        """Split long environment variables into chunks.

        Splits the environment variables that exceed the Sagemaker maximum
        length of 256 characters into individual components.

        Args:
            env: The environment variables.

        Returns:
            The updated environment variables.

        Raises:
            RuntimeError: If an environment variable exceeds the maximum length
                of 2560 characters.
        """
        updated_env = env.copy()
        for key, value in env.items():
            if len(value) <= 256:
                continue

            # We keep the number of chunks to a maximum of 10 to avoid passing
            # too many environment variables to the Sagemaker job and also to
            # make the reconstruction easier to implement
            if len(value) > 256 * 10:
                raise RuntimeError(
                    f"Environment variable {key} exceeds the maximum length of "
                    f"2560 characters."
                )

            updated_env.pop(key)

            # Split the environment variable into chunks of 256 characters
            chunks = [value[i : i + 256] for i in range(0, len(value), 256)]
            for i, chunk in enumerate(chunks):
                updated_env[f"{key}{ENV_VAR_CHUNK_SUFFIX}{i}"] = chunk

        return updated_env

    @staticmethod
    def reconstruct_environment_variables() -> None:
        """Reconstruct environment variables that were split into chunks.

        Reconstructs the environment variables with values that exceed the
        Sagemaker maximum length of 256 characters from their individual
        chunks.
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
