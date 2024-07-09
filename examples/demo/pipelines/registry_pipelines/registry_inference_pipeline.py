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
from steps.deployer import deploy_to_databricks
from steps.dynamic_importer_step import dynamic_importer
from steps.predict_preprocessor_step import predict_preprocessor
from steps.predictor_step import predictor

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import MLFLOW, SKLEARN
from zenml.integrations.databricks.flavors.databricks_orchestrator_flavor import DatabricksOrchestratorSettings
    

docker_settings = DockerSettings(
    required_integrations=[MLFLOW, SKLEARN], requirements=["scikit-image"]
)

databricks_settings = DatabricksOrchestratorSettings(
    cluster_name="inferencing-cluster",
    node_type_id="standard_d8ads_v5",
)

@pipeline(enable_cache=True, settings={"docker": docker_settings, "orchestrator.databricks": DatabricksOrchestratorSettings()})
def mlflow_registry_inference_pipeline():
    # Link all the steps artifacts together
    deployed_model = deploy_to_databricks()
    batch_data = dynamic_importer()
    inference_data = predict_preprocessor(batch_data)
    predictor(deployed_model, inference_data)
