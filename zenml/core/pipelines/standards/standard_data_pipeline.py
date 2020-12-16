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

from zenml.core.pipelines.config.standard_config import ConfigKeys


class DatalineKeys(ConfigKeys):
    EXPERIMENT_NAME = 'experiment_name'
    DATASOURCE = 'datasource'
    DESTINATION = 'destination'
    OUTPUT_BASE_DIR = 'output_base_dir'
    GCP_PROJECT = 'project_id'
    GCP_REGION = 'gcp_region'
    ENABLE_CACHE = 'enable_cache'
    ORCHESTRATION = 'orchestration'
    EXECUTION = 'execution'
    METADATA_ARGS = 'metadata_args'
    SCHEMA_ = 'schema'


class DestinationKeys(ConfigKeys):
    PROJECT = 'project'
    DATASET = 'dataset'
    TABLE = 'table'


class OrchestratorKeys(ConfigKeys):
    TYPE = 'type'
    ARGS = 'args'
