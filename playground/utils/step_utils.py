"""
The collection of utility functions/classes are inspired by their original
implementation of the Tensorflow Extended team, which can be found here:

https://github.com/tensorflow/tfx/blob/master/tfx/dsl/component/experimental/decorators.py

This version is heavily adjusted to work with the Pipeline-Step paradigm which
is proposed by ZenML.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
from typing import Any, Callable, Dict, List, Text

from tfx import types as tfx_types
from tfx.dsl.component.experimental.decorators import _SimpleComponent
from tfx.dsl.components.base.base_executor import BaseExecutor
from tfx.dsl.components.base.executor_spec import ExecutorClassSpec
from tfx.types import component_spec


class _FunctionExecutor(BaseExecutor):
    _FUNCTION = staticmethod(lambda: None)

    def Do(self,
           input_dict: Dict[Text, List[tfx_types.Artifact]],
           output_dict: Dict[Text, List[tfx_types.Artifact]],
           exec_properties: Dict[Text, Any]) -> None:
        function_args = {}
        for name, artifact in input_dict.items():
            if len(artifact) == 1:
                function_args[name] = artifact[0]
            else:
                raise ValueError(('Expected input %r to %s to be a singleton '
                                  'ValueArtifact channel (got %s '
                                  'instead).') % (name, self, artifact))
        for name, artifact in output_dict.items():
            if len(artifact) == 1:
                function_args[name] = artifact[0]
            else:
                raise ValueError(('Expected output %r to %s to be a singleton '
                                  'ValueArtifact channel (got %s '
                                  'instead).') % (name, self, artifact))

        for name, parameter in exec_properties.items():
            function_args[name] = parameter

        self._FUNCTION(**function_args)


def convert_to_component(step) -> Callable[..., Any]:
    spec_inputs, spec_outputs, spec_params = {}, {}, {}
    for key, artifact_type in step.INPUT_SPEC.items():
        spec_inputs[key] = component_spec.ChannelParameter(type=artifact_type)
    for key, artifact_type in step.OUTPUT_SPEC.items():
        spec_outputs[key] = component_spec.ChannelParameter(type=artifact_type)
    for key, prim_type in step.PARAM_SPEC.items():
        spec_params[key] = component_spec.ExecutionParameter(type=prim_type)

    component_spec_class = type('%s_Spec' % step.__class__.__name__,
                                (tfx_types.ComponentSpec,),
                                {'INPUTS': spec_inputs,
                                 'OUTPUTS': spec_outputs,
                                 'PARAMETERS': spec_params})

    executor_class = type('%s_Executor' % step.__class__.__name__,
                          (_FunctionExecutor,),
                          {'_FUNCTION': staticmethod(step.process),
                           '__module__': step.__module__})

    module = sys.modules[step.__module__]
    setattr(module, '%s_Executor' % step.__class__.__name__, executor_class)

    executor_spec_instance = ExecutorClassSpec(executor_class=executor_class)

    return type(step.__class__.__name__,
                (_SimpleComponent,),
                {'SPEC_CLASS': component_spec_class,
                 'EXECUTOR_SPEC': executor_spec_instance,
                 '__module__': step.__module__})
