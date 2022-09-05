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
"""Entrypoint configuration for the Kubernetes worker/step pods."""

from typing import Any, List, Optional, Set

from zenml.entrypoints import StepEntrypointConfiguration

RUN_NAME_OPTION = "run_name"


class KubernetesStepEntrypointConfiguration(StepEntrypointConfiguration):
    """Entrypoint configuration for running steps on Kubernetes."""

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Kubernetes specific entrypoint options.

        The argument `RUN_NAME_OPTION` is needed for `get_run_name` to have
        consistent values between steps.

        Returns:
            Set of entrypoint options.
        """
        return super().get_entrypoint_options() | {RUN_NAME_OPTION}

    @classmethod
    def get_entrypoint_arguments(cls, **kwargs: Any) -> List[str]:
        """Kubernetes specific entrypoint arguments.

        Sets the value for the `RUN_NAME_OPTION` argument.

        Args:
            **kwargs: Additional args.

        Returns:
            List of entrypoint arguments.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{RUN_NAME_OPTION}",
            kwargs[RUN_NAME_OPTION],
        ]

    def get_run_name(self, pipeline_name: str) -> Optional[str]:
        """Returns the ZenML run name.

        Args:
            pipeline_name: Name of the ZenML pipeline (unused).

        Returns:
            ZenML run name.
        """
        job_id: str = self.entrypoint_args[RUN_NAME_OPTION]
        return job_id
