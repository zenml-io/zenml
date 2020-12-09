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
"""Base Step Interface definition"""

from typing import Dict, Type

from zenml.utils.source_utils import resolve_source_path, \
    load_source_path_class
from zenml.utils.zenml_analytics import track, CREATE_STEP


class BaseStep:
    """Base class for all ZenML steps.

    These are 'windows' into the base components for simpler overrides.
    """

    @staticmethod
    def from_config(config_block: Dict) -> Type:
        """
        Takes config block that represents a Step and converts it back into
        its Python equivalent. This functionality is similar for most steps,
        and expected config_block may look like

        {
            'source': this.module.StepClass@sha  # where sha is optional
            'args': {}  # to be passed to the constructor
        }

        Args:
            config_block: config block representing source and args of step.
        """
        # resolve source path
        if 'source' in config_block:
            source = config_block['source']
            class_ = load_source_path_class(source)
            args = config_block['args']
            return class_(**args)
        else:
            raise AssertionError("Cannot create config_block without source "
                                 "key.")

    def to_config(self) -> Dict:
        """
        Converts from step back to config. This functionality for most steps
        yields the following config block.

        {
            'source': this.file.path.BaseStep@sha  # where sha is optional
            'args': {}  # whatever is used in the constructor for BaseStep
        }
        """
        # resolve git
        source_path = resolve_source_path(
            self.__class__.__module__ + '.' + self.__class__.__name__
        )

        return {
            'source': source_path,
            'args': self.__dict__  # everything in init
        }
