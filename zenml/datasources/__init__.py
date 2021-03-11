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

from zenml.datasources.base_datasource import BaseDatasource
from zenml.datasources.bq_datasource import BigQueryDatasource
from zenml.datasources.csv_datasource import CSVDatasource
from zenml.datasources.image_datasource import ImageDatasource
from zenml.datasources.json_datasource import JSONDatasource
from zenml.datasources.numpy_datasource import NumpyDatasource
from zenml.datasources.pandas_datasource import PandasDatasource

from zenml.utils.requirement_utils import check_integration, \
    POSTGRES_INTEGRATION
from zenml.logger import get_logger

logger = get_logger(__name__)

try:
    check_integration(POSTGRES_INTEGRATION)
    from zenml.datasources.postgres_datasource import PostgresDatasource
except ModuleNotFoundError as e:
    logger.debug(f"There were failed imports due to missing integrations. "
                 f"PostgresDatasource was not imported. "
                 f"More information:")
    logger.debug(e)

