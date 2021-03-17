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
import inspect
from typing import Dict

from zenml.backends import BaseBackend
from zenml.enums import StepTypes
from zenml.standards.standard_keys import StepKeys
from zenml.utils.print_utils import to_pretty_string, PrintStyles
from zenml.utils.source_utils import resolve_class, \
    load_source_path_class, is_valid_source


class BaseStep:
    """
    Base class for all ZenML steps.

    These are 'windows' into the base components for simpler overrides.
    """
    STEP_TYPE = StepTypes.base.name

    def __init__(self, backend: BaseBackend = None, **kwargs):
        """
        Base data step constructor.

        Args:
            **kwargs: Keyword arguments used in the construction of a step
            from a configuration file.
        """
        self._kwargs = kwargs
        self._immutable = False
        self.backend = backend
        self._source = resolve_class(self.__class__)

    def __str__(self):
        return to_pretty_string(self.to_config())

    def __repr__(self):
        return to_pretty_string(self.to_config(), style=PrintStyles.PPRINT)

    @staticmethod
    def from_config(config_block: Dict):
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
        if StepKeys.SOURCE in config_block:
            source = config_block[StepKeys.SOURCE]
            class_ = load_source_path_class(source)
            args = config_block[StepKeys.ARGS]
            resolved_args = {}

            # resolve backend
            backend = None
            if StepKeys.BACKEND in config_block:
                backend_config = config_block[StepKeys.BACKEND]
                backend = BaseBackend.from_config(backend_config)

            # resolve args for special cases
            for k, v in args.items():
                if isinstance(v, str) and is_valid_source(v):
                    resolved_args[k] = load_source_path_class(v)
                else:
                    resolved_args[k] = v

            obj = class_(**resolved_args)

            # If we load from config, its immutable
            obj._immutable = True
            obj.backend = backend
            return obj
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
        kwargs = {}
        for key, kwarg in self._kwargs.items():
            if inspect.isclass(kwarg):
                kwargs[key] = resolve_class(kwarg)
            else:
                kwargs[key] = kwarg

        config = {
            StepKeys.SOURCE: self._source,
            StepKeys.ARGS: kwargs,  # everything to be recorded
        }

        # only add backend if its set
        if self.backend is not None:
            config.update({StepKeys.BACKEND: self.backend.to_config()})

        return config

    def with_backend(self, backend: BaseBackend):
        """Builder for step backends."""
        self.backend = backend
        return self
