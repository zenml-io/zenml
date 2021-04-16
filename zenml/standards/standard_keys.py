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


class GlobalKeys(ConfigKeys):
    VERSION = 'version'
    ARTIFACT_STORE = 'artifact_store'
    METADATA_STORE = 'metadata'
    BACKEND = 'backend'
    PIPELINE = 'pipeline'


class PipelineKeys(ConfigKeys):
    ARGS = 'args'
    SOURCE = 'source'
    STEPS = 'steps'
    DATASOURCE = 'datasource'
    DATASOURCE_COMMIT_ID = 'datasource_commit_id'
    ENABLE_CACHE = 'enable_cache'


class PipelineDetailKeys(ConfigKeys):
    NAME = 'name'
    TYPE = 'type'
    ENABLE_CACHE = 'enable_cache'


class DatasourceKeys(ConfigKeys):
    ID = 'id'
    NAME = 'name'
    SOURCE = 'source'
    ARGS = 'args'


class BackendKeys(ConfigKeys):
    TYPE = 'type'
    ARGS = 'args'
    SOURCE = 'source'


class MLMetadataKeys(ConfigKeys):
    TYPE = 'type'
    ARGS = 'args'


class StepKeys(ConfigKeys):
    NAME = 'name'
    SOURCE = 'source'
    ARGS = 'args'
    BACKEND = 'backend'


class TrainingSteps(ConfigKeys):
    DATA = 'data'
    SPLIT = 'split'
    SEQUENCER = 'sequencer'
    PREPROCESSER = 'preprocesser'
    TRAINER = 'trainer'
    EVALUATOR = 'evaluator'
    DEPLOYER = 'deployer'


class NLPSteps(ConfigKeys):
    DATA = 'data'
    SPLIT = 'split'
    TRAINER = 'trainer'
    TOKENIZER = 'tokenizer'


class DataSteps(ConfigKeys):
    DATA = 'data'


class InferSteps(ConfigKeys):
    DATA = 'data'
    INFER = 'infer'


# HELPER KEYS

class MethodKeys(ConfigKeys):
    METHOD = 'method'
    PARAMETERS = 'parameters'


class DefaultKeys(ConfigKeys):
    STRING = 'string'
    INTEGER = 'integer'
    BOOLEAN = 'boolean'
    FLOAT = 'float'
