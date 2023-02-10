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


from pipelines.deployment_inference_pipeline.deployment_inference_pipeline import (
    deployment_inference_pipeline,
)
from pipelines.training_pipeline.training_pipeline import (
    mlflow_training_pipeline,
)
from steps.dynamic_importer.dynamic_importer_step import dynamic_importer
from steps.evaluator.evaluator_step import tf_evaluator
from steps.loader.loader_step import loader_mnist
from steps.normalizer.normalizer_step import normalizer
from steps.predictor.predictor_step import predictor
from steps.tf_predict_preprocessor.tf_predict_preprocessor_step import (
    tf_predict_preprocessor,
)
from steps.trainer.trainer_step import TrainerParameters, tf_trainer

from zenml.integrations.mlflow.mlflow_utils import get_tracking_uri
from zenml.integrations.mlflow.steps.mlflow_deployer import (
    MLFlowDeployerParameters,
    mlflow_model_registry_deployer_step,
)
from zenml.integrations.mlflow.steps.mlflow_registry import (
    MLFlowRegistryParameters,
    mlflow_register_model_step,
)

if __name__ == "__main__":
    # Initialize a training pipeline runs that will be logged to mlflow
    for i, lr in enumerate([0.001, 0.003, 0.005]):
        mlflow_training_pipeline(
            importer=loader_mnist(),
            normalizer=normalizer(),
            trainer=tf_trainer(params=TrainerParameters(epochs=5, lr=lr)),
            evaluator=tf_evaluator(),
            model_register=mlflow_register_model_step(
                params=MLFlowRegistryParameters(
                    registered_model_name="Tensorflow-mnist-model",
                    registered_model_description="A simple mnist model trained with zenml",
                    tags={"framework": "tensorflow", "dataset": "mnist"},
                    description=f"The {i+1}th run of the mlflow_training_pipeline with a learning rate of {lr}",
                )
            ),
        ).run()

    # Initialize a model deployment & inference pipeline
    pipeline = deployment_inference_pipeline(
        mlflow_model_deployer=mlflow_model_registry_deployer_step(
            params=MLFlowDeployerParameters(
                registered_model_name="Tensorflow-mnist-model",
                registered_model_version="2",
                # or you can use the model stage if you have set it in the mlflow registry
                # registered_model_stage="Staging",
            )
        ),
        dynamic_importer=dynamic_importer(),
        predict_preprocessor=tf_predict_preprocessor(),
        predictor=predictor(),
    )
    pipeline.run()

    print(
        "Now run \n "
        f"    mlflow ui --backend-store-uri '{get_tracking_uri()}'\n"
        "To inspect your experiment runs within the mlflow UI.\n"
        "You can find your runs tracked within the `mlflow_example_pipeline`"
        "experiment. Here you'll also be able to compare the two runs.)"
    )
