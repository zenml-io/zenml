#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
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

from typing import Text, Dict, Any, Optional

from tfx.dsl.components.base.base_component import BaseComponent
from tfx.dsl.components.base.executor_spec import ExecutorClassSpec
from tfx.types import standard_artifacts, Channel
from tfx.types.component_spec import ComponentSpec, ExecutionParameter, \
    ChannelParameter

from zenml.core.components.tokenizer.executor import TokenizerExecutor
from zenml.core.standards.standard_keys import StepKeys

VOCAB = "vocabulary"
MERGES = "merges"
TOKENIZER = "tokenizer"
TEXT_CACHE = "text_cache"
EXAMPLES = "examples"
OUTPUT_EXAMPLES = "output_examples"


class TokenizerSpec(ComponentSpec):
    PARAMETERS = {
        StepKeys.SOURCE: ExecutionParameter(type=Text),
        StepKeys.ARGS: ExecutionParameter(type=Dict[Text, Any]),
    }
    INPUTS = {
        EXAMPLES: ChannelParameter(type=standard_artifacts.Examples),
    }

    OUTPUTS = {
        TOKENIZER: ChannelParameter(type=standard_artifacts.Model),
        OUTPUT_EXAMPLES: ChannelParameter(type=standard_artifacts.Examples),
        TEXT_CACHE: ChannelParameter(type=standard_artifacts.Examples)
    }


class Tokenizer(BaseComponent):
    SPEC_CLASS = TokenizerSpec
    EXECUTOR_SPEC = ExecutorClassSpec(TokenizerExecutor)

    def __init__(self,
                 source: Text,
                 source_args: Dict[Text, Any],
                 examples: Optional[ChannelParameter] = None,
                 tokenizer: Optional[ChannelParameter] = None,
                 output_examples: Optional[ChannelParameter] = None,
                 text_cache: Optional[ChannelParameter] = None,
                 instance_name: Optional[Text] = None
                 ):
        """
        Interface for all DataGen components, the main component responsible
        for reading data and converting to TFRecords. This is how we handle
        versioning data for now.

        Args:
            source:
            source_args:
            tokenizer:
            instance_name:
            examples:
        """
        examples = examples or Channel(type=standard_artifacts.Examples)
        tokenizer = tokenizer or Channel(type=standard_artifacts.Model)
        output_examples = output_examples or Channel(
            type=standard_artifacts.Examples)
        text_cache = text_cache or Channel(type=standard_artifacts.Examples)

        # Initiate the spec and create instance
        spec = self.SPEC_CLASS(source=source,
                               args=source_args,
                               tokenizer=tokenizer,
                               examples=examples,
                               output_examples=output_examples,
                               text_cache=text_cache)

        super(Tokenizer, self).__init__(spec=spec,
                                        instance_name=instance_name)
