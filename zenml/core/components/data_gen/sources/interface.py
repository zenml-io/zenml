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

from zenml.core.components.data_gen.constants import DatasourceKeys


class SourceInterface:
    ARG_KEYS = None

    @classmethod
    def config_parser(cls, config):
        """
        Args:
            config:
        """
        DatasourceKeys.key_check(config)
        args = config[DatasourceKeys.ARGS]
        cls.ARG_KEYS.key_check(args)
        return config

    @abc.abstractmethod
    def beam_transform(self, *args, **kwargs):
        """
        Args:
            *args:
            **kwargs:
        """
        pass
