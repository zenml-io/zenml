#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
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

from typing import Dict, Any, Text

from tfx import types
from tfx.components.base.base_component import BaseComponent
from tfx.dsl.components.base import executor_spec
from tfx.types import standard_artifacts
from tfx.types.component_spec import ComponentSpec, ExecutionParameter, \
    ChannelParameter

from zenml.core.components.split_gen import executor


class SplitGenComponentSpec(ComponentSpec):
    """SplitGen ExampleGen component spec."""
    PARAMETERS = {
        'source': ExecutionParameter(type=Text),
        'args': ExecutionParameter(type=Dict[Text, Any]),
    }
    INPUTS = {
        'input_examples': ChannelParameter(type=standard_artifacts.Examples),
        'statistics': ChannelParameter(
            type=standard_artifacts.ExampleStatistics),
        'schema': ChannelParameter(type=standard_artifacts.Schema)
    }
    OUTPUTS = {
        'examples': ChannelParameter(type=standard_artifacts.Examples)
    }


class SplitGen(BaseComponent):
    SPEC_CLASS = SplitGenComponentSpec
    EXECUTOR_SPEC = executor_spec.ExecutorClassSpec(executor.Executor)

    def __init__(self,
                 source: Text,
                 source_args: Dict[Text, Any],
                 input_examples: types.Channel,  # input
                 examples: types.Channel = None,  # output
                 statistics: types.Channel = None,
                 schema: types.Channel = None):

        examples = examples or types.Channel(
            type=standard_artifacts.Examples)

        spec = SplitGenComponentSpec(
            source=source,
            args=source_args,
            input_examples=input_examples,
            statistics=statistics,
            schema=schema,
            examples=examples)

        super(SplitGen, self).__init__(spec=spec)
