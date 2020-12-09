#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the 'License');
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an 'AS IS' BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

from zenml.core.pipelines.config.config_utils import ConfigKeys

DATA_SPLIT_NAME = 'examples'
DATA_COL = '_data_'
SCHEMA = 'schema'

# Possible types and sources (with the corresponding args)

TYPE_TEXT = 'text'
TYPE_TABULAR = 'tabular'
TYPE_IMAGE = 'image'
TYPE_IMAGE_SEG = 'image_segmentation'

SOURCE_BQ = 'bq'
SOURCE_GCS = 'gcs'
SOURCE_MVG_BQ = 'mvg_bq'
SOURCE_LOCAL_IMAGE = 'local_image'
SOURCE_LOCAL_CSV = 'local_csv'
SOURCE_GCS_IMAGE = 'gcs_image'
SOURCE_GCS_CSV = 'gcs_csv'

# local storage data source args
BINARY_DATA = 'binary_data'
METADATA = 'metadata'
FILE_EXT = 'file_ext'
FILE_NAME = 'file_name'
BASE_PATH = 'base_path'
FILE_PATH = 'file_path'

# image data constants
IMAGE = 'image'
LABEL = 'label'
MASK = 'mask'


class BQArgs(ConfigKeys):
    PROJECT = 'project'
    DATASET = 'dataset'
    TABLE = 'table'
    LIMIT_ = 'limit'
    SERVICE_ACCOUNT_ = 'service_account'


class LocalImageArgs(ConfigKeys):
    BASE_PATH = 'base_path'


class LocalCSVArgs(ConfigKeys):
    BASE_PATH = 'base_path'


class MVGBQArgs(ConfigKeys):
    PROJECT = 'project'
    DATASET = 'dataset'
    TABLE = 'table'
    ASSET_IDS_ = 'asset_ids'
    LIMIT_ = 'limit'
    PGN_DATABASE_ = 'pgn_database'
    ERROR_DATABASE_ = 'error_database'


class GCSArgs(ConfigKeys):
    SERVICE_ACCOUNT = 'service_account'
    PATH = 'path'


class GCSImageArgs(ConfigKeys):
    BASE_PATH = 'base_path'
    SERVICE_ACCOUNT = 'service_account'


# Component keys
class SpecParamKeys(ConfigKeys):
    SOURCE = 'source'
    SOURCE_ARGS = 'args'


class DatasourceKeys(ConfigKeys):
    SOURCE = 'source'
    TYPE = 'type'
    ARGS = 'args'


class DestinationKeys(ConfigKeys):
    PROJECT = 'project'
    DATASET = 'dataset'
    TABLE = 'table'
