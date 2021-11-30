#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""This is an unmodified copy from the TFX source code (outside of superficial, stylistic changes)

Decorators for defining components via Python functions in Vertex AI.
"""
import types
from typing import Any, Callable

from tfx.dsl.component.experimental.decorators import component


def exit_handler(func: types.FunctionType) -> Callable[..., Any]:
    """Creates an exit handler from a typehint-annotated Python function.
    This decorator creates an exit handler wrapping the component typehint
    annotation - typehint annotations specified for the arguments and return value
    for a Python function.
    Exit handler is to annotate the component for post actions of a pipeline,
    only supported in Vertex AI. Specifically, function
    arguments can be annotated with the following types and associated semantics
    supported in component. In order to get in the final status of dependent
    pipeline, parameter should be defined as Parameter[str], passing in
    FinalStatusStr type when initializing the component.
    This is example usage of component definition using this decorator:
    ```
      from tfx import v1 as tfx
      @tfx.orchestration.experimental.exit_handler
      def MyExitHandlerComponent(final_status: tfx.dsl.components.Parameter[str]):
        # parse the final status
        pipeline_task_status = pipeline_pb2.PipelineTaskFinalStatus()
        proto_utils.json_to_proto(final_status, pipeline_task_status)
        print(pipeline_task_status)
    ```
    Example usage in a Vertex AI graph definition:
    ```
      exit_handler = exit_handler_component(
      final_status=tfx.dsl.experimental.FinalStatusStr())
      dsl_pipeline = tfx.dsl.Pipeline(...)
      runner = tfx.orchestration.experimental.KubeflowV2DagRunner(...)
      runner.set_exit_handler([exit_handler])
      runner.run(pipeline=dsl_pipeline)
    ```
    Experimental: no backwards compatibility guarantees.
    Args:
      func: Typehint-annotated component executor function.
    Returns:
      `base_component.BaseComponent` subclass for the given component executor
      function.
    """
    return component(func)


class FinalStatusStr(str):
    """FinalStatusStr: is the type for parameter receiving PipelineTaskFinalStatus.
    Vertex AI backend passes in jsonlized string of
    kfp.pipeline_spec.pipeline_spec_pb2.PipelineTaskFinalStatus.
    This is example usage of FinalStatusStr definition:
    ```
    exit_handler = exit_handler_component(
        final_status=tfx.dsl.experimental.FinalStatusStr())
    ```
    """
