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

from zenml.components.bulk_inferrer.constants import MODEL, EXAMPLES, \
    MODEL_BLESSING, PREDICTIONS
from zenml.components.bulk_inferrer.executor import BulkInferrerExecutor
from zenml.standards.standard_keys import StepKeys


class BulkInferrerSpec(ComponentSpec):
    PARAMETERS = {
        StepKeys.SOURCE: ExecutionParameter(type=Text),
        StepKeys.ARGS: ExecutionParameter(type=Dict[Text, Any]),
    }
    INPUTS = {
        MODEL: ChannelParameter(type=standard_artifacts.Model, optional=True),
        EXAMPLES: ChannelParameter(type=standard_artifacts.Examples),
        MODEL_BLESSING: ChannelParameter(type=standard_artifacts.ModelBlessing,
                                         optional=True)

    }
    OUTPUTS = {
        PREDICTIONS: ChannelParameter(type=standard_artifacts.Examples)
    }


class BulkInferrer(BaseComponent):
    SPEC_CLASS = BulkInferrerSpec
    EXECUTOR_SPEC = ExecutorClassSpec(BulkInferrerExecutor)

    def __init__(self,
                 source: Text,
                 source_args: Dict[Text, Any],
                 model: Optional[ChannelParameter] = None,
                 model_blessing: Optional[ChannelParameter] = None,
                 instance_name: Optional[Text] = None,
                 examples: Optional[ChannelParameter] = None,
                 predictions: Optional[ChannelParameter] = None):
        """
        Interface for all DataGen components, the main component responsible
        for reading data and converting to TFRecords. This is how we handle
        versioning data for now.
        Args:
            source:
            source_args:
            model:
            model_blessing:
            instance_name:
            examples:
            predictions:
        """
        examples = examples or Channel(type=standard_artifacts.Examples)
        predictions = predictions or Channel(type=standard_artifacts.Examples)

        # Initiate the spec and create instance
        spec = self.SPEC_CLASS(source=source,
                               args=source_args,
                               model=model,
                               model_blessing=model_blessing,
                               examples=examples,
                               predictions=predictions)

        super(BulkInferrer, self).__init__(spec=spec,
                                           instance_name=instance_name)
