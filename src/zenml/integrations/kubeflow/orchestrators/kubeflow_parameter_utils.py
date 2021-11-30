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

Utilities for processing runtime parameters during compilation."""
import threading

from tfx.orchestration import data_types

_thread_local = threading.local()


class ParameterContext:
    """A context that helps collecting runtime parameters during compilation.
    This context object should be only used by PipelineBuilder during compilation,
    to collect all the RuntimeParameter encountered. For example:
    ```
    tasks = []
    with ParameterContext() as pc:
      for component in components:
        tasks.append(step_builder.StepBuilder(...).build())
        ...
    ```
    Then later on, `pc.parameters` stores the list of all RuntimeParameters
    occurred when building each steps, which can be used to populate
    pipeline_spec.runtime_parameters field.
    """

    def __init__(self):
        """Initializes the ParameterContext."""
        self.parameters = []

    def __enter__(self) -> "ParameterContext":
        """Enters the ParameterContext."""
        if hasattr(_thread_local, "parameter_list"):
            raise RuntimeError("ParameterContext cannot be nested.")
        _thread_local.parameter_list = []
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exits the ParameterContext."""
        self.parameters.extend(_thread_local.parameter_list)
        _thread_local.__delattr__("parameter_list")


def attach_parameter(parameter: data_types.RuntimeParameter):
    """Attaches a runtime parameter to the current context."""
    if not hasattr(_thread_local, "parameter_list"):
        raise RuntimeError(
            "attach_parameter() must run under ParameterContext."
        )

    _thread_local.parameter_list.append(parameter)
