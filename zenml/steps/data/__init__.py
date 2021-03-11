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

from zenml.steps.data.base_data_step import BaseDataStep
from zenml.steps.data.bq_data_step import BQDataStep
from zenml.steps.data.csv_data_step import CSVDataStep
from zenml.steps.data.image_data_step import ImageDataStep
from zenml.logger import get_logger
from zenml.utils.requirement_utils import check_integration, \
    POSTGRES_INTEGRATION

logger = get_logger(__name__)

try:
    check_integration(POSTGRES_INTEGRATION)
    from zenml.steps.data.postgres_data_step import PostgresDataStep
except ModuleNotFoundError as e:
    logger.debug(f"There were failed imports due to missing integrations. "
                 f"PostgresDataStep was not imported. "
                 f"More information:")
    logger.debug(e)
