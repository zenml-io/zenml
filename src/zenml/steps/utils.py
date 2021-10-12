#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

"""
The collection of utility functions/classes are inspired by their original
implementation of the Tensorflow Extended team, which can be found here:

https://github.com/tensorflow/tfx/blob/master/tfx/dsl/component/experimental/decorators.py

This version is heavily adjusted to work with the Pipeline-Step paradigm which
is proposed by ZenML.
"""

from __future__ import absolute_import, division, print_function

import inspect
import json
import sys
from typing import Any, Callable, Dict, List, Optional, Type

import pydantic
from pydantic import create_model
from tfx import types as tfx_types
from tfx.dsl.component.experimental.decorators import _SimpleComponent
from tfx.dsl.components.base.base_executor import BaseExecutor
from tfx.dsl.components.base.executor_spec import ExecutorClassSpec
from tfx.types import component_spec
from tfx.types.channel import Channel
from tfx.utils import json_utils

from zenml.annotations import Input, Output
from zenml.artifacts.base_artifact import BaseArtifact
from zenml.exceptions import StepInterfaceError

STEP_INNER_FUNC_NAME: str = "process"


class _PropertyDictWrapper(json_utils.Jsonable):
    """Helper class to wrap inputs/outputs from TFX nodes.
    Currently, this class is read-only (setting properties is not implemented).
    Internal class: no backwards compatibility guarantees.
    Code Credit: https://github.com/tensorflow/tfx/blob/51946061ae3be656f1718a3d62cd47228b89b8f4/tfx/types/node_common.py
    """

    def __init__(
        self,
        data: Dict[str, Channel],
        compat_aliases: Optional[Dict[str, str]] = None,
    ):
        """Initializes the wrapper object.

        Args:
            data: The data to be wrapped.
            compat_aliases: Compatability aliases to support deprecated keys.
        """
        self._data = data
        self._compat_aliases = compat_aliases or {}

    def __iter__(self):
        """Returns a generator that yields keys of the wrapped dictionary."""
        yield from self._data

    def __getitem__(self, key):
        """Returns the dictionary value for the specified key."""
        if key in self._compat_aliases:
            key = self._compat_aliases[key]
        return self._data[key]

    def __getattr__(self, key):
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

    def keys(self):
        """Returns the keys of the wrapped dictionary."""
        return self._data.keys()

    def values(self):
        """Returns the values of the wrapped dictionary."""
        return self._data.values()

    def items(self):
        """Returns the items of the wrapped dictionary."""
        return self._data.items()


class _ZenMLSimpleComponent(_SimpleComponent):
    """Simple ZenML TFX component with outputs overridden."""

    @property
    def outputs(self) -> _PropertyDictWrapper:
        """Returns the wrapped spec outputs."""
        return _PropertyDictWrapper(self.spec.outputs)


class _FunctionExecutor(BaseExecutor):
    """Base TFX Executor class which is compatible with ZenML steps"""

    _FUNCTION = staticmethod(lambda: None)

    def Do(
        self,
        input_dict: Dict[str, List[tfx_types.Artifact]],
        output_dict: Dict[str, List[tfx_types.Artifact]],
        exec_properties: Dict[str, Any],
    ):
        """Main block for the execution of the step

        Args:
            input_dict: dictionary containing the input artifacts
            output_dict: dictionary containing the output artifacts
            exec_properties: dictionary containing the execution parameters
        """

        # Building the args for the process function
        function_args = {}

        # Resolving the input artifacts
        for name, artifact in input_dict.items():
            if len(artifact) == 1:
                function_args[name] = artifact[0]
            else:
                raise ValueError(
                    (
                        "Expected input %r to %s to be a singleton "
                        "ValueArtifact channel (got %s instead)."
                    )
                    % (name, self, artifact)
                )

        # Resolving the output artifacts and the return annotations
        return_artifact = output_dict.pop("return_output", None)
        for name, artifact in output_dict.items():
            if len(artifact) == 1:
                function_args[name] = artifact[0]
            else:
                raise ValueError(
                    (
                        "Expected output %r to %s to be a singleton "
                        "ValueArtifact channel (got %s instead)."
                    )
                    % (name, self, artifact)
                )

        # Resolving the primitive input and output annotations
        spec = inspect.getfullargspec(self._FUNCTION)
        args = spec.args
        inputs_to_take_care_of = []
        param_spec = {}
        for arg in args:
            arg_type = spec.annotations.get(arg, None)
            if isinstance(arg_type, Input):
                if not issubclass(arg_type.type, BaseArtifact):
                    inputs_to_take_care_of.append(arg)
            elif isinstance(arg_type, Output):
                pass
            else:
                param_spec.update({arg: arg_type})

        # Resolving the execution parameters
        new_exec = {k: json.loads(v) for k, v in exec_properties.items()}
        pydantic_c: Type[pydantic.BaseModel] = create_model(
            "params", **{k: (v, ...) for k, v in param_spec.items()}
        )
        function_args.update(pydantic_c.parse_obj(new_exec).dict())

        returns = self._FUNCTION(**function_args)

        # Managing the returns of the process function
        if return_artifact is not None:
            artifact = return_artifact[0]
            if returns is not None:
                artifact.materializers.json.write_file(returns)
            else:
                raise StepInterfaceError()

        if returns is not None and return_artifact is None:
            raise StepInterfaceError()


def generate_component(step) -> Callable[..., Any]:
    """Utility function which converts a ZenML step into a TFX Component

    Args:
        step: a ZenML step instance

    Returns:
        component: the class of the corresponding TFX component
    """

    # Managing the parameters for component spec creation
    spec_inputs, spec_outputs, spec_params = {}, {}, {}
    for key, artifact_type in step.INPUT_SPEC.items():
        spec_inputs[key] = component_spec.ChannelParameter(type=artifact_type)
    for key, artifact_type in step.OUTPUT_SPEC.items():
        spec_outputs[key] = component_spec.ChannelParameter(type=artifact_type)
    for key, prim_type in step.PARAM_SPEC.items():
        spec_params[key] = component_spec.ExecutionParameter(type=str)

    component_spec_class = type(
        "%s_Spec" % step.__class__.__name__,
        (tfx_types.ComponentSpec,),
        {
            "INPUTS": spec_inputs,
            "OUTPUTS": spec_outputs,
            "PARAMETERS": spec_params,
        },
    )

    # Defining a executor class bu utilizing the process function
    executor_class = type(
        "%s_Executor" % step.__class__.__name__,
        (_FunctionExecutor,),
        {
            "_FUNCTION": staticmethod(getattr(step, STEP_INNER_FUNC_NAME)),
            "__module__": step.__module__,
        },
    )

    module = sys.modules[step.__module__]
    setattr(module, "%s_Executor" % step.__class__.__name__, executor_class)
    executor_spec_instance = ExecutorClassSpec(executor_class=executor_class)

    # Defining the component with the corresponding executor and spec
    return type(
        step.__class__.__name__,
        (_ZenMLSimpleComponent,),
        {
            "SPEC_CLASS": component_spec_class,
            "EXECUTOR_SPEC": executor_spec_instance,
            "__module__": step.__module__,
        },
    )
