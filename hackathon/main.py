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
from typing import Dict
from zenml.client import Client
from zenml.config.pipeline_spec import PipelineSpec
from zenml.models.v2.core.step_run import StepRunResponse
import json


### Helper functions for the AI script

# Get the latest run for a model version
def get_model_version_latest_run(model_version_id: str) -> str:
    """Get the latest run for a model version.
    
    Args:
        model_version_id (str): The model version ID.
    
    Returns:
        str: The latest run ID.
    """
    pipeline_run_ids = Client().zen_store.get_model_version(model_version_id).pipeline_run_ids
    latest_run_id = list(pipeline_run_ids.values())[-1]
    return latest_run_id

# Get code reference for a run
def get_run_steps(run_id: str) -> Dict[str, "StepRunResponse"]:
    """Get the steps for a run.
    
    Args:
        run_id (str): The run ID.
        
    Returns:
        str: The steps for the run.
    """
    return Client().zen_store.get_run(run_id).steps

# Get the code reference for a step
def get_step_code_reference(step: "StepRunResponse") -> str:
    """Get the code reference for a step.
    
    Args:
        step (StepRunResponse): The step.
        
    Returns:
        str: The code reference for the step.
    """
    return step.source_code

def get_pipeline_info(run_id) -> str:
    return Client().zen_store.get_run(run_id).pipeline.spec.model_dump_json()

# Construct a JSON response of the steps code from a pipeline run
def construct_json_response_of_steps_code_from_pipeline_run(run_id: str) -> str:
    """Construct a JSON response of the steps code from a pipeline run.
    
    Args:
        run_id (str): The run ID.
        
    Returns:
        str: The JSON response of the steps code from the pipeline run.
    """
    steps = get_run_steps(run_id)
    pipeline_info = get_pipeline_info(run_id)
    steps_code = {}
    for step_id, step in steps.items():
        steps_code[step_id] = get_step_code_reference(step)
    response = json.dumps(steps_code)
    return response

# Get the used stack for a run
def get_stack_and_components_for_run(run_id: str) -> str:
    """Get the used stack for a run.
    
    Args:
        run_id (str): The run ID.
        
    Returns:
        str: The used stack for the run.
    """
    return Client().zen_store.get_run(run_id).stack.to_yaml()

# Construct a JSON response of the stack and components for a pipeline run
def construct_json_response_of_stack_and_components_from_pipeline_run(run_id: str) -> str:
    """Construct a JSON response of the stack and components for a pipeline run.
    
    Args:
        run_id (str): The run ID.
        
    Returns:
        str: The JSON response of the stack and components for the pipeline run.
    """
    stack_and_components = get_stack_and_components_for_run(run_id)
    response = json.dumps(stack_and_components)
    return response
    
def main():
    model_version_id = "08beb6db-b899-4d8b-8972-39dbef405c70"
    # Get the latest run for a model version
    latest_run = get_model_version_latest_run(model_version_id)
    steps_code = construct_json_response_of_steps_code_from_pipeline_run(latest_run)
    print(steps_code)
    # Get the stack and components for a run
    stack_and_components = construct_json_response_of_stack_and_components_from_pipeline_run(latest_run)
    print(stack_and_components)
    
    
if __name__ == "__main__":
    main()
    
        