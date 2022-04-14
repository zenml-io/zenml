#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from pipeline import (
    TrainerConfig,
    importer_mnist,
    mlflow_example_pipeline,
    normalizer,
    tf_evaluator,
    tf_trainer,
)

from zenml.integrations.mlflow.mlflow_environment import global_mlflow_env

if __name__ == "__main__":

    # Initialize a pipeline run
    run_1 = mlflow_example_pipeline(
        importer=importer_mnist(),
        normalizer=normalizer(),
        trainer=tf_trainer(config=TrainerConfig(epochs=5, lr=0.0003)),
        evaluator=tf_evaluator(),
    )

    run_1.run()

    # Initialize a pipeline run again
    run_2 = mlflow_example_pipeline(
        importer=importer_mnist(),
        normalizer=normalizer(),
        trainer=tf_trainer(config=TrainerConfig(epochs=5, lr=0.0001)),
        evaluator=tf_evaluator(),
    )

    run_2.run()
    with global_mlflow_env() as mlflow_env:
        print(
            "Now run \n "
            f"    mlflow ui --backend-store-uri {mlflow_env.tracking_uri}\n"
            "To inspect your experiment runs within the mlflow ui.\n"
            "You can find your runs tracked within the `mlflow_example_pipeline`"
            "experiment. Here you'll also be able to compare the two runs.)"
        )
