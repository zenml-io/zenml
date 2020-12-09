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
"""Definition of a the base Backend"""

from typing import Dict


class BaseBackend:
    """Base class for all ZenML backends.

    Every ZenML pipeline runs in backends
    """
    BACKEND_TYPE = None
    BACKEND_KEY = None

    def __init__(self, **kwargs):
        pass

    def to_config(self):
        """Converts Backend to ZenML config block."""
        return {
            self.BACKEND_KEY: {
                'type': self.BACKEND_TYPE,
                'args': self.__dict__  # everything in init
            }
        }

    @classmethod
    def from_config(cls, config: Dict):
        """
        Convert from ZenML config dict to ZenML Backend object.

        Args:
            config: a ZenML config in dict-form (probably loaded from YAML).
        """
        from zenml.core.backends.backend_factory import backend_factory
        backend_class = backend_factory.get_single_backend(config['type'])
        backend_args = config['args']
        obj = backend_class(**backend_args)
        return obj
