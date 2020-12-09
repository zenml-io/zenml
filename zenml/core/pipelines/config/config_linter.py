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

import logging

from zenml.core.components.session_transform.sequence_transform import \
    SequenceTransform
from zenml.core.components.split_gen.component import SplitGen
from zenml.core.components.trainer.component import Trainer
from zenml.core.components.transform.component import Transform
from zenml.core.pipelines.config.standard_config import GlobalKeys


class ConfigLinter:

    def __init__(self, version: int = 1):
        """
        Args:
            version (int):
        """
        self.version = version

    @staticmethod
    def lint(config):
        """
        Args:
            config:
        """
        GlobalKeys.key_check(config)

        parsers = [SplitGen.lint,
                   Transform.lint,
                   Trainer.lint]

        if GlobalKeys.TIMESERIES_ in config:
            parsers.append(SequenceTransform.config_parser)

        for p_func in parsers:
            try:
                _ = p_func(config)
            except AssertionError as e:
                logging.error('Problem while reading the config '
                              'file: {}'.format(e))
                raise e
            except Exception as e:
                logging.error(e)
                raise AssertionError(
                    'We found an error in parsing your config YAML, but could '
                    'not infer what it is precisely. Please ensure your YAML '
                    'is formatted properly, and you are following the format '
                    'set in our docs: https://docs.maiot.io')
