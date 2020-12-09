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
#
# # Datasources
# from zenml.core.datasources.base_datasource import BaseDatasource
# from zenml.core.datasources.bq_datasource import BigQueryDatasource
# from zenml.core.datasources.csv_datasource import CSVDatasource
# from zenml.core.datasources.image_datasource import ImageDatasource
#
# # Pipelines
# from zenml.core.pipelines.base_pipeline import BasePipeline
# from zenml.core.pipelines.data_pipeline import DataPipeline
# from zenml.core.pipelines.infer_pipeline import BatchInferencePipeline
# from zenml.core.pipelines.training_pipeline import TrainingPipeline
#
# # Steps
# from zenml.core.steps.trainer import TrainerStep
# from zenml.core.steps.split import SplitStep
# from zenml.core.steps.deployer import DeployerStep
# from zenml.core.steps.evaluator import EvaluatorStep
# from zenml.core.steps.preprocesser import PreprocesserStep
# from zenml.core.steps.data.base_data_step import BaseDataStep
# from zenml.core.steps.timeseries import TimeseriesStep
# from zenml.core.steps.base_step import BaseStep
#
# # Backends
# from zenml.core import backends

import os
# set tensorflow logging level
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'