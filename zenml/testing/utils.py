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
import zenml
import tensorflow as tf
from zenml.core.repo.repo import Repository
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.datasources.csv_datasource import CSVDatasource
from zenml.core.steps.preprocesser.standard_preprocesser \
    .standard_preprocesser import \
    StandardPreprocesser
from zenml.core.steps.split.categorical_domain_split_step import \
    CategoricalDomainSplit
from zenml.core.steps.trainer.tensorflow_trainers.tf_ff_trainer import \
    FeedForwardTrainer

# reset pipeline root to redirect to testing so that it writes the yamls there
ZENML_ROOT = zenml.__path__[0]
TEST_ROOT = os.path.join(ZENML_ROOT, "testing")

pipeline_root = os.path.join(TEST_ROOT, "test_pipelines")
csv_root = os.path.join(TEST_ROOT, "test_data")
image_root = os.path.join(csv_root, "images")


def run_pipelines():
    repo: Repository = Repository.get_instance()
    repo.zenml_config.set_pipelines_dir(pipeline_root)
    training_pipeline = TrainingPipeline(name='csvtest{0}'.format(1))

    try:
        # Add a datasource, automatically track and version it.
        ds = CSVDatasource(name='my_csv_datasource',
                           path=os.path.join(csv_root,
                                             "my_dataframe.csv"))
    except:
        ds = repo.get_datasource_by_name("my_csv_datasource")

    training_pipeline.add_datasource(ds)

    # Add a split
    training_pipeline.add_split(CategoricalDomainSplit(
        categorical_column="name",
        split_map={'train': ["arnold", "nicholas"],
                   'eval': ["lülük"]}))

    # Add a preprocessing unit
    training_pipeline.add_preprocesser(
        StandardPreprocesser(
            features=["name", "age", "date"],
            labels=['gpa']
        )
    )

    # Add a trainer
    training_pipeline.add_trainer(FeedForwardTrainer(
        batch_size=1,
        loss='binary_crossentropy',
        last_activation='sigmoid',
        output_units=1,
        metrics=['accuracy'],
        epochs=1))

    # Run the pipeline locally
    try:
        training_pipeline.run()
    except Exception as e:
        print(e)
