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


class StepKeys(ConfigKeys):
    FN = 'fn'
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

# class AIPlatformKeys(ConfigKeys):
#     SCALE_TIER = 'scale_tier'
#     RUNTIME_VERSION_ = 'runtime_version'
#     PYTHON_VERSION_ = 'python_version'
#     MAX_RUNNING_TIME_ = 'max_running_time'
#
#
# class OrchestratorKeys(ConfigKeys):
#     TYPE = 'type'
#     ARGS = 'args'
#
#
# class BigQueryKeys(ConfigKeys):
#     PROJECT_ = 'project'
#     DATASET = 'dataset'
#     TABLE_ = 'table'
#
#
# class KubeflowKeys(ConfigKeys):
#     IMAGE_ = ''
#
#
# class BeamKeys(ConfigKeys):
#     RUNNER = 'runner'
#     WORKER_MACHINE_TYPE_ = 'worker_machine_type'
#     NUM_WORKERS_ = 'num_workers'
#     MAX_NUM_WORKERS_ = 'max_num_workers'
#     DISK_SIZE_GB_ = 'disk_size_gb'
#     AUTOSCALING_ALGORITHM_ = 'autoscaling_algorithm'
#
#
# class GCPOrchestratorKeys(ConfigKeys):
#     SERVICE_ACCOUNT = 'service_account'
#     PROJECT_ = 'project'
#     ZONE_ = 'zone'
#     NAME_ = 'name'
#     IMAGE_NAME_ = 'image_name'
#     PREEMPTIBLE_ = 'preemptible'
#     MACHINE_TYPE_ = 'machine_type'
#
#
# class GCPProviderKeys(ConfigKeys):
#     ARTIFACT_STORE_ = 'artifact_store'
#
#
# class MetadataKeys(ConfigKeys):
#     TYPE = 'type'
#     HOST_ = 'host'
#     PORT_ = 'port'
#     DATABASE_ = 'database'
#     USERNAME_ = 'username'
#     PASSWORD_ = 'password'
#
