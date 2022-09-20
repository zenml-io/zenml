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
"""Implementation of the Kubeflow entrypoint configuration."""

import os
from typing import Any, List, Optional, Set

from tfx.orchestration.portable import data_types

from zenml.entrypoints import StepEntrypointConfiguration
from zenml.integrations.kubeflow.orchestrators import utils

METADATA_UI_PATH_OPTION = "metadata_ui_path"
ENV_ZENML_RUN_NAME = "ZENML_RUN_NAME"


class KubeflowEntrypointConfiguration(StepEntrypointConfiguration):
    """Entrypoint configuration for running steps on kubeflow.

    This class writes a markdown file that will be displayed in the KFP UI.
    """

    @classmethod
    def get_entrypoint_options(cls) -> Set[str]:
        """Gets all options required for running with this configuration.

        The metadata ui path option expects a path where the markdown file
        that will be displayed in the kubeflow UI should be written. The same
        path needs to be added as an output artifact called
        `mlpipeline-ui-metadata` for the corresponding `kfp.dsl.ContainerOp`.

        Returns:
            The superclass options as well as an option for the metadata ui
            path.
        """
        return super().get_entrypoint_options() | {METADATA_UI_PATH_OPTION}

    @classmethod
    def get_entrypoint_arguments(cls, **kwargs: Any) -> List[str]:
        """Gets all arguments that the entrypoint command should be called with.

        Args:
            **kwargs: Kwargs, must include the metadata ui path.

        Returns:
            The superclass arguments as well as arguments for the metadata ui
            path.
        """
        return super().get_entrypoint_arguments(**kwargs) + [
            f"--{METADATA_UI_PATH_OPTION}",
            kwargs[METADATA_UI_PATH_OPTION],
        ]

    def get_run_name(self, pipeline_name: str) -> Optional[str]:
        """Returns the Kubeflow pipeline run name.

        Args:
            pipeline_name: The name of the pipeline.

        Returns:
            The Kubeflow pipeline run name.

        Raises:
            RuntimeError: If the run name environment variable is not set.
        """
        try:
            return os.environ[ENV_ZENML_RUN_NAME]
        except KeyError:
            raise RuntimeError(
                "Unable to read run name from environment variable "
                f"{ENV_ZENML_RUN_NAME}."
            )

    def post_run(
        self,
        pipeline_name: str,
        step_name: str,
        execution_info: Optional[data_types.ExecutionInfo] = None,
    ) -> None:
        """Writes a markdown file that will display information.

        This will be about the step execution and input/output artifacts in the
        KFP UI.

        Args:
            pipeline_name: The name of the pipeline.
            step_name: The name of the step.
            execution_info: The execution info of the step.
        """
        if execution_info:
            utils.dump_ui_metadata(
                execution_info=execution_info,
                metadata_ui_path=self.entrypoint_args[METADATA_UI_PATH_OPTION],
            )
