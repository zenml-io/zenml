# Copyright 2020 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Builder for Kubeflow pipelines level proto spec."""

import random
import re
import string
from typing import Any, Dict, List, Optional

from absl import logging
from google.protobuf import json_format
from kfp.pipeline_spec import pipeline_spec_pb2 as pipeline_pb2
from tfx.dsl.components.base import base_node
from tfx.orchestration import data_types, pipeline

from zenml.integrations.kubeflow.orchestrators import (
    kubeflow_compiler_utils as compiler_utils,
)
from zenml.integrations.kubeflow.orchestrators import (
    kubeflow_parameter_utils as parameter_utils,
)
from zenml.integrations.kubeflow.orchestrators import (
    kubeflow_step_builder as step_builder,
)

_LEGAL_NAME_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,127}")


def _check_name(name: str) -> None:
    """Checks the user-provided pipeline name."""
    if not _LEGAL_NAME_PATTERN.fullmatch(name):
        raise ValueError(
            "User provided pipeline name % is illegal, please follow "
            "the pattern of [a-z0-9][a-z0-9-]{0,127}."
        )


def _generate_component_name_suffix() -> str:
    """Generates a random string for component name suffix."""
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(10))


class RuntimeConfigBuilder:
    """Kubeflow pipelines RuntimeConfig builder."""

    def __init__(
        self,
        pipeline_info: data_types.PipelineInfo,
        parameter_values: Dict[str, Any],
    ):
        """Creates a RuntimeConfigBuilder object.
        Args:
          pipeline_info: a TFX pipeline info object, containing pipeline root info.
          parameter_values: mapping from runtime parameter names to its values.
        """
        self._pipeline_root = pipeline_info.pipeline_root
        self._parameter_values = parameter_values or {}

    def build(self) -> pipeline_pb2.PipelineJob.RuntimeConfig:
        """Build a RuntimeConfig proto."""
        return pipeline_pb2.PipelineJob.RuntimeConfig(
            gcs_output_directory=self._pipeline_root,
            parameters={
                k: compiler_utils.get_kubeflow_value(v)
                for k, v in self._parameter_values.items()
            },
        )


class PipelineBuilder:
    """Kubeflow pipelines spec builder.
    Constructs a pipeline spec based on the TFX pipeline object.
    """

    def __init__(
        self,
        tfx_pipeline: pipeline.Pipeline,
        default_image: str,
        default_commands: Optional[List[str]] = None,
        exit_handler: Optional[base_node.BaseNode] = None,
    ):
        """Creates a PipelineBuilder object.
        A PipelineBuilder takes in a TFX pipeline object. Then
        PipelineBuilder.build() outputs Kubeflow PipelineSpec proto.
        Args:
          tfx_pipeline: A TFX pipeline object.
          default_image: Specifies the TFX container image used in CMLE container
            tasks. Can be overriden by per component specification.
          default_commands: Optionally specifies the commands of the provided
            container image. When not provided, the default `ENTRYPOINT` specified
            in the docker image is used. Note: the commands here refers to the K8S
              container command, which maps to Docker entrypoint field. If one
              supplies command but no args are provided for the container, the
              container will be invoked with the provided command, ignoring the
              `ENTRYPOINT` and `CMD` defined in the Dockerfile. One can find more
              details regarding the difference between K8S and Docker conventions at
            https://kubernetes.io/docs/tasks/inject-data-application/define-command-argument-container/#notes
          exit_handler: the optional custom component for post actions triggered
             after all pipeline tasks finish.
        """
        self._pipeline_info = tfx_pipeline.pipeline_info
        self._pipeline = tfx_pipeline
        self._default_image = default_image
        self._default_commands = default_commands
        self._exit_handler = exit_handler

    def build(self) -> pipeline_pb2.PipelineSpec:
        """Build a pipeline PipelineSpec."""

        _check_name(self._pipeline_info.pipeline_name)

        deployment_config = pipeline_pb2.PipelineDeploymentConfig()
        pipeline_info = pipeline_pb2.PipelineInfo(
            name=self._pipeline_info.pipeline_name
        )

        tfx_tasks = {}
        component_defs = {}
        # Map from (producer component id, output key) to (new producer component
        # id, output key)
        channel_redirect_map = {}
        with parameter_utils.ParameterContext() as pc:
            for component in self._pipeline.components:
                if (
                    self._exit_handler
                    and component.id == compiler_utils.TFX_DAG_NAME
                ):
                    component.with_id(
                        component.id + _generate_component_name_suffix()
                    )
                    logging.warning(
                        "_tfx_dag is system reserved name for pipeline with"
                        "exit handler, added suffix to your component name: %s",
                        component.id,
                    )
                # Here the topological order of components is required.
                # If a channel redirection is needed, redirect mapping is expected to be
                # available because the upstream node (which is the cause for
                # redirecting) is processed before the downstream consumer nodes.
                built_tasks = step_builder.StepBuilder(
                    node=component,
                    deployment_config=deployment_config,
                    component_defs=component_defs,
                    image=self._default_image,
                    image_cmds=self._default_commands,
                    beam_pipeline_args=self._pipeline.beam_pipeline_args,
                    enable_cache=self._pipeline.enable_cache,
                    pipeline_info=self._pipeline_info,
                    channel_redirect_map=channel_redirect_map,
                ).build()
                tfx_tasks.update(built_tasks)

        result = pipeline_pb2.PipelineSpec(pipeline_info=pipeline_info)

        # if exit handler is defined, put all the TFX tasks under tfx_dag,
        # exit handler is a separate component triggered by tfx_dag.
        if self._exit_handler:
            for name, task_spec in tfx_tasks.items():
                result.components[compiler_utils.TFX_DAG_NAME].dag.tasks[
                    name
                ].CopyFrom(task_spec)
            # construct root with exit handler
            exit_handler_task = step_builder.StepBuilder(
                node=self._exit_handler,
                deployment_config=deployment_config,
                component_defs=component_defs,
                image=self._default_image,
                image_cmds=self._default_commands,
                beam_pipeline_args=self._pipeline.beam_pipeline_args,
                enable_cache=self._pipeline.enable_cache,
                pipeline_info=self._pipeline_info,
                channel_redirect_map=channel_redirect_map,
                is_exit_handler=True,
            ).build()
            result.root.dag.tasks[
                compiler_utils.TFX_DAG_NAME
            ].component_ref.name = compiler_utils.TFX_DAG_NAME
            result.root.dag.tasks[
                compiler_utils.TFX_DAG_NAME
            ].task_info.name = compiler_utils.TFX_DAG_NAME
            result.root.dag.tasks[self._exit_handler.id].CopyFrom(
                exit_handler_task[self._exit_handler.id]
            )
        else:
            for name, task_spec in tfx_tasks.items():
                result.root.dag.tasks[name].CopyFrom(task_spec)

        result.deployment_spec.update(
            json_format.MessageToDict(deployment_config)
        )
        for name, component_def in component_defs.items():
            result.components[name].CopyFrom(component_def)

        # Attach runtime parameter to root's input parameter
        for param in pc.parameters:
            result.root.input_definitions.parameters[param.name].CopyFrom(
                compiler_utils.build_parameter_type_spec(param)
            )

        return result
