#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
from pipelines.training_pipeline.training_pipeline import (
    neptune_example_pipeline,
)
from steps.evaluator.evaluator_step import tf_evaluator
from steps.loader.loader_step import loader_mnist
from steps.normalizer.normalizer_step import normalizer
from steps.trainer.trainer_step import TrainerParameters, tf_trainer

if __name__ == "__main__":
    # Initialize a pipeline run
    run = neptune_example_pipeline(
        importer=loader_mnist(),
        normalizer=normalizer(),
        trainer=tf_trainer(params=TrainerParameters(epochs=5, lr=0.0003)),
        evaluator=tf_evaluator(),
    )

    run.run()
