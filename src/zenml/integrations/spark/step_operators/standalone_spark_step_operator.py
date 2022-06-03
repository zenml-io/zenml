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
import subprocess
from typing import List, ClassVar

from zenml.integrations.spark import SPARK_STEP_OPERATOR
from zenml.integrations.spark.step_operators import spark_entrypoint
from zenml.step_operators import BaseStepOperator

ENTRYPOINT = spark_entrypoint.__file__


class StandaloneSparkStepOperator(BaseStepOperator):
    # Instance parameters
    master: str
    deploy_mode: str = 'client'
    configuration_properties: List[str] = []

    # Class configuration
    FLAVOR: ClassVar[str] = SPARK_STEP_OPERATOR

    def _create_base_command(self):
        """Create the base command for spark-submit."""
        command = [
            "spark-submit",
            "--master",
            self.master,
            "--deploy-mode",
            self.deploy_mode,
        ]
        return command

    def _create_configurations(self):
        """Build the configuration parameters for the spark-submit command."""
        configurations = []
        for o in self.configuration_properties:
            configurations.extend(["--conf", o])
        return configurations

    @staticmethod
    def _build_entrypoint_command(entrypoint_command):
        """Build the python entrypoint command for the spark-submit."""
        command = [ENTRYPOINT]

        for arg in [
            "--main_module",
            "--step_source_path",
            "--execution_info_path",
            "--input_artifact_types_path"
        ]:
            i = entrypoint_command.index(arg)
            command.extend([arg, entrypoint_command[i + 1]])

        return command

    def launch(
        self,
        pipeline_name: str,
        run_name: str,
        requirements: List[str],
        entrypoint_command: List[str],
    ) -> None:
        """Launch the spark job with spark-submit."""

        # Base command
        base_command = self._create_base_command()

        # Add configurations
        configurations = self._create_configurations()
        base_command.extend(configurations)

        # Add the entrypoint
        entrypoint = self._build_entrypoint_command(entrypoint_command)

        # Finalize the command
        final_command = " ".join(base_command + entrypoint)

        process = subprocess.Popen(
            final_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True
        )

        stdout, stderr = process.communicate()

        if process.returncode != 0:
            raise RuntimeError(stderr)
        print(stdout)
