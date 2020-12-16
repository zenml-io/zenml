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

class ConfigKeys:
    @classmethod
    def get_keys(cls):
        keys = {key: value for key, value in cls.__dict__.items() if
                not isinstance(value, classmethod) and
                not isinstance(value, staticmethod) and
                not callable(value) and
                not key.startswith('__')}

        required = {k: v for k, v in keys.items() if not k.endswith('_')}
        optional = {k: v for k, v in keys.items() if k.endswith('_')}

        return required, optional

    @classmethod
    def key_check(cls, _input):
        # Check whether the given config is a dict
        """
        Args:
            _input:
        """
        assert isinstance(_input, dict), 'Please specify a dict for {}' \
            .format(cls.__name__)

        # Required and optional keys for the config dict
        required, optional = cls.get_keys()

        # Check for missing keys
        missing_keys = [k for k in required.values() if
                        k not in _input.keys()]
        assert len(missing_keys) == 0, \
            'Missing key(s) {} in {}'.format(missing_keys,
                                             cls.__name__)

        # Check for unknown keys
        unknown_keys = [k for k in _input.keys() if
                        k not in required.values() and
                        k not in optional.values()]
        assert len(unknown_keys) == 0, \
            'Unknown key(s) {} in {}. Required keys : {} ' \
            'Optional Keys: {}'.format(unknown_keys,
                                       cls.__name__,
                                       list(required.values()),
                                       list(optional.values()))


class MethodDescriptions:
    MODES = {}

    @classmethod
    def check_name_and_params(cls, method_name, method_params):
        """
        Args:
            method_name:
            method_params:
        """
        assert method_name in cls.MODES.keys(), \
            'Choose one of the defined methods: {}'.format(cls.MODES.keys())

        assert all(
            p in method_params.keys() for p in cls.MODES[method_name][1]), \
            'All the required params {} of the {} needs to be defined' \
                .format(cls.MODES[method_name][1], method_name)

    @classmethod
    def get_method(cls, method_name):
        """
        Args:
            method_name:
        """
        return cls.MODES[method_name][0]
