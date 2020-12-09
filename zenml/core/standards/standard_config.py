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

from zenml.core.pipelines.config.config_utils import ConfigKeys


class GlobalKeys(ConfigKeys):
    VERSION = 'version'
    SPECS = 'specs'
    STEPS = 'steps'


class EnvironmentKeys(ConfigKeys):
    EXPERIMENT_NAME = 'experiment_name'
    ARTIFACT_STORE = 'artifact_store'
    METADATA_STORE = 'metadata_store'
    ENABLE_CACHE = 'enable_cache'
    BACKENDS = 'backends'


class BackendKeys(ConfigKeys):
    TYPE = 'type'
    ARGS = 'args'


class TrainingSteps(ConfigKeys):
    DATA = 'data'
    SPLIT = 'split'
    SEQUENCING = 'sequencing'
    PREPROCESSING = 'preprocessing'
    TRAINING = 'training'
    EVALUATION = 'evaluation'
    DEPLOYMENT = 'deployment'


class DataSteps(ConfigKeys):
    DATA = 'data'


class InferSteps(ConfigKeys):
    DATA = 'data'
    INFER = 'infer'


# HELPER KEYS

class MethodKeys(ConfigKeys):
    METHOD = 'method'
    PARAMETERS = 'parameters'
