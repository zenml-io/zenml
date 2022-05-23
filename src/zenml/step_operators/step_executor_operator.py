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
import json
import os
import sys
from typing import TYPE_CHECKING, Any, List, Tuple, cast

from tfx.orchestration.portable import data_types
from tfx.orchestration.portable.base_executor_operator import (
    BaseExecutorOperator,
)
from tfx.proto.orchestration import (
    executable_spec_pb2,
    execution_result_pb2,
    pipeline_pb2,
)

import zenml
import zenml.constants
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.steps.utils import (
    INTERNAL_EXECUTION_PARAMETER_PREFIX,
    PARAM_CUSTOM_STEP_OPERATOR,
)
from zenml.utils import source_utils, yaml_utils

if TYPE_CHECKING:
    from zenml.stack import Stack
    from zenml.step_operators import BaseStepOperator

logger = get_logger(__name__)


def _write_execution_info(
    execution_info: data_types.ExecutionInfo, path: str
) -> None:
    """Writes execution information to a given path."""
    execution_info_bytes = execution_info.to_proto().SerializeToString()

    with fileio.open(path, "wb") as f:
        f.write(execution_info_bytes)

    logger.debug("Finished writing execution info to '%s'", path)


def _read_executor_output(
    output_path: str,
) -> execution_result_pb2.ExecutorOutput:
    """Reads executor output from the given path.

    Returns:
        Executor output object.

    Raises:
        RuntimeError: If no output is written to the given path.
    """
    if fileio.exists(output_path):
        with fileio.open(output_path, "rb") as f:
            return execution_result_pb2.ExecutorOutput.FromString(f.read())
    else:
        raise RuntimeError(
            f"Unable to find executor output at path '{output_path}'."
        )


class StepExecutorOperator(BaseExecutorOperator):
    """StepExecutorOperator extends TFX's BaseExecutorOperator.

    This class can be passed as a custom executor operator during
    a pipeline run which will then be used to call the step's
    configured step operator to launch it in some environment.
    """

    SUPPORTED_EXECUTOR_SPEC_TYPE = [
        executable_spec_pb2.PythonClassExecutableSpec
    ]
    SUPPORTED_PLATFORM_CONFIG_TYPE: List[Any] = []

    @staticmethod
    def _collect_requirements(
        stack: "Stack",
        pipeline_node: pipeline_pb2.PipelineNode,
    ) -> List[str]:
        """Collects all requirements necessary to run a step.

        Args:
            stack: Stack on which the step is being executed.
            pipeline_node: Pipeline node info for a step.

        Returns:
            Alphabetically sorted list of pip requirements.
        """
        requirements = stack.requirements()

        # Add pipeline requirements from the corresponding node context
        for context in pipeline_node.contexts.contexts:
            if context.type.name == "pipeline_requirements":
                pipeline_requirements = context.properties[
                    "pipeline_requirements"
                ].field_value.string_value.split(" ")
                requirements.update(pipeline_requirements)
                break

        # TODO [ENG-696]: Find a nice way to set this if the running version of
        #  ZenML is not an official release (e.g. on a development branch)
        # Add the current ZenML version as a requirement
        requirements.add(f"zenml=={zenml.__version__}")

        return sorted(requirements)

    @staticmethod
    def _resolve_user_modules(
        pipeline_node: pipeline_pb2.PipelineNode,
    ) -> Tuple[str, str]:
        """Resolves the main and step module.

        Args:
            pipeline_node: Pipeline node info for a step.

        Returns:
            A tuple containing the path of the resolved main module and step
            class.
        """
        main_module_path = zenml.constants.USER_MAIN_MODULE
        if not main_module_path:
            main_module_path = source_utils.get_module_source_from_module(
                sys.modules["__main__"]
            )

        step_type = cast(str, pipeline_node.node_info.type.name)
        step_module_path, step_class = step_type.rsplit(".", maxsplit=1)
        if step_module_path == "__main__":
            step_module_path = main_module_path

        step_source_path = f"{step_module_path}.{step_class}"

        return main_module_path, step_source_path

    @staticmethod
    def _get_step_operator(
        stack: "Stack", execution_info: data_types.ExecutionInfo
    ) -> "BaseStepOperator":
        """Fetches the step operator specified in the execution info.

        Args:
            stack: Stack on which the step is being executed.
            execution_info: Execution info needed to run the step.

        Returns:
            The step operator to run a step.
        """
        step_operator = stack.step_operator

        # the two following errors should never happen as the stack gets
        # validated before running the pipeline
        if not step_operator:
            raise RuntimeError(
                f"No step operator specified for active stack '{stack.name}'."
            )

        step_operator_property_name = (
            INTERNAL_EXECUTION_PARAMETER_PREFIX + PARAM_CUSTOM_STEP_OPERATOR
        )
        required_step_operator = json.loads(
            execution_info.exec_properties[step_operator_property_name]
        )
        if required_step_operator != step_operator.name:
            raise RuntimeError(
                f"No step operator named '{required_step_operator}' in active "
                f"stack '{stack.name}'."
            )

        return step_operator

    def run_executor(
        self,
        execution_info: data_types.ExecutionInfo,
    ) -> execution_result_pb2.ExecutorOutput:
        """Invokes the executor with inputs provided by the Launcher.

        Args:
            execution_info: Necessary information to run the executor.

        Returns:
            The executor output.
        """
        # Pretty sure these attributes will always be not None, assert here so
        # mypy doesn't complain
        assert execution_info.pipeline_node
        assert execution_info.pipeline_info
        assert execution_info.pipeline_run_id
        assert execution_info.tmp_dir
        assert execution_info.execution_output_uri

        step_name = execution_info.pipeline_node.node_info.id
        stack = Repository().active_stack
        step_operator = self._get_step_operator(
            stack=stack, execution_info=execution_info
        )

        requirements = self._collect_requirements(
            stack=stack, pipeline_node=execution_info.pipeline_node
        )

        # Write the execution info to a temporary directory inside the artifact
        # store so the step operator entrypoint can load it
        execution_info_path = os.path.join(
            execution_info.tmp_dir, "zenml_execution_info.pb"
        )
        _write_execution_info(execution_info, path=execution_info_path)

        main_module, step_source_path = self._resolve_user_modules(
            pipeline_node=execution_info.pipeline_node
        )

        input_artifact_types_path = os.path.join(
            execution_info.tmp_dir, "input_artifacts.json"
        )
        input_artifact_type_mapping = {
            input_name: source_utils.resolve_class(artifacts[0].__class__)
            for input_name, artifacts in execution_info.input_dict.items()
        }
        yaml_utils.write_json(
            input_artifact_types_path, input_artifact_type_mapping
        )
        entrypoint_command = [
            "python",
            "-m",
            "zenml.step_operators.entrypoint",
            "--main_module",
            main_module,
            "--step_source_path",
            step_source_path,
            "--execution_info_path",
            execution_info_path,
            "--input_artifact_types_path",
            input_artifact_types_path,
        ]

        logger.info(
            "Using step operator `%s` to run step `%s`.",
            step_operator.name,
            step_name,
        )
        logger.debug(
            "Step operator requirements: %s, entrypoint command: %s.",
            requirements,
            entrypoint_command,
        )
        step_operator.launch(
            pipeline_name=execution_info.pipeline_info.id,
            run_name=execution_info.pipeline_run_id,
            requirements=requirements,
            entrypoint_command=entrypoint_command,
        )

        return _read_executor_output(execution_info.execution_output_uri)
