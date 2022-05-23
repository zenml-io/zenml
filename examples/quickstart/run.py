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


from pipelines import inference_pipeline, training_pipeline
from steps import (
    deployment_trigger,
    evaluator,
    inference_data_loader,
    prediction_service_loader,
    predictor,
    skew_comparison,
    svc_trainer_mlflow,
    training_data_loader,
)

from zenml.integrations.dash.visualizers.pipeline_run_lineage_visualizer import (
    PipelineRunLineageVisualizer,
)
from zenml.integrations.evidently.steps import (
    EvidentlyProfileConfig,
    EvidentlyProfileStep,
)
from zenml.integrations.evidently.visualizers import EvidentlyVisualizer
from zenml.integrations.facets.visualizers.facet_statistics_visualizer import (
    FacetStatisticsVisualizer,
)
from zenml.integrations.mlflow.steps import mlflow_model_deployer_step
from zenml.repository import Repository


def main():

    # configure drift detector
    evidently_profile_config = EvidentlyProfileConfig(
        column_mapping=None, profile_sections=["datadrift"]
    )
    drift_detector = EvidentlyProfileStep(config=evidently_profile_config)

    # initialize and run training pipeline
    training_pipeline(
        training_data_loader=training_data_loader(),
        skew_comparison=skew_comparison(),
        trainer=svc_trainer_mlflow(),
        evaluator=evaluator(),
        deployment_trigger=deployment_trigger(),
        model_deployer=mlflow_model_deployer_step(),
    ).run(run_name="first_training_pipeline_run")

    # initialize and run inference pipeline
    inference_pipeline(
        inference_data_loader=inference_data_loader(),
        prediction_service_loader=prediction_service_loader(),
        predictor=predictor(),
        training_data_loader=training_data_loader(),
        skew_comparison=skew_comparison(),
        drift_detector=drift_detector,
    ).run(run_name="first_inference_pipeline_run")

    # fetch latest runs for each pipeline
    repo = Repository()
    train_run = repo.get_pipeline(pipeline_name="training_pipeline").runs[-1]
    inference_run = repo.get_pipeline(pipeline_name="inference_pipeline").runs[
        -1
    ]

    # visualize training pipeline
    PipelineRunLineageVisualizer().visualize(train_run)

    # visualize inference pipeline
    PipelineRunLineageVisualizer().visualize(inference_run)

    # visualize train-test skew
    train_test_skew_step = train_run.get_step(name="skew_comparison")
    FacetStatisticsVisualizer().visualize(train_test_skew_step)

    # visualize training-serving skew
    training_serving_skew_step = inference_run.get_step(name="skew_comparison")
    FacetStatisticsVisualizer().visualize(training_serving_skew_step)

    # visualize data drift
    drift_detection_step = inference_run.get_step(name="drift_detector")
    EvidentlyVisualizer().visualize(drift_detection_step)


if __name__ == "__main__":
    main()
