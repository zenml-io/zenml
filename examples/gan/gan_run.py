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

from zenml.core.datasources.image_datasource import ImageDatasource
from zenml.core.pipelines.training_pipeline import TrainingPipeline
from zenml.core.steps.split.categorical_domain_split_step import \
    CategoricalDomainSplit
from zenml.core.repo.repo import Repository
from examples.gan.trainer.trainer_step import CycleGANTrainer
from examples.gan.preprocessing.preprocessor import GANPreprocessor

repo: Repository = Repository().get_instance()

gan_pipeline = TrainingPipeline(name="gan_test",
                                enable_cache=True)

try:
    ds = ImageDatasource(name="gan_images",
                         base_path="gs://zenml_quickstart/cycle_gan_mini")
except:
    ds = repo.get_datasource_by_name('gan_images')

gan_pipeline.add_datasource(ds)

gan_pipeline.add_split(CategoricalDomainSplit(categorical_column="label",
                                              split_map={"train": ["monet"],
                                                         "eval": ["real"]}))

gan_pipeline.add_preprocesser(GANPreprocessor())

gan_pipeline.add_trainer(CycleGANTrainer(epochs=100))

gan_pipeline.run()
