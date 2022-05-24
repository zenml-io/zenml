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

"""
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
    Any,
    Callable,
    ClassVar,
    Dict,
    ItemsView,
    Iterator,
    KeysView,
    List,
    Optional,
    Sequence,
    Set,
    Type,
    ValuesView,
)

import pydantic
from tfx.dsl.component.experimental.decorators import _SimpleComponent
from tfx.dsl.components.base.base_executor import BaseExecutor
from tfx.dsl.components.base.executor_spec import ExecutorClassSpec
from tfx.orchestration.portable import outputs_utils
from tfx.proto.orchestration import execution_result_pb2
from tfx.types import component_spec
from tfx.types.channel import Channel
from tfx.utils import json_utils

from zenml.artifacts.base_artifact import BaseArtifact
from zenml.exceptions import MissingStepParameterError, StepInterfaceError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.steps.base_step_config import BaseStepConfig
from zenml.steps.step_context import StepContext
from zenml.steps.step_environment import StepEnvironment
from zenml.steps.step_output import Output
from zenml.utils import source_utils

logger = get_logger(__name__)

STEP_INNER_FUNC_NAME: str = "entrypoint"
SINGLE_RETURN_OUT_NAME: str = "output"
PARAM_STEP_NAME: str = "step_name"
PARAM_ENABLE_CACHE: str = "enable_cache"
PARAM_PIPELINE_PARAMETER_NAME: str = "pipeline_parameter_name"
PARAM_CREATED_BY_FUNCTIONAL_API: str = "created_by_functional_api"
PARAM_CUSTOM_STEP_OPERATOR: str = "custom_step_operator"
INTERNAL_EXECUTION_PARAMETER_PREFIX: str = "zenml-"
INSTANCE_CONFIGURATION: str = "INSTANCE_CONFIGURATION"
OUTPUT_SPEC: str = "OUTPUT_SPEC"


def do_types_match(type_a: Type[Any], type_b: Type[Any]) -> bool:
    """Check whether type_a and type_b match.

    Args:
        type_a: First Type to check.
        type_b: Second Type to check.

    Returns:
        True if types match, otherwise False.
    """
    # TODO [ENG-158]: Check more complicated cases where type_a can be a sub-type
    #  of type_b
    return type_a == type_b


def resolve_type_annotation(obj: Any) -> Any:
    """Returns the non-generic class for generic aliases of the typing module.

    If the input is no generic typing alias, the input itself is returned.

    Example: if the input object is `typing.Dict`, this method will return the
    concrete class `dict`.
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


def generate_component_spec_class(
    step_name: str,
    input_spec: Dict[str, Type[BaseArtifact]],
    output_spec: Dict[str, Type[BaseArtifact]],
    execution_parameter_names: Set[str],
) -> Type[component_spec.ComponentSpec]:
    """Generates a TFX component spec class for a ZenML step.

    Args:
        step_name: Name of the step for which the component will be created.
        input_spec: Input artifacts of the step.
        output_spec: Output artifacts of the step
        execution_parameter_names: Execution parameter names of the step.

    Returns:
        A TFX component spec class.
    """
    inputs = {
        key: component_spec.ChannelParameter(type=artifact_type)
        for key, artifact_type in input_spec.items()
    }
    outputs = {
        key: component_spec.ChannelParameter(type=artifact_type)
        for key, artifact_type in output_spec.items()
    }
    parameters = {
        key: component_spec.ExecutionParameter(type=str)  # type: ignore[no-untyped-call] # noqa
        for key in execution_parameter_names
    }
    return type(
        f"{step_name}_Spec",
        (component_spec.ComponentSpec,),
        {
            "INPUTS": inputs,
            "OUTPUTS": outputs,
            "PARAMETERS": parameters,
        },
    )


def generate_component_class(
    step_name: str,
    step_module: str,
    input_spec: Dict[str, Type[BaseArtifact]],
    output_spec: Dict[str, Type[BaseArtifact]],
    execution_parameter_names: Set[str],
    step_function: Callable[..., Any],
    materializers: Dict[str, Type[BaseMaterializer]],
) -> Type["_ZenMLSimpleComponent"]:
    """Generates a TFX component class for a ZenML step.

    Args:
        step_name: Name of the step for which the component will be created.
        step_module: Module in which the step class is defined.
        input_spec: Input artifacts of the step.
        output_spec: Output artifacts of the step
        execution_parameter_names: Execution parameter names of the step.
        step_function: The actual function to execute when running the step.
        materializers: Materializer classes for all outputs of the step.

    Returns:
        A TFX component class.
    """
    component_spec_class = generate_component_spec_class(
        step_name=step_name,
        input_spec=input_spec,
        output_spec=output_spec,
        execution_parameter_names=execution_parameter_names,
    )

    # Create executor class
    executor_class_name = f"{step_name}_Executor"
    executor_class = type(
        executor_class_name,
        (_FunctionExecutor,),
        {
            "_FUNCTION": staticmethod(step_function),
            "__module__": step_module,
            "materializers": materializers,
            PARAM_STEP_NAME: step_name,
        },
    )

    # Add the executor class to the module in which the step was defined
    module = sys.modules[step_module]
    setattr(module, executor_class_name, executor_class)

    return type(
        step_name,
        (_ZenMLSimpleComponent,),
        {
            "SPEC_CLASS": component_spec_class,
            "EXECUTOR_SPEC": ExecutorClassSpec(executor_class=executor_class),
            "__module__": step_module,
        },
    )


class _PropertyDictWrapper(json_utils.Jsonable):
    """Helper class to wrap inputs/outputs from TFX nodes.
    Currently, this class is read-only (setting properties is not implemented).
    Internal class: no backwards compatibility guarantees.
    Code Credit: https://github.com/tensorflow/tfx/blob
    /51946061ae3be656f1718a3d62cd47228b89b8f4/tfx/types/node_common.py
    """

    def __init__(
        self,
        data: Dict[str, Channel],
        compat_aliases: Optional[Dict[str, str]] = None,
    ):
        """Initializes the wrapper object.

        Args:
            data: The data to be wrapped.
            compat_aliases: Compatibility aliases to support deprecated keys.
        """
        self._data = data
        self._compat_aliases = compat_aliases or {}

    def __iter__(self) -> Iterator[str]:
        """Returns a generator that yields keys of the wrapped dictionary."""
        yield from self._data

    def __getitem__(self, key: str) -> Channel:
        """Returns the dictionary value for the specified key."""
        if key in self._compat_aliases:
            key = self._compat_aliases[key]
        return self._data[key]

    def __getattr__(self, key: str) -> Channel:
        """Returns the dictionary value for the specified key."""
        if key in self._compat_aliases:
            key = self._compat_aliases[key]
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError

    def __repr__(self) -> str:
        """Returns the representation of the wrapped dictionary."""
        return repr(self._data)

    def get_all(self) -> Dict[str, Channel]:
        """Returns the wrapped dictionary."""
        return self._data

    def keys(self) -> KeysView[str]:
        """Returns the keys of the wrapped dictionary."""
        return self._data.keys()

    def values(self) -> ValuesView[Channel]:
        """Returns the values of the wrapped dictionary."""
        return self._data.values()

    def items(self) -> ItemsView[str, Channel]:
        """Returns the items of the wrapped dictionary."""
        return self._data.items()


class _ZenMLSimpleComponent(_SimpleComponent):
    """Simple ZenML TFX component with outputs overridden."""

    @property
    def outputs(self) -> _PropertyDictWrapper:  # type: ignore[override]
        """Returns the wrapped spec outputs."""
        return _PropertyDictWrapper(self.spec.outputs)


class _FunctionExecutor(BaseExecutor):
    """Base TFX Executor class which is compatible with ZenML steps"""

    _FUNCTION = staticmethod(lambda: None)
    materializers: ClassVar[
        Optional[Dict[str, Type["BaseMaterializer"]]]
    ] = None

    def resolve_materializer_with_registry(
        self, param_name: str, artifact: BaseArtifact
    ) -> Type[BaseMaterializer]:
        """Resolves the materializer for the given obj_type.

        Args:
            param_name: Name of param.
            artifact: A TFX artifact type.

        Returns:
            The right materializer based on the defaults or optionally the one
            set by the user.
        """
        if not self.materializers:
            raise ValueError("Materializers are missing is not set!")

        materializer_class = self.materializers[param_name]
        return materializer_class

    def resolve_input_artifact(
        self, artifact: BaseArtifact, data_type: Type[Any]
    ) -> Any:
        """Resolves an input artifact, i.e., reading it from the Artifact Store
        to a pythonic object.

        Args:
            artifact: A TFX artifact type.
            data_type: The type of data to be materialized.

        Returns:
            Return the output of `handle_input()` of selected materializer.
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

        materializer = source_utils.load_source_path_class(
            artifact.materializer
        )(artifact)
        # The materializer now returns a resolved input
        return materializer.handle_input(data_type=data_type)

    def resolve_output_artifact(
        self, param_name: str, artifact: BaseArtifact, data: Any
    ) -> None:
        """Resolves an output artifact, i.e., writing it to the Artifact Store.
        Calls `handle_return(return_values)` of the selected materializer.

        Args:
            param_name: Name of output param.
            artifact: A TFX artifact type.
            data: The object to be passed to `handle_return()`.
        """
        # Skip materialization for BaseArtifact and subclasses.
        if issubclass(type(data), BaseArtifact):
            return

        materializer_class = self.resolve_materializer_with_registry(
            param_name, artifact
        )
        artifact.materializer = source_utils.resolve_class(materializer_class)
        artifact.datatype = source_utils.resolve_class(type(data))
        materializer_class(artifact).handle_return(data)

    def check_output_types_match(
        self, output_value: Any, specified_type: Type[Any]
    ) -> None:
        """Raise error if types don't match.

        Args:
            output_value: Value of output.
            specified_type: What the type of output should be as defined in the
            signature.

        Raises:
            ValueError if types do not match.
        """
        # TODO [ENG-160]: Include this check when we figure out the logic of
        #  slightly different subclasses.
        if not do_types_match(type(output_value), specified_type):
            raise ValueError(
                f"Output `{output_value}` of type {type(output_value)} does "
                f"not match specified return type {specified_type} in step "
                f"{getattr(self, PARAM_STEP_NAME)}"
            )

    def Do(
        self,
        input_dict: Dict[str, List[BaseArtifact]],
        output_dict: Dict[str, List[BaseArtifact]],
        exec_properties: Dict[str, Any],
    ) -> None:
        """Main block for the execution of the step

        Args:
            input_dict: dictionary containing the input artifacts
            output_dict: dictionary containing the output artifacts
            exec_properties: dictionary containing the execution parameters
        """
        step_name = getattr(self, PARAM_STEP_NAME)

        # remove all ZenML internal execution properties
        exec_properties = {
            k: json.loads(v)
            for k, v in exec_properties.items()
            if not k.startswith(INTERNAL_EXECUTION_PARAMETER_PREFIX)
        }

        # Building the args for the entrypoint function
        function_params = {}

        # First, we parse the inputs, i.e., params and input artifacts.
        spec = inspect.getfullargspec(inspect.unwrap(self._FUNCTION))
        args = spec.args

        if args and args[0] == "self":
            args.pop(0)

        for arg in args:
            arg_type = spec.annotations.get(arg, None)
            arg_type = resolve_type_annotation(arg_type)

            if issubclass(arg_type, BaseStepConfig):
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
                    output_materializers=self.materializers or {},
                    output_artifacts=output_artifacts,
                )
                function_params[arg] = context
            else:
                # At this point, it has to be an artifact, so we resolve
                function_params[arg] = self.resolve_input_artifact(
                    input_dict[arg][0], arg_type
                )

        if self._context is None:
            raise RuntimeError(
                "No TFX context is set for the currently running pipeline. "
                "Cannot retrieve pipeline runtime information."
            )
        # Wrap the execution of the step function in a step environment
        # that the step function code can access to retrieve information about
        # the pipeline runtime, such as the current step name and the current
        # pipeline run ID
        with StepEnvironment(
            pipeline_name=self._context.pipeline_info.id,
            pipeline_run_id=self._context.pipeline_run_id,
            step_name=getattr(self, PARAM_STEP_NAME),
        ):
            return_values = self._FUNCTION(**function_params)

        spec = inspect.getfullargspec(inspect.unwrap(self._FUNCTION))
        return_type: Type[Any] = spec.annotations.get("return", None)
        if return_type is not None:
            if isinstance(return_type, Output):
                output_annotations = list(return_type.items())
            else:
                output_annotations = [(SINGLE_RETURN_OUT_NAME, return_type)]

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
                return_values, output_annotations
            ):
                if not isinstance(return_value, output_type):
                    raise StepInterfaceError(
                        f"Wrong type for output '{output_name}' of step "
                        f"'{step_name}' (expected type: {output_type}, "
                        f"actual type: {type(return_value)})."
                    )

                self.resolve_output_artifact(
                    output_name, output_dict[output_name][0], return_value
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
