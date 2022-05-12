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


from pipelines.quickstart_pipeline.pipeline_definition import (
    quickstart_pipeline,
)
from steps.deployer.deployment_trigger import deployment_trigger
from steps.drift_detector.evidently_reference_data_splitter import (
    get_reference_data,
)
from steps.evaluator.sklearn_evaluator import evaluator
from steps.importer.import_digits import importer
from steps.trainer.sklearn_svc_trainer import svc_trainer_mlflow

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

if __name__ == "__main__":

    # We need to make sure the evidently step is configured properly
    evidently_profile_config = EvidentlyProfileConfig(
        column_mapping=None, profile_sections=["datadrift"]
    )

    p = quickstart_pipeline(
        importer=importer(),
        trainer=svc_trainer_mlflow(),
        evaluator=evaluator(),
        get_reference_data=get_reference_data(),
        drift_detector=EvidentlyProfileStep(config=evidently_profile_config),
        deployment_trigger=deployment_trigger(),
        model_deployer=mlflow_model_deployer_step(),
    )

    p.run()

    repo = Repository()
    pipelines = repo.get_pipelines()
    my_pipeline = repo.get_pipeline(pipeline_name="quickstart_pipeline")
    latest_run = my_pipeline.runs[-1]

    PipelineRunLineageVisualizer().visualize(latest_run)

    outputs = latest_run.get_step(name="get_reference_data")
    FacetStatisticsVisualizer().visualize(outputs)

    drift_detection_step = latest_run.get_step(name="drift_detector")
    EvidentlyVisualizer().visualize(drift_detection_step)

    model_deployer = repo.active_stack.model_deployer
    services = model_deployer.find_model_server(
        pipeline_name="quickstart_pipeline",
        pipeline_step_name="mlflow_model_deployer_step",
        running=True,
    )
    service = services[0]
    service.check_status()

    X_test = latest_run.steps[0].outputs["X_test"].read()
    y_test = latest_run.steps[0].outputs["y_test"].read()

    print(f"Model predicted {pred0}, true label was {y_test[0]}")
