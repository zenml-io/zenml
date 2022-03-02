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

import argparse
import importlib
import json
import logging
import os
import sys
import textwrap
from typing import Dict, List, MutableMapping, Optional, Tuple, Type

from google.protobuf import json_format
from kubernetes import config as k8s_config
from tfx.dsl.compiler import constants
from tfx.orchestration import metadata
from tfx.orchestration.local import runner_utils
from tfx.orchestration.portable import (
    data_types,
    kubernetes_executor_operator,
    launcher,
    runtime_parameter_utils,
)
from tfx.proto.orchestration import executable_spec_pb2, pipeline_pb2
from tfx.types import artifact, channel, standard_artifacts
from tfx.types.channel import Property

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.artifacts.type_registry import type_registry
from zenml.exceptions import RepositoryNotFoundError
from zenml.integrations.registry import integration_registry
from zenml.orchestrators.utils import execute_step
from zenml.repository import Repository
from zenml.steps.utils import generate_component_class, _FunctionExecutor
from zenml.utils import source_utils
from tfx.orchestration.portable.data_types import ExecutionInfo
from tfx.dsl.components.base.base_executor import BaseExecutor
from tfx.orchestration.portable.python_executor_operator import run_with_executor
from tfx.proto.orchestration.execution_invocation_pb2 import ExecutionInvocation


def _create_executor_class(
    step_source_module_name: str,
    step_function_name: str,
    # input_artifact_type_mapping: Dict[str, str],
) -> Type[_FunctionExecutor]:
    """Creates an executor class for a given step and adds it to the target
    module.

    Args:
        step_source_module_name: Name of the module in which the step function
            is defined.
        step_function_name: Name of the step function.
        input_artifact_type_mapping: A dictionary mapping input names to
            a string representation of their artifact classes.
    """
    step_module = importlib.import_module(step_source_module_name)
    step_class = getattr(step_module, step_function_name)
    step_instance = step_class()

    materializers = step_instance.get_materializers(ensure_complete=True)

    input_spec = {}
    # for input_name, class_path in input_artifact_type_mapping.items():
    #     artifact_class = source_utils.load_source_path_class(class_path)
    #     if not issubclass(artifact_class, BaseArtifact):
    #         raise RuntimeError(
    #             f"Class `{artifact_class}` specified as artifact class for "
    #             f"input '{input_name}' is not a ZenML BaseArtifact subclass."
    #         )
    #     input_spec[input_name] = artifact_class

    for key, value in step_class.INPUT_SIGNATURE.items():
        input_spec[key] = BaseArtifact

    output_spec = {}
    for key, value in step_class.OUTPUT_SIGNATURE.items():
        output_spec[key] = type_registry.get_artifact_type(value)[0]

    execution_parameters = {
        **step_instance.PARAM_SPEC,
        **step_instance._internal_execution_parameters,
    }

    component_class = generate_component_class(
        step_name=step_instance.name,
        step_module=step_source_module_name,
        input_spec=input_spec,
        output_spec=output_spec,
        execution_parameter_names=set(execution_parameters),
        step_function=step_instance.entrypoint,
        materializers=materializers,
    )

    return component_class.EXECUTOR_SPEC.executor_class


def _parse_command_line_arguments() -> argparse.Namespace:
    """Parses the command line input arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--main_module", type=str, required=True)
    parser.add_argument("--step_module", type=str, required=True)
    parser.add_argument("--step_function_name", type=str, required=True)
    # parser.add_argument("--input_artifact_types", type=str, required=True)
    parser.add_argument("--execution_info", type=str, required=True)

    return parser.parse_args()


def main() -> None:
    """Runs a single step defined by the command line arguments."""
    # Log to the container's stdout so Kubeflow Pipelines UI can display logs to
    # the user.
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    logging.getLogger().setLevel(logging.INFO)

    args = _parse_command_line_arguments()

    # make sure all integrations are activated so all materializers etc. are
    # available
    integration_registry.activate_integrations()

    # import the user main module to register all the materializers
    importlib.import_module(args.main_module)

    executor_class = _create_executor_class(
        step_source_module_name=args.step_module,
        step_function_name=args.step_function_name,
        #executor_class_target_module_name=executor_class_target_module_name,
        # input_artifact_type_mapping=json.loads(args.input_artifact_types),
    )

    execution_info_proto = ExecutionInvocation.FromString(args.execution_info)
    execution_info = ExecutionInfo.from_proto(execution_info_proto)
    context = BaseExecutor.Context(
        tmp_dir=execution_info.tmp_dir,
        unique_id=str(execution_info.execution_id),
        executor_output_uri=execution_info.execution_output_uri,
        stateful_working_dir=execution_info.stateful_working_dir,
        pipeline_node=execution_info.pipeline_node,
        pipeline_info=execution_info.pipeline_info,
        pipeline_run_id=execution_info.pipeline_run_id)

    executor = executor_class(context=context)
    run_with_executor(execution_info=execution_info, executor=executor)


if __name__ == "__main__":
    main()
