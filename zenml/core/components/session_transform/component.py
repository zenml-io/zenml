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

import abc
from typing import Optional, Text

from tfx.components.base import base_component
from tfx.types import channel_utils, artifact_utils, standard_artifacts


class SessionTransform(base_component.BaseComponent):
    """Custom SessionTransform component

    This component is created as a baseline to apply transformations on a
    session level .

    In order to use the baseline for creating a component, the user needs to
    follow three steps:

        1 - Create a new executor class inheriting from the SessionExecutor
            and overwrite the method called 'get_combiner' which needs to return
            the CombineFn which processes sessions

        2 - Create a new component class inheriting from the SessionComponent
            and set the EXECUTOR_SPEC using the executor mentioned in step 1

        3 - Implement the config parser for the specific use-case
    """

    SPEC_CLASS = None

    def __init__(self,
                 examples=None,
                 schema=None,
                 config=None,
                 instance_name: Optional[Text] = None):
        """
        Args:
            examples:
            schema:
            config:
            instance_name:
        """
        self.exp_dict = config
        self.schema = schema
        config_dict = self.config_parser(config)

        output_artifact = standard_artifacts.Examples()
        output_artifact.split_names = artifact_utils.encode_split_names(
            ['train', 'eval'])

        output = channel_utils.as_channel([output_artifact])

        spec = self.SPEC_CLASS(
            input=examples,
            schema=schema,
            output=output,
            **config_dict
        )
        super(SessionTransform, self).__init__(spec=spec,
                                               instance_name=instance_name)

    @abc.abstractmethod
    def config_parser(self):
        """Abstract method which needs to be implemented to parse the relevant
        configuration out of the experiment config file
        """
        return {}
