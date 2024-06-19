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
import json
from typing import Any, Dict, List

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.logging.step_logging import fetch_logs
from zenml.models.v2.core.step_run import StepRunResponse


# Get the latest run for a model version
def get_model_version_latest_run(model_version_id: str) -> str:
    """Get the latest run for a model version.

    Args:
        model_version_id (str): The model version ID.

    Returns:
        str: The latest run ID.
    """
    pipeline_run_ids = (
        Client().zen_store.get_model_version(model_version_id).pipeline_run_ids
    )
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
def construct_json_response_of_steps_code_from_pipeline_run(
    run_id: str,
) -> str:
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
def construct_json_response_of_stack_and_components_from_pipeline_run(
    run_id: str,
) -> str:
    """Construct a JSON response of the stack and components for a pipeline run.

    Args:
        run_id (str): The run ID.

    Returns:
        str: The JSON response of the stack and components for the pipeline run.
    """
    stack_and_components = get_stack_and_components_for_run(run_id)
    response = json.dumps(stack_and_components)
    return response


# Get pipeline runs stats


# Get number of runs completed and failed
def get_pipeline_runs_stats(model_version_id: str) -> Dict[str, int]:
    """Get the number of runs completed and failed for a pipeline.

    Args:
        pipeline_id (str): The pipeline ID.

    Returns:
        Dict[str, int]: The number of runs completed and failed for the pipeline.
    """
    pipeline_run_ids = (
        Client().zen_store.get_model_version(model_version_id).pipeline_run_ids
    )
    runs_stats = {"total": 0, "completed": 0, "failed": 0}
    for run_id in pipeline_run_ids.values():
        run = Client().zen_store.get_run(run_id)
        runs_stats["total"] += 1
        if str(run.status) == "completed":
            runs_stats["completed"] += 1
        elif str(run.status) == "failed":
            runs_stats["failed"] += 1
    return runs_stats


# Get the number model artifacts for a run
def get_number_model_artifacts_for_run(model_version_id: str) -> int:
    """Get the number of model artifacts for a run.

    Args:
        model_version_id (str): The model version ID.

    Returns:
        int: The number of model artifacts for the run.
    """
    return len(
        Client()
        .zen_store.get_model_version(model_version_id)
        .model_artifact_ids
    )


# Get the number of artifacts for a run
def get_number_artifacts_for_run(model_version_id: str) -> int:
    """Get the number of artifacts for a run.

    Args:
        model_version_id (str): The model version ID.

    Returns:
        int: The number of artifacts for the run.
    """
    return len(
        Client()
        .zen_store.get_model_version(model_version_id)
        .data_artifact_ids
    )


# Get model version description section
def get_model_version_description_section(model_version_id: str) -> str:
    """Get the description section for a model version.

    Args:
        model_version_id (str): The model version ID.

    Returns:
        str: The description section for the model version.
    """
    return Client().zen_store.get_model_version(model_version_id).description


# Get the model version run metadata
def get_model_version_run_metadata(model_version_id: str) -> Dict[str, str]:
    """Get the run metadata for a model version.

    Args:
        model_version_id (str): The model version ID.

    Returns:
        Dict[str, str]: The run metadata for the model version.
    """
    run_metadata = {}
    for key, value in (
        Client()
        .zen_store.get_model_version(model_version_id)
        .run_metadata.items()
    ):
        run_metadata[key] = value.value
    return run_metadata


# Construct a JSON response of the model version run metadata
def construct_json_response_of_model_version_stats(
    model_version_id: str,
) -> str:
    """Construct a JSON response of the model version run metadata.

    Args:
        model_version_id (str): The model version ID.

    Returns:
        str: The JSON response of the model version run metadata.
    """
    model_version_stats = {}
    model_version_stats["run stats"] = get_pipeline_runs_stats(
        model_version_id
    )
    model_version_stats["model artifacts"] = (
        get_number_model_artifacts_for_run(model_version_id)
    )
    model_version_stats["data artifacts"] = get_number_artifacts_for_run(
        model_version_id
    )
    model_version_stats["description"] = get_model_version_description_section(
        model_version_id
    )
    model_version_stats["run metadata"] = get_model_version_run_metadata(
        model_version_id
    )
    response = json.dumps(model_version_stats)
    return response


# Get the failing steps for the runs
def get_failing_steps_for_runs(model_version_id: str) -> Dict[str, str]:
    """Get the failing steps for the runs.

    Args:
        model_version_id (str): The model version ID.

    Returns:
        Dict[str, str]: The failing steps for the runs.
    """
    pipeline_run_ids = (
        Client().zen_store.get_model_version(model_version_id).pipeline_run_ids
    )
    failing_steps: Dict[str, List[Any]] = {}
    for run_id in pipeline_run_ids.values():
        run = Client().zen_store.get_run(run_id)
        steps = {}
        if str(run.status) == "failed":
            steps = get_run_steps(run_id).values()
            for step in steps:
                failing_step_details = {}
                if str(step.status) == "failed":
                    failing_step_details["id"] = str(step.id)
                    if step.logs is not None:
                        failing_step_details["logs"] = fetch_logs(
                            zen_store=Client().zen_store,
                            artifact_store_id=run.stack.components[
                                StackComponentType.ARTIFACT_STORE
                            ][0].id,
                            logs_uri=step.logs.uri,
                        )
                    failing_step_details["code"] = get_step_code_reference(
                        step
                    )
                    failing_step_details["stack"] = (
                        get_stack_and_components_for_run(run_id)
                    )
                if step.name not in failing_steps.keys():
                    failing_steps[step.name] = [failing_step_details]
                failing_steps[step.name].append(failing_step_details)
    return failing_steps


# Construct a JSON response of the failing steps for the runs
def construct_json_response_of_failing_steps_for_runs(
    model_version_id: str,
) -> str:
    """Construct a JSON response of the failing steps for the runs.

    Args:
        model_version_id (str): The model version ID.

    Returns:
        str: The JSON response of the failing steps for the runs.
    """
    failing_steps = get_failing_steps_for_runs(model_version_id)
    response = json.dumps(failing_steps)
    return response
