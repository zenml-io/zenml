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
    CategoricalDomainSplitStep
from zenml.core.repo.repo import Repository
from examples.gan.gan_functions import CycleGANTrainer
from examples.gan.preprocessing import GANPreprocessor

repo: Repository = Repository().get_instance()

gan_pipeline = TrainingPipeline(name="whynotletitfly",
                                enable_cache=False)

try:
    ds = ImageDatasource(name="gan_images",
                         base_path="/Users/nicholasjunge/workspaces/maiot/ce_project/images_mini")
except:
    ds = repo.get_datasource_by_name('gan_images')

gan_pipeline.add_datasource(ds)

gan_pipeline.add_split(CategoricalDomainSplitStep(categorical_column="label",
                                                  split_map={"train": [0],
                                                             "eval": [1]}))

gan_pipeline.add_preprocesser(GANPreprocessor())

# gan_pipeline.add_preprocesser(transform_step)

gan_pipeline.add_trainer(CycleGANTrainer(epochs=5))

gan_pipeline.run()
