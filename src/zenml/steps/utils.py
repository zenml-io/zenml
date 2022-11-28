#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

"""Utility functions for Steps.

The collection of utility functions/classes are inspired by their original
implementation of the Tensorflow Extended team, which can be found here:

https://github.com/tensorflow/tfx/blob/master/tfx/dsl/component/experimental
/decorators.py

This version is heavily adjusted to work with the Pipeline-Step paradigm which
is proposed by ZenML.
"""

from __future__ import absolute_import, division, print_function

import inspect
import json
import sys
import typing
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
)

import pydantic
from tfx.dsl.components.base.base_executor import BaseExecutor
from tfx.dsl.components.base.executor_spec import ExecutorClassSpec
from tfx.orchestration.portable import outputs_utils
from tfx.proto.orchestration import execution_result_pb2
from tfx.types import component_spec

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.config.step_configurations import StepConfiguration
from zenml.config.step_run_info import StepRunInfo
from zenml.exceptions import MissingStepParameterError, StepInterfaceError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.steps.step_context import StepContext
from zenml.steps.step_environment import StepEnvironment
from zenml.steps.step_output import Output
from zenml.utils import proto_utils, source_utils

if TYPE_CHECKING:
    from tfx.dsl.component.experimental.decorators import _SimpleComponent

    from zenml.config.step_configurations import ArtifactConfiguration
    from zenml.steps.base_step import BaseStep

logger = get_logger(__name__)

STEP_INNER_FUNC_NAME = "entrypoint"
SINGLE_RETURN_OUT_NAME = "output"
PARAM_STEP_NAME = "name"
PARAM_ENABLE_CACHE = "enable_cache"
PARAM_PIPELINE_PARAMETER_NAME = "pipeline_parameter_name"
PARAM_CREATED_BY_FUNCTIONAL_API = "created_by_functional_api"
PARAM_STEP_OPERATOR = "step_operator"
PARAM_EXPERIMENT_TRACKER = "experiment_tracker"
INTERNAL_EXECUTION_PARAMETER_PREFIX = "zenml-"
INSTANCE_CONFIGURATION = "INSTANCE_CONFIGURATION"
PARAM_OUTPUT_ARTIFACTS = "output_artifacts"
PARAM_OUTPUT_MATERIALIZERS = "output_materializers"
PARAM_SETTINGS = "settings"
PARAM_EXTRA_OPTIONS = "extra"


def resolve_type_annotation(obj: Any) -> Any:
    """Returns the non-generic class for generic aliases of the typing module.

    If the input is no generic typing alias, the input itself is returned.

    Example: if the input object is `typing.Dict`, this method will return the
    concrete class `dict`.

    Args:
        obj: The object to resolve.

    Returns:
        The non-generic class for generic aliases of the typing module.
    """
    from typing import _GenericAlias  # type: ignore[attr-defined]

    if sys.version_info >= (3, 8):
        return typing.get_origin(obj) or obj
    else:
        # python 3.7
        if isinstance(obj, _GenericAlias):
            return obj.__origin__
        else:
            return obj


def parse_return_type_annotations(
    step_annotations: Dict[str, Any]
) -> Dict[str, Any]:
    """Parse the returns of a step function into a dict of resolved types.

    Called within `BaseStepMeta.__new__()` to define `cls.OUTPUT_SIGNATURE`.
    Called within `Do()` to resolve type annotations.

    Args:
        step_annotations: Type annotations of the step function.

    Returns:
        Output signature of the new step class.
    """
    return_type = step_annotations.get("return", None)
    if return_type is None:
        return {}

    # Cast simple output types to `Output`.
    if not isinstance(return_type, Output):
        return_type = Output(**{SINGLE_RETURN_OUT_NAME: return_type})

    # Resolve type annotations of all outputs and save in new dict.
    output_signature = {
        output_name: resolve_type_annotation(output_type)
        for output_name, output_type in return_type.items()
    }
    return output_signature


def create_component_class(step: "BaseStep") -> Type["_SimpleComponent"]:
    """Creates a TFX component class.

    Args:
        step: The step for which to create the component class.

    Returns:
        The component class.
    """
    from tfx.dsl.component.experimental.decorators import _SimpleComponent

    executor_class = create_executor_class(step=step)
    component_spec_class = _create_component_spec_class(step=step)

    module, _ = source_utils.resolve_class(step.__class__).rsplit(".", 1)

    return type(
        step.configuration.name,
        (_SimpleComponent,),
        {
            "SPEC_CLASS": component_spec_class,
            "EXECUTOR_SPEC": ExecutorClassSpec(executor_class=executor_class),
            "__module__": module,
        },
    )


def _create_component_spec_class(
    step: "BaseStep",
) -> Type[component_spec.ComponentSpec]:
    """Creates a TFX component spec class.

    Args:
        step: The step for which to create the component spec class.

    Returns:
        The component spec class.
    """
    # Ensure that the step configuration is complete
    configuration = StepConfiguration.parse_obj(step.configuration)

    inputs = _create_channel_parameters(configuration.inputs)
    outputs = _create_channel_parameters(configuration.outputs)

    execution_parameter_names = set(configuration.parameters).union(
        step._internal_execution_parameters
    )
    parameters = {
        key: component_spec.ExecutionParameter(type=str)  # type: ignore[no-untyped-call] # noqa
        for key in execution_parameter_names
    }
    return type(
        f"{step.name}_Spec",
        (component_spec.ComponentSpec,),
        {
            "INPUTS": inputs,
            "OUTPUTS": outputs,
            "PARAMETERS": parameters,
            "__module__": __name__,
        },
    )


def _create_channel_parameters(
    artifacts: Mapping[str, "ArtifactConfiguration"]
) -> Dict[str, component_spec.ChannelParameter]:
    """Creates TFX channel parameters for ZenML artifacts.

    Args:
        artifacts: The ZenML artifacts.

    Returns:
        TFX channel parameters.
    """
    channel_parameters = {}
    for key, artifact_config in artifacts.items():
        artifact_class: Type[
            BaseArtifact
        ] = source_utils.load_and_validate_class(
            artifact_config.artifact_source, expected_class=BaseArtifact
        )
        channel_parameters[key] = component_spec.ChannelParameter(
            type=artifact_class
        )
    return channel_parameters


def create_executor_class(
    step: "BaseStep",
) -> Type["_ZenMLStepExecutor"]:
    """Creates an executor class for a step.

    Args:
        step: The step instance for which to create an executor class.

    Returns:
        The executor class.
    """
    executor_class_name = _get_executor_class_name(step.configuration.name)
    executor_class = type(
        executor_class_name,
        (_ZenMLStepExecutor,),
        {"_STEP": step, "__module__": __name__},
    )

    # Add the executor class to the current module, so tfx can load it
    module = sys.modules[__name__]
    setattr(module, executor_class_name, executor_class)

    return executor_class


def get_executor_class(step_name: str) -> Optional[Type["_ZenMLStepExecutor"]]:
    """Gets the executor class for a step.

    Args:
        step_name: Name of the step for which to get the executor class.

    Returns:
        The executor class.
    """
    executor_class_name = _get_executor_class_name(step_name)
    module = sys.modules[__name__]
    return getattr(module, executor_class_name, None)


def _get_executor_class_name(step_name: str) -> str:
    """Gets the executor class name for a step.

    Args:
        step_name: Name of the step for which to get the executor class name.

    Returns:
        The executor class name.
    """
    return f"{step_name}_Executor"


class _ZenMLStepExecutor(BaseExecutor):
    """TFX Executor which runs ZenML steps."""

    if TYPE_CHECKING:
        _STEP: ClassVar["BaseStep"]

    @property
    def configuration(self) -> StepConfiguration:
        """Configuration of the step to execute.

        Returns:
            The step configuration.
        """
        return StepConfiguration.parse_obj(self._STEP.configuration)

    def _load_output_materializers(self) -> Dict[str, Type[BaseMaterializer]]:
        """Loads the output materializers for the step.

        Returns:
            The step output materializers.
        """
        materializers = {}
        for name, output in self.configuration.outputs.items():
            materializer_class: Type[
                BaseMaterializer
            ] = source_utils.load_and_validate_class(
                output.materializer_source, expected_class=BaseMaterializer
            )
            materializers[name] = materializer_class
        return materializers

    def _load_input_artifact(
        self, artifact: BaseArtifact, data_type: Type[Any]
    ) -> Any:
        """Loads an input artifact.

        Args:
            artifact: The artifact to load.
            data_type: The data type of the artifact value.

        Returns:
            The artifact value.
        """
        # Skip materialization for BaseArtifact and its subtypes.
        if issubclass(data_type, BaseArtifact):
            if data_type != type(artifact):
                logger.warning(
                    f"You specified the data_type `{data_type}` but the actual "
                    f"artifact type from the previous step is "
                    f"`{type(artifact)}`. Ignoring this for now, but please be "
                    f"aware of this in your step code."
                )
            return artifact

        materializer_class = source_utils.load_source_path_class(
            artifact.materializer
        )
        materializer = materializer_class(artifact)
        return materializer.handle_input(data_type=data_type)

    def _store_output_artifact(
        self,
        materializer_class: Type[BaseMaterializer],
        materializer_source: str,
        artifact: BaseArtifact,
        data: Any,
    ) -> None:
        """Stores an output artifact.

        Args:
            materializer_class: The materializer class to store the artifact.
            materializer_source: The source of the materializer class.
            artifact: The artifact to store.
            data: The data to store in the artifact.
        """
        artifact.materializer = materializer_source
        artifact.datatype = source_utils.resolve_class(type(data))
        materializer_class(artifact).handle_return(data)

    def Do(
        self,
        input_dict: Dict[str, List[BaseArtifact]],
        output_dict: Dict[str, List[BaseArtifact]],
        exec_properties: Dict[str, Any],
    ) -> None:
        """Main block for the execution of the step.

        Args:
            input_dict: dictionary containing the input artifacts
            output_dict: dictionary containing the output artifacts
            exec_properties: dictionary containing the execution parameters

        Raises:
            MissingStepParameterError: if a required parameter is missing.
            RuntimeError: if the step fails.
            StepInterfaceError: if the step interface is not implemented.
        """
        from zenml.steps import BaseParameters

        step_name = self.configuration.name
        step_function = self._STEP.entrypoint
        output_materializers = self._load_output_materializers()

        # remove all ZenML internal execution properties
        exec_properties = {
            k: json.loads(v)
            for k, v in exec_properties.items()
            if not k.startswith(INTERNAL_EXECUTION_PARAMETER_PREFIX)
        }

        # Building the args for the entrypoint function
        function_params = {}

        # First, we parse the inputs, i.e., params and input artifacts.
        spec = inspect.getfullargspec(inspect.unwrap(step_function))
        args = spec.args

        if args and args[0] == "self":
            args.pop(0)

        for arg in args:
            arg_type = spec.annotations.get(arg, None)
            arg_type = resolve_type_annotation(arg_type)

            if issubclass(arg_type, BaseParameters):
                try:
                    config_object = arg_type.parse_obj(exec_properties)
                except pydantic.ValidationError as e:
                    missing_fields = [
                        str(field)
                        for error_dict in e.errors()
                        for field in error_dict["loc"]
                    ]

                    raise MissingStepParameterError(
                        step_name,
                        missing_fields,
                        arg_type,
                    ) from None
                function_params[arg] = config_object
            elif issubclass(arg_type, StepContext):
                output_artifacts = {k: v[0] for k, v in output_dict.items()}
                context = arg_type(
                    step_name=step_name,
                    output_materializers=output_materializers,
                    output_artifacts=output_artifacts,
                )
                function_params[arg] = context
            else:
                # At this point, it has to be an artifact, so we resolve
                function_params[arg] = self._load_input_artifact(
                    input_dict[arg][0], arg_type
                )

        if self._context is None:
            raise RuntimeError(
                "No TFX context is set for the currently running pipeline. "
                "Cannot retrieve pipeline runtime information."
            )

        pipeline_config = proto_utils.get_pipeline_config(
            self._context.pipeline_node
        )
        step_run_info = StepRunInfo(
            config=self.configuration,
            pipeline=pipeline_config,
            run_name=self._context.pipeline_run_id,
        )
        # Wrap the execution of the step function in a step environment
        # that the step function code can access to retrieve information about
        # the pipeline runtime, such as the current step name and the current
        # pipeline run ID
        with StepEnvironment(
            pipeline_name=self._context.pipeline_info.id,
            pipeline_run_id=self._context.pipeline_run_id,
            step_name=step_name,
            step_run_info=step_run_info,
            cache_enabled=self.configuration.enable_cache,
        ):
            return_values = step_function(**function_params)

        output_annotations = parse_return_type_annotations(spec.annotations)
        if len(output_annotations) > 0:
            # if there is only one output annotation (either directly specified
            # or contained in an `Output` tuple) we treat the step function
            # return value as the return for that output
            if len(output_annotations) == 1:
                return_values = [return_values]
            elif not isinstance(return_values, Sequence):
                # if the user defined multiple outputs, the return value must
                # be a sequence
                raise StepInterfaceError(
                    f"Wrong step function output type for step '{step_name}: "
                    f"Expected multiple outputs ({output_annotations}) but "
                    f"the function did not return a sequence-like object "
                    f"(actual return value: {return_values})."
                )
            elif len(output_annotations) != len(return_values):
                # if the user defined multiple outputs, the amount of actual
                # outputs must be the same
                raise StepInterfaceError(
                    f"Wrong amount of step function outputs for step "
                    f"'{step_name}: Expected {len(output_annotations)} outputs "
                    f"but the function returned {len(return_values)} outputs"
                    f"(return values: {return_values})."
                )

            for return_value, (output_name, output_type) in zip(
                return_values, output_annotations.items()
            ):
                if not isinstance(return_value, output_type):
                    raise StepInterfaceError(
                        f"Wrong type for output '{output_name}' of step "
                        f"'{step_name}' (expected type: {output_type}, "
                        f"actual type: {type(return_value)})."
                    )

                materializer_class = output_materializers[output_name]
                materializer_source = self.configuration.outputs[
                    output_name
                ].materializer_source

                self._store_output_artifact(
                    materializer_class=materializer_class,
                    materializer_source=materializer_source,
                    artifact=output_dict[output_name][0],
                    data=return_value,
                )

        # Write the executor output to the artifact store so the executor
        # operator (potentially not running on the same machine) can read it
        # to populate the metadata store
        executor_output = execution_result_pb2.ExecutorOutput()
        outputs_utils.populate_output_artifact(executor_output, output_dict)

        logger.debug(
            "Writing executor output to '%s'.",
            self._context.executor_output_uri,
        )
        with fileio.open(self._context.executor_output_uri, "wb") as f:
            f.write(executor_output.SerializeToString())
