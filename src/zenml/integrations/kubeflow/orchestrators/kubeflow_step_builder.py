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
"""Builder for Kubeflow pipelines StepSpec proto."""

import itertools
from typing import Any, Dict, List, Optional, Tuple

from absl import logging
from kfp.pipeline_spec import pipeline_spec_pb2 as pipeline_pb2
from ml_metadata.proto import metadata_store_pb2
from tfx import components
from tfx.components.evaluator import constants
from tfx.dsl.compiler import compiler_utils as tfx_compiler_utils
from tfx.dsl.component.experimental import executor_specs, placeholders
from tfx.dsl.components.base import base_component, base_node, executor_spec
from tfx.dsl.components.common import importer, resolver
from tfx.dsl.experimental.conditionals import conditional
from tfx.dsl.input_resolution.strategies import (
    latest_artifact_strategy,
    latest_blessed_model_strategy,
)
from tfx.orchestration import data_types
from tfx.types import artifact_utils, standard_artifacts
from tfx.types.channel import Channel
from tfx.utils import deprecation_utils

from zenml.integrations.kubeflow.orchestrators import (
    kubeflow_compiler_utils as compiler_utils,
)
from zenml.integrations.kubeflow.orchestrators import (
    kubeflow_decorators as decorators,
)
from zenml.integrations.kubeflow.orchestrators import (
    kubeflow_parameter_utils as parameter_utils,
)

_EXECUTOR_LABEL_PATTERN = "{}_executor"

# Task name suffix used for the ModelBlessing resolver part of
# latest blessed model resolver.
_MODEL_BLESSING_RESOLVER_SUFFIX = "-model-blessing-resolver"
# Task name suffix used for Model resolver part of latest blessed model
# resolver.
_MODEL_RESOLVER_SUFFIX = "-model-resolver"

# Input key used in model resolver spec.
_MODEL_RESOLVER_INPUT_KEY = "input"

# Shorthands for various specs in Kubeflow IR proto.
ResolverSpec = pipeline_pb2.PipelineDeploymentConfig.ResolverSpec
ImporterSpec = pipeline_pb2.PipelineDeploymentConfig.ImporterSpec
ContainerSpec = pipeline_pb2.PipelineDeploymentConfig.PipelineContainerSpec

_DRIVER_COMMANDS = (
    "python",
    "-m",
    "tfx.orchestration.kubeflow.v2.file_based_example_gen.driver",
)


def _resolve_command_line(
    container_spec: executor_specs.TemplatedExecutorContainerSpec,
    exec_properties: Dict[str, Any],
) -> List[str]:
    """Resolves placeholders in the command line of a container.
    Args:
      container_spec: Container structure to resolve
      exec_properties: The map of component's execution properties
    Returns:
      Resolved command line.
    Raises:
      TypeError: On unsupported type of command-line arguments, or when the
        resolved argument is not a string.
    """

    def expand_command_line_arg(
        cmd_arg: placeholders.CommandlineArgumentType,
    ) -> str:
        """Resolves a single argument."""
        if isinstance(cmd_arg, str):
            return cmd_arg
        elif isinstance(cmd_arg, placeholders.InputValuePlaceholder):
            if cmd_arg.input_name in exec_properties:
                return "{{$.inputs.parameters['%s']}}" % cmd_arg.input_name
            else:
                return "{{$.inputs.artifacts['%s'].value}}" % cmd_arg.input_name
        elif isinstance(cmd_arg, placeholders.InputUriPlaceholder):
            return "{{$.inputs.artifacts['%s'].uri}}" % cmd_arg.input_name
        elif isinstance(cmd_arg, placeholders.OutputUriPlaceholder):
            return "{{$.outputs.artifacts['%s'].uri}}" % cmd_arg.output_name
        elif isinstance(cmd_arg, placeholders.ConcatPlaceholder):
            resolved_items = [
                expand_command_line_arg(item) for item in cmd_arg.items
            ]
            for item in resolved_items:
                if not isinstance(item, str):
                    raise TypeError(
                        'Expanded item "{}" has incorrect type "{}"'.format(
                            item, type(item)
                        )
                    )
            return "".join(resolved_items)
        else:
            raise TypeError(
                'Unsupported type of command-line arguments: "{}".'
                " Supported types are {}.".format(
                    type(cmd_arg), str(executor_specs.CommandlineArgumentType)
                )
            )

    resolved_command_line = []
    for cmd_arg in container_spec.command or []:
        resolved_cmd_arg = expand_command_line_arg(cmd_arg)
        if not isinstance(resolved_cmd_arg, str):
            raise TypeError(
                'Resolved argument "{}" (type="{}") is not a string.'.format(
                    resolved_cmd_arg, type(resolved_cmd_arg)
                )
            )
        resolved_command_line.append(resolved_cmd_arg)

    return resolved_command_line


class StepBuilder:
    """Kubeflow pipelines task builder.
    Constructs a pipeline task spec based on the TFX node information. Meanwhile,
    augments the deployment config associated with the node.
    """

    def __init__(
        self,
        node: base_node.BaseNode,
        deployment_config: pipeline_pb2.PipelineDeploymentConfig,
        component_defs: Dict[str, pipeline_pb2.ComponentSpec],
        image: Optional[str] = None,
        image_cmds: Optional[List[str]] = None,
        beam_pipeline_args: Optional[List[str]] = None,
        enable_cache: bool = False,
        pipeline_info: Optional[data_types.PipelineInfo] = None,
        channel_redirect_map: Optional[Dict[Tuple[str, str], str]] = None,
        is_exit_handler: bool = False,
    ):
        """Creates a StepBuilder object.
        A StepBuilder takes in a TFX node object (usually it's a component/resolver/
        importer), together with other configuration (e.g., TFX image, beam args).
        Then, step_builder.build() outputs the StepSpec pb object.
        Args:
          node: A TFX node. The logical unit of a step. Note, currently for resolver
            node we only support two types of resolver
            policies, including: 1) latest blessed model, and 2) latest model
              artifact.
          deployment_config: The deployment config in Kubeflow IR to be populated.
          component_defs: Dict mapping from node id to compiled ComponetSpec proto.
            Items in the dict will get updated as the pipeline is built.
          image: TFX image used in the underlying container spec. Required if node
            is a TFX component.
          image_cmds: Optional. If not specified the default `ENTRYPOINT` defined
            in the docker image will be used. Note: the commands here refers to the
              K8S container command, which maps to Docker entrypoint field. If one
              supplies command but no args are provided for the container, the
              container will be invoked with the provided command, ignoring the
              `ENTRYPOINT` and `CMD` defined in the Dockerfile. One can find more
              details regarding the difference between K8S and Docker conventions at
            https://kubernetes.io/docs/tasks/inject-data-application/define-command-argument-container/#notes
          beam_pipeline_args: Pipeline arguments for Beam powered Components.
          enable_cache: If true, enables cache lookup for this pipeline step.
            Defaults to False.
          pipeline_info: Optionally, the pipeline info associated with current
            pipeline. The pipeline context is required if the current node is a
            resolver. Defaults to None.
          channel_redirect_map: Map from (producer component id, output key) to (new
            producer component id, output key). This is needed for cases where one
            DSL node is splitted into multiple tasks in pipeline API proto. For
            example, latest blessed model resolver.
          is_exit_handler: Marking whether the task is for exit handler.
        Raises:
          ValueError: On the following two cases:
            1. The node being built is an instance of BaseComponent but image was
               not provided.
            2. The node being built is a Resolver but the associated pipeline
               info was not provided.
        """
        self._name = node.id
        self._node = node
        self._deployment_config = deployment_config
        self._component_defs = component_defs
        self._inputs = node.inputs
        self._outputs = node.outputs
        self._enable_cache = enable_cache
        self._is_exit_handler = is_exit_handler
        if channel_redirect_map is None:
            self._channel_redirect_map = {}
        else:
            self._channel_redirect_map = channel_redirect_map

        self._exec_properties = node.exec_properties

        if isinstance(self._node, base_component.BaseComponent) and not image:
            raise ValueError(
                "TFX image is required for component of type %s"
                % type(self._node)
            )
        if isinstance(self._node, resolver.Resolver) and not pipeline_info:
            raise ValueError("pipeline_info is needed for resolver node.")

        self._tfx_image = image
        self._image_cmds = image_cmds
        self._beam_pipeline_args = beam_pipeline_args or []
        if isinstance(self._node.executor_spec, executor_spec.BeamExecutorSpec):
            self._beam_pipeline_args = (
                self._node.executor_spec.beam_pipeline_args
            )
        self._pipeline_info = pipeline_info

    def build(self) -> Dict[str, pipeline_pb2.PipelineTaskSpec]:  # noqa
        """Builds a pipeline PipelineTaskSpec given the node information.
        Each TFX node maps one task spec and usually one component definition and
        one executor spec. (with resolver node as an exception. See explaination
        in the Returns section).
         - Component definition includes interfaces of a node. For example, name
        and type information of inputs/outputs/execution_properties.
         - Task spec contains the topologies around the node. For example, the
        dependency nodes, where to read the inputs and exec_properties (from another
        task, from parent component or from a constant value). The task spec has the
        name of the component definition it references. It is possible that a task
        spec references an existing component definition that's built previously.
         - Executor spec encodes how the node is actually executed. For example,
        args to start a container, or query strings for resolvers. All executor spec
        will be packed into deployment config proto.
        During the build, all three parts mentioned above will be updated.
        Returns:
          A Dict mapping from node id to PipelineTaskSpec messages corresponding to
          the node. For most of the cases, the dict contains a single element.
          The only exception is when compiling latest blessed model resolver.
          One DSL node will be split to two resolver specs to reflect the
          two-phased query execution.
        Raises:
          NotImplementedError: When the node being built is an InfraValidator.
        """
        # 1. Resolver tasks won't have input artifacts in the API proto. First we
        #    specialcase two resolver types we support.
        if isinstance(self._node, resolver.Resolver):
            return self._build_resolver_spec()

        # 2. Build component spec.
        component_def = pipeline_pb2.ComponentSpec()
        task_spec = pipeline_pb2.PipelineTaskSpec()
        executor_label = _EXECUTOR_LABEL_PATTERN.format(self._name)
        component_def.executor_label = executor_label

        # Conditionals
        implicit_input_channels = {}
        implicit_upstream_node_ids = set()
        predicates = conditional.get_predicates(self._node)
        if predicates:
            implicit_keys_map = {
                tfx_compiler_utils.implicit_channel_key(channel): key
                for key, channel in self._inputs.items()
            }
            cel_predicates = []
            for predicate in predicates:
                for channel in predicate.dependent_channels():
                    implicit_key = tfx_compiler_utils.implicit_channel_key(
                        channel
                    )
                    if implicit_key not in implicit_keys_map:
                        # Store this channel and add it to the node inputs later.
                        implicit_input_channels[implicit_key] = channel
                        # Store the producer node and add it to the upstream nodes later.
                        implicit_upstream_node_ids.add(
                            channel.producer_component_id
                        )
                placeholder_pb = predicate.encode_with_keys(
                    tfx_compiler_utils.build_channel_to_key_fn(
                        implicit_keys_map
                    )
                )
                cel_predicates.append(
                    compiler_utils.placeholder_to_cel(placeholder_pb)
                )
            task_spec.trigger_policy.condition = " && ".join(cel_predicates)

        # Inputs
        for name, input_channel in itertools.chain(
            self._inputs.items(), implicit_input_channels.items()
        ):
            input_artifact_spec = compiler_utils.build_input_artifact_spec(
                input_channel
            )
            component_def.input_definitions.artifacts[name].CopyFrom(
                input_artifact_spec
            )
        # Outputs
        for name, output_channel in self._outputs.items():
            # Currently, we're working under the assumption that for tasks
            # (those generated by BaseComponent), each channel contains a single
            # artifact.
            output_artifact_spec = compiler_utils.build_output_artifact_spec(
                output_channel
            )
            component_def.output_definitions.artifacts[name].CopyFrom(
                output_artifact_spec
            )
        # Exec properties
        for name, value in self._exec_properties.items():
            # value can be None for unprovided optional exec properties.
            if value is None:
                continue
            parameter_type_spec = compiler_utils.build_parameter_type_spec(
                value
            )
            component_def.input_definitions.parameters[name].CopyFrom(
                parameter_type_spec
            )
        if self._name not in self._component_defs:
            self._component_defs[self._name] = component_def
        else:
            raise ValueError(
                f"Found duplicate component ids {self._name} while "
                "building component definitions."
            )

        # 3. Build task spec.
        task_spec.task_info.name = self._name
        dependency_ids = sorted(
            {node.id for node in self._node.upstream_nodes}
            | implicit_upstream_node_ids
        )

        for name, input_channel in itertools.chain(
            self._inputs.items(), implicit_input_channels.items()
        ):
            # TODO(b/169573945): Add support for vertex if requested.
            if not isinstance(input_channel, Channel):
                raise TypeError("Only single Channel is supported.")
            if self._is_exit_handler:
                logging.error(
                    "exit handler component doesn't take input artifact, "
                    "the input will be ignored."
                )
                continue
            # If the redirecting map is provided (usually for latest blessed model
            # resolver, we'll need to redirect accordingly. Also, the upstream node
            # list will be updated and replaced by the new producer id.
            producer_id = input_channel.producer_component_id
            output_key = input_channel.output_key
            for k, v in self._channel_redirect_map.items():
                if k[0] == producer_id and producer_id in dependency_ids:
                    dependency_ids.remove(producer_id)
                    dependency_ids.append(v[0])
            producer_id = self._channel_redirect_map.get(
                (producer_id, output_key), (producer_id, output_key)
            )[0]
            output_key = self._channel_redirect_map.get(
                (producer_id, output_key), (producer_id, output_key)
            )[1]
            input_artifact_spec = (
                pipeline_pb2.TaskInputsSpec.InputArtifactSpec()
            )
            input_artifact_spec.task_output_artifact.producer_task = producer_id
            input_artifact_spec.task_output_artifact.output_artifact_key = (
                output_key
            )
            task_spec.inputs.artifacts[name].CopyFrom(input_artifact_spec)
        for name, value in self._exec_properties.items():
            if value is None:
                continue
            if isinstance(value, data_types.RuntimeParameter):
                parameter_utils.attach_parameter(value)
                task_spec.inputs.parameters[
                    name
                ].component_input_parameter = value.name
            elif isinstance(value, decorators.FinalStatusStr):
                if not self._is_exit_handler:
                    logging.error(
                        "FinalStatusStr type is only allowed to use in exit"
                        " handler. The parameter is ignored."
                    )
                else:
                    task_spec.inputs.parameters[
                        name
                    ].task_final_status.producer_task = (
                        compiler_utils.TFX_DAG_NAME
                    )
            else:
                task_spec.inputs.parameters[name].CopyFrom(
                    pipeline_pb2.TaskInputsSpec.InputParameterSpec(
                        runtime_value=compiler_utils.value_converter(value)
                    )
                )

        task_spec.component_ref.name = self._name

        dependency_ids = sorted(dependency_ids)
        for dependency in dependency_ids:
            task_spec.dependent_tasks.append(dependency)

        if self._enable_cache:
            task_spec.caching_options.CopyFrom(
                pipeline_pb2.PipelineTaskSpec.CachingOptions(
                    enable_cache=self._enable_cache
                )
            )

        if self._is_exit_handler:
            task_spec.trigger_policy.strategy = (
                pipeline_pb2.PipelineTaskSpec.TriggerPolicy.ALL_UPSTREAM_TASKS_COMPLETED
            )
            task_spec.dependent_tasks.append(compiler_utils.TFX_DAG_NAME)

        # 4. Build the executor body for other common tasks.
        executor = pipeline_pb2.PipelineDeploymentConfig.ExecutorSpec()
        if isinstance(self._node, importer.Importer):
            executor.importer.CopyFrom(self._build_importer_spec())
        elif isinstance(self._node, components.FileBasedExampleGen):
            executor.container.CopyFrom(
                self._build_file_based_example_gen_spec()
            )
        elif isinstance(self._node, (components.InfraValidator)):
            raise NotImplementedError(
                'The componet type "{}" is not supported'.format(
                    type(self._node)
                )
            )
        else:
            executor.container.CopyFrom(self._build_container_spec())
        self._deployment_config.executors[executor_label].CopyFrom(executor)

        return {self._name: task_spec}

    def _build_container_spec(self) -> ContainerSpec:
        """Builds the container spec for a component.
        Returns:
          The PipelineContainerSpec represents the container execution of the
          component.
        Raises:
          NotImplementedError: When the executor class is neither ExecutorClassSpec
          nor TemplatedExecutorContainerSpec.
        """
        assert isinstance(self._node, base_component.BaseComponent)
        if isinstance(
            self._node.executor_spec,
            executor_specs.TemplatedExecutorContainerSpec,
        ):
            container_spec = self._node.executor_spec
            result = ContainerSpec(
                image=container_spec.image,
                command=_resolve_command_line(
                    container_spec=container_spec,
                    exec_properties=self._node.exec_properties,
                ),
            )
            return result

        # The container entrypoint format below assumes ExecutorClassSpec.
        if not isinstance(
            self._node.executor_spec, executor_spec.ExecutorClassSpec
        ):
            raise NotImplementedError(
                "Executor spec: % is not supported in Kubeflow V2 yet."
                "Currently only ExecutorClassSpec is supported."
            )

        result = ContainerSpec()
        result.image = self._tfx_image
        if self._image_cmds:
            for cmd in self._image_cmds:
                result.command.append(cmd)
        executor_path = "%s.%s" % (
            self._node.executor_spec.executor_class.__module__,
            self._node.executor_spec.executor_class.__name__,
        )
        # Resolve container arguments.
        result.args.append("--executor_class_path")
        result.args.append(executor_path)
        result.args.append("--json_serialized_invocation_args")
        result.args.append("{{$}}")
        result.args.extend(self._beam_pipeline_args)

        return result

    def _build_file_based_example_gen_spec(self) -> ContainerSpec:
        """Builds FileBasedExampleGen into a PipelineContainerSpec.
        Returns:
          The PipelineContainerSpec represents the container execution of the
          component, which should includes both the driver execution, and the
          executor execution.
        Raises:
          ValueError: When the node is a FileBasedExampleGen but tfx image was not
            specified.
        """
        assert isinstance(self._node, components.FileBasedExampleGen)
        if not self._tfx_image:
            raise ValueError("TFX image is required for FileBasedExampleGen.")

        # 1. Build the driver container execution by setting the pre_cache_check
        # hook.
        result = ContainerSpec()
        driver_hook = ContainerSpec.Lifecycle(
            pre_cache_check=ContainerSpec.Lifecycle.Exec(
                command=_DRIVER_COMMANDS,
                args=[
                    "--json_serialized_invocation_args",
                    "{{$}}",
                ],
            )
        )
        driver_hook.pre_cache_check.args.extend(self._beam_pipeline_args)
        result.lifecycle.CopyFrom(driver_hook)

        # 2. Build the executor container execution in the same way as a regular
        # component.
        result.image = self._tfx_image
        if self._image_cmds:
            for cmd in self._image_cmds:
                result.command.append(cmd)
        executor_path = "%s.%s" % (
            self._node.executor_spec.executor_class.__module__,
            self._node.executor_spec.executor_class.__name__,
        )
        # Resolve container arguments.
        result.args.append("--executor_class_path")
        result.args.append(executor_path)
        result.args.append("--json_serialized_invocation_args")
        result.args.append("{{$}}")
        result.args.extend(self._beam_pipeline_args)
        return result

    def _build_importer_spec(self) -> ImporterSpec:
        """Builds ImporterSpec."""
        assert isinstance(self._node, importer.Importer)
        output_channel = self._node.outputs[importer.IMPORT_RESULT_KEY]
        result = ImporterSpec()

        # Importer's output channel contains one artifact instance with
        # additional properties.
        artifact_instance = list(output_channel.get())[0]
        struct_proto = compiler_utils.pack_artifact_properties(
            artifact_instance
        )
        if struct_proto:
            result.metadata.CopyFrom(struct_proto)

        result.reimport = bool(
            self._exec_properties[importer.REIMPORT_OPTION_KEY]
        )

        # 'artifact_uri' property of Importer node should be string, but the type
        # is not checked (except the pytype hint) in Importer node.
        # It is possible to escape the type constraint and pass a RuntimeParameter.
        # If that happens, we need to overwrite the runtime parameter name to
        # 'artifact_uri', instead of using the name of user-provided runtime
        # parameter.
        if isinstance(
            self._exec_properties[importer.SOURCE_URI_KEY],
            data_types.RuntimeParameter,
        ):
            result.artifact_uri.runtime_parameter = importer.SOURCE_URI_KEY
        else:
            result.artifact_uri.CopyFrom(
                compiler_utils.value_converter(
                    self._exec_properties[importer.SOURCE_URI_KEY]
                )
            )

        single_artifact = artifact_utils.get_single_instance(
            list(output_channel.get())
        )
        result.type_schema.CopyFrom(
            pipeline_pb2.ArtifactTypeSchema(
                instance_schema=compiler_utils.get_artifact_schema(
                    single_artifact
                )
            )
        )

        return result

    def _build_latest_artifact_resolver(
        self,
    ) -> Dict[str, pipeline_pb2.PipelineTaskSpec]:
        """Builds a resolver spec for a latest artifact resolver.
        Returns:
          A list of two PipelineTaskSpecs. One represents the query for latest valid
          ModelBlessing artifact. Another one represents the query for latest
          blessed Model artifact.
        Raises:
          ValueError: when desired_num_of_artifacts != 1. 1 is the only supported
            value currently.
        """
        # Fetch the init kwargs for the resolver.
        resolver_config = self._exec_properties[resolver.RESOLVER_CONFIG]
        if (
            isinstance(resolver_config, dict)
            and resolver_config.get("desired_num_of_artifacts", 0) > 1
        ):
            raise ValueError(
                "Only desired_num_of_artifacts=1 is supported currently."
                " Got {}".format(
                    resolver_config.get("desired_num_of_artifacts")
                )
            )

        component_def = pipeline_pb2.ComponentSpec()
        executor_label = _EXECUTOR_LABEL_PATTERN.format(self._name)
        component_def.executor_label = executor_label
        task_spec = pipeline_pb2.PipelineTaskSpec()
        task_spec.task_info.name = self._name

        for name, output_channel in self._outputs.items():
            output_artifact_spec = compiler_utils.build_output_artifact_spec(
                output_channel
            )
            component_def.output_definitions.artifacts[name].CopyFrom(
                output_artifact_spec
            )
        for name, value in self._exec_properties.items():
            if value is None:
                continue
            parameter_type_spec = compiler_utils.build_parameter_type_spec(
                value
            )
            component_def.input_definitions.parameters[name].CopyFrom(
                parameter_type_spec
            )
            if isinstance(value, data_types.RuntimeParameter):
                parameter_utils.attach_parameter(value)
                task_spec.inputs.parameters[
                    name
                ].component_input_parameter = value.name
            else:
                task_spec.inputs.parameters[name].CopyFrom(
                    pipeline_pb2.TaskInputsSpec.InputParameterSpec(
                        runtime_value=compiler_utils.value_converter(value)
                    )
                )
        self._component_defs[self._name] = component_def
        task_spec.component_ref.name = self._name

        artifact_queries = {}
        # Buid the artifact query for each channel in the input dict.
        for name, c in self._inputs.items():
            query_filter = ('schema_title="{type}" AND state={state}').format(
                type=compiler_utils.get_artifact_title(c.type),
                state=metadata_store_pb2.Artifact.State.Name(
                    metadata_store_pb2.Artifact.LIVE
                ),
            )
            # Resolver's output dict has the same set of keys as its input dict.
            artifact_queries[name] = ResolverSpec.ArtifactQuerySpec(
                filter=query_filter
            )

        resolver_spec = ResolverSpec(output_artifact_queries=artifact_queries)
        executor = pipeline_pb2.PipelineDeploymentConfig.ExecutorSpec()
        executor.resolver.CopyFrom(resolver_spec)
        self._deployment_config.executors[executor_label].CopyFrom(executor)
        return {self._name: task_spec}

    def _build_resolver_for_latest_model_blessing(
        self, model_blessing_channel_key: str
    ) -> pipeline_pb2.PipelineTaskSpec:
        """Builds the resolver spec for latest valid ModelBlessing artifact."""
        name = "{}{}".format(self._name, _MODEL_BLESSING_RESOLVER_SUFFIX)

        # Component def.
        component_def = pipeline_pb2.ComponentSpec()
        executor_label = _EXECUTOR_LABEL_PATTERN.format(name)
        component_def.executor_label = executor_label
        output_artifact_spec = compiler_utils.build_output_artifact_spec(
            self._outputs[model_blessing_channel_key]
        )
        component_def.output_definitions.artifacts[
            model_blessing_channel_key
        ].CopyFrom(output_artifact_spec)
        self._component_defs[name] = component_def

        # Task spec.
        task_spec = pipeline_pb2.PipelineTaskSpec()
        task_spec.task_info.name = name
        task_spec.component_ref.name = name

        # Builds the resolver executor spec for latest valid ModelBlessing.
        executor = pipeline_pb2.PipelineDeploymentConfig.ExecutorSpec()
        artifact_queries = {}
        query_filter = (
            'schema_title="{type}" AND state={state}'
            " AND metadata.{key}.number_value={value}"
        ).format(
            type=compiler_utils.get_artifact_title(
                standard_artifacts.ModelBlessing
            ),
            state=metadata_store_pb2.Artifact.State.Name(
                metadata_store_pb2.Artifact.LIVE
            ),
            key=constants.ARTIFACT_PROPERTY_BLESSED_KEY,
            value=constants.BLESSED_VALUE,
        )
        artifact_queries[
            model_blessing_channel_key
        ] = ResolverSpec.ArtifactQuerySpec(filter=query_filter)
        executor.resolver.CopyFrom(
            ResolverSpec(output_artifact_queries=artifact_queries)
        )
        self._deployment_config.executors[executor_label].CopyFrom(executor)

        return task_spec

    def _build_resolver_for_latest_blessed_model(
        self,
        model_channel_key: str,
        model_blessing_resolver_name: str,
        model_blessing_channel_key: str,
    ) -> pipeline_pb2.PipelineTaskSpec:
        """Builds the resolver spec for latest blessed Model artifact."""
        name = "{}{}".format(self._name, _MODEL_RESOLVER_SUFFIX)

        # Component def.
        component_def = pipeline_pb2.ComponentSpec()
        executor_label = _EXECUTOR_LABEL_PATTERN.format(name)
        component_def.executor_label = executor_label
        input_artifact_spec = compiler_utils.build_input_artifact_spec(
            self._outputs[model_blessing_channel_key]
        )
        component_def.input_definitions.artifacts[
            _MODEL_RESOLVER_INPUT_KEY
        ].CopyFrom(input_artifact_spec)
        output_artifact_spec = compiler_utils.build_output_artifact_spec(
            self._outputs[model_channel_key]
        )
        component_def.output_definitions.artifacts[model_channel_key].CopyFrom(
            output_artifact_spec
        )
        self._component_defs[name] = component_def

        # Task spec.
        task_spec = pipeline_pb2.PipelineTaskSpec()
        task_spec.task_info.name = name
        task_spec.component_ref.name = name
        input_artifact_spec = pipeline_pb2.TaskInputsSpec.InputArtifactSpec()
        input_artifact_spec.task_output_artifact.producer_task = (
            model_blessing_resolver_name
        )
        input_artifact_spec.task_output_artifact.output_artifact_key = (
            model_blessing_channel_key
        )
        task_spec.inputs.artifacts[_MODEL_RESOLVER_INPUT_KEY].CopyFrom(
            input_artifact_spec
        )

        # Resolver executor spec.
        executor = pipeline_pb2.PipelineDeploymentConfig.ExecutorSpec()
        artifact_queries = {}
        query_filter = (
            'schema_title="{type}" AND '
            "state={state} AND "
            "name=\"{{{{$.inputs.artifacts['{input_key}']"
            ".metadata['{property_key}']}}}}\""
        ).format(
            type=compiler_utils.get_artifact_title(standard_artifacts.Model),
            state=metadata_store_pb2.Artifact.State.Name(
                metadata_store_pb2.Artifact.LIVE
            ),
            input_key=_MODEL_RESOLVER_INPUT_KEY,
            property_key=constants.ARTIFACT_PROPERTY_CURRENT_MODEL_ID_KEY,
        )
        artifact_queries[model_channel_key] = ResolverSpec.ArtifactQuerySpec(
            filter=query_filter
        )
        executor.resolver.CopyFrom(
            ResolverSpec(output_artifact_queries=artifact_queries)
        )
        self._deployment_config.executors[executor_label].CopyFrom(executor)

        return task_spec

    def _build_latest_blessed_model_resolver(
        self,
    ) -> Dict[str, pipeline_pb2.PipelineTaskSpec]:
        """Builds two resolver specs to resolve the latest blessed model."""
        # The two phased resolution logic will be mapped to the following:
        # 1. A ResolverSpec to get the latest ModelBlessing artifact under the
        #    current context, with a valid current_model_id custom property
        #    attached; and
        # 2. A ResolverSpec to get the latest Model artifact under the current
        #    context, where the unique name of the artifact is corresponding to
        #    the current_model_id field in step 1.
        #
        # Such conversion will generate two PipelineTaskSpec:
        # 1. A TaskSpec with the name '{component_id}-model-blessing-resolver',
        #    where component_id is the original node id from the DSL resolver node.
        #    This TaskSpec has no input artifact but one output artifacts,
        #    which is the latest valid ModelBlessing artifact it
        #    finds.
        # 2. A TaskSpec with the name '{component_id}-model-resolver'. This TaskSpec
        #    has one input artifact connected to the 'model_blessing' output of
        #    '{component_id}-model-blessing-resolver', representing the latest
        #    blessed model it finds in MLMD under the same context.
        assert len(self._inputs) == 2, "Expecting 2 input Channels"

        model_channel_key, model_blessing_channel_key = None, None
        # Find the output key for ModelBlessing and Model, respectively
        for name, c in self._inputs.items():
            if issubclass(c.type, standard_artifacts.ModelBlessing):
                model_blessing_channel_key = name
            elif issubclass(c.type, standard_artifacts.Model):
                model_channel_key = name

        assert model_channel_key is not None, "Expecting Model as input"
        assert model_blessing_channel_key is not None, (
            "Expecting ModelBlessing as" " input"
        )

        model_blessing_resolver = (
            self._build_resolver_for_latest_model_blessing(
                model_blessing_channel_key
            )
        )

        model_resolver = self._build_resolver_for_latest_blessed_model(
            model_channel_key=model_channel_key,
            model_blessing_resolver_name=model_blessing_resolver.task_info.name,
            model_blessing_channel_key=model_blessing_channel_key,
        )

        # 5. Modify the channel_redirect_map passed in.
        self._channel_redirect_map[(self._node.id, model_channel_key)] = (
            model_resolver.task_info.name,
            model_channel_key,
        )
        self._channel_redirect_map[
            (self._node.id, model_blessing_channel_key)
        ] = (
            model_blessing_resolver.task_info.name,
            model_blessing_channel_key,
        )

        return {
            model_blessing_resolver.task_info.name: model_blessing_resolver,
            model_resolver.task_info.name: model_resolver,
        }

    def _build_resolver_spec(self) -> Dict[str, pipeline_pb2.PipelineTaskSpec]:
        """Validates and builds ResolverSpec for this node.
        Returns:
          A list of PipelineTaskSpec represents the (potentially multiple) resolver
          task(s).
        Raises:
          TypeError: When get unsupported resolver policy. Currently only support
            LatestBlessedModelStrategy and LatestArtifactsStrategy.
        """
        assert isinstance(self._node, resolver.Resolver)

        strategy_cls = self._exec_properties[resolver.RESOLVER_STRATEGY_CLASS]
        strategy_cls = deprecation_utils.get_first_nondeprecated_class(
            strategy_cls
        )
        if (
            strategy_cls
            == latest_blessed_model_strategy.LatestBlessedModelStrategy
        ):
            return self._build_latest_blessed_model_resolver()
        elif strategy_cls == latest_artifact_strategy.LatestArtifactStrategy:
            return self._build_latest_artifact_resolver()
        else:
            raise TypeError(
                "Unexpected resolver policy encountered. Currently "
                "only support LatestArtifactStrategy and LatestBlessedModelStrategy "
                f"but got: {strategy_cls}."
            )
