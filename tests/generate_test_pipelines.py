#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
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

import os
from pathlib import Path

import zenml
from zenml.datasources import CSVDatasource
from zenml.exceptions import AlreadyExistsException
from zenml.logger import get_logger
from zenml.pipelines import TrainingPipeline
from zenml.repo import GlobalConfig
from zenml.repo import Repository
from zenml.steps.preprocesser import StandardPreprocesser
from zenml.steps.split import CategoricalDomainSplit
from zenml.steps.trainer import TFFeedForwardTrainer
from zenml.utils import path_utils

logger = get_logger(__name__)

# reset pipeline root to redirect to tests so that it writes the yamls there
ZENML_ROOT = str(Path(zenml.__path__[0]).parent)
TEST_ROOT = os.path.join(ZENML_ROOT, "tests")

# Set analytics to false BEFORE init_repo
global_config = GlobalConfig.get_instance()
global_config.set_analytics_opt_in(False)
Repository.init_repo(TEST_ROOT, analytics_opt_in=False)

pipeline_root = os.path.join(TEST_ROOT, "pipelines")
csv_root = os.path.join(TEST_ROOT, "test_data")
image_root = os.path.join(csv_root, "images")

repo: Repository = Repository.get_instance()
if path_utils.is_dir(pipeline_root):
    path_utils.rm_dir(pipeline_root)
repo.zenml_config.set_pipelines_dir(pipeline_root)

try:
    for i in range(1, 6):
        training_pipeline = TrainingPipeline(name='csvtest{0}'.format(i))

        try:
            # Add a datasource. This will automatically track and version it.
            ds = CSVDatasource(name='my_csv_datasource',
                               path=os.path.join(csv_root, "my_dataframe.csv"))
        except AlreadyExistsException:
            ds = repo.get_datasource_by_name("my_csv_datasource")

        training_pipeline.add_datasource(ds)

        # Add a split
        training_pipeline.add_split(CategoricalDomainSplit(
            categorical_column="name",
            split_map={'train': ["arnold"],
                       'eval': ["lülük"],
                       'test': ["nicholas"]}))

        # Add a preprocessing unit
        training_pipeline.add_preprocesser(
            StandardPreprocesser(
                features=["name", "age"],
                labels=['gpa'],
                overwrite={'gpa': {
                    'transform': [
                        {'method': 'no_transform', 'parameters': {}}]}}
            ))

        # Add a trainer
        training_pipeline.add_trainer(TFFeedForwardTrainer(
            batch_size=1,
            loss='binary_crossentropy',
            last_activation='sigmoid',
            output_units=1,
            metrics=['accuracy'],
            epochs=i))

        # Run the pipeline locally
        training_pipeline.run()

except Exception as e:
    logger.error(e)
