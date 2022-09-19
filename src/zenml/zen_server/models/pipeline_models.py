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
"""Project Models for the API endpoint definitions."""
from typing import Any, Dict, List, Optional

from pydantic import Field

from zenml.config.global_config import GlobalConfiguration
from zenml.models import (
    PipelineModel,
    PipelineRunModel,
    ProjectModel,
    UserModel,
)
from zenml.models.constants import MODEL_NAME_FIELD_MAX_LENGTH
from zenml.zen_server.models.base_models import (
    ProjectScopedCreateRequest,
    UpdateRequest,
)


class CreatePipelineRequest(ProjectScopedCreateRequest[PipelineModel]):
    """Pipeline model for create requests."""

    _MODEL_TYPE = PipelineModel

    name: str = Field(
        title="The name of the pipeline.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    docstring: Optional[str]
    configuration: Dict[str, str]


class UpdatePipelineRequest(UpdateRequest[PipelineModel]):
    """Pipeline model for update requests."""

    _MODEL_TYPE = PipelineModel

    name: Optional[str] = Field(
        title="The name of the pipeline.",
        max_length=MODEL_NAME_FIELD_MAX_LENGTH,
    )

    docstring: Optional[str]
    # TODO: [server] have another look at this to figure out if adding a
    #  single k:v pair overwrites the existing k:v pairs
    configuration: Optional[Dict[str, str]]


class HydratedPipelineModel(PipelineModel):
    """Pipeline model with User and Project fully hydrated."""

    runs: List["PipelineRunModel"] = Field(
        title="A list of the last x Pipeline Runs."
    )

    project: ProjectModel = Field(  # type: ignore[assignment]
        title="The project that contains this pipeline."
    )
    user: UserModel = Field(  # type: ignore[assignment]
        title="The user that created this pipeline.",
    )

    class Config:
        """Example of a json-serialized instance."""

        schema_extra: Dict[str, Any] = {
            "example": {
                "id": "24db6395-669b-4e6d-8e60-cc2c4f6c47cf",
                "name": "example_pipeline",
                "docstring": None,
                "configuration": {},
                "project": {
                    "id": "48533493-cb6d-4927-bc72-b8e998503d93",
                    "name": "default",
                    "description": "",
                    "created": "2022-09-15T11:43:29.994722",
                    "updated": "2022-09-15T11:43:29.994722",
                },
                "user": {
                    "id": "3143dec6-450e-4909-bf3e-a5f389b2a566",
                    "name": "default",
                    "full_name": "",
                    "email": "",
                    "active": "True",
                    "created": "2022-09-15T11:43:29.994722",
                    "updated": "2022-09-15T11:43:29.994722",
                },
                "created": "2022-09-15T11:43:29.994722",
                "updated": "2022-09-15T11:43:29.994722",
                "runs": [
                    {
                        "id": "c3a15c1e-7f77-4cd7-9fe6-e2fde19b7a39",
                        "name": "example_pipeline-16_Sep_22-14_30_25_931594",
                        "stack_id": "341dd1d4-13fe-4163-9921-a0587da31651",
                        "pipeline_id": "24db6395-669b-4e6d-8e60-cc2c4f6c47cf",
                        "runtime_configuration": {
                            "dag_filepath": "zenml/examples/airflow_orchestration/run.py",
                            "run_name": "example_pipeline-16_Sep_22-14_30_25_931594",
                            "schedule": None,
                        },
                        "zenml_version": "0.13.2",
                        "git_sha": None,
                        "mlmd_id": 2,
                        "user": "3143dec6-450e-4909-bf3e-a5f389b2a566",
                        "created": "2022-09-15T11:43:29.994722",
                        "updated": "2022-09-15T11:43:29.994722",
                    },
                    {
                        "id": "46e1e41f-9436-45ef-a4e8-46976dbbe6b8",
                        "name": "airflow_example_pipeline-16_Sep_22-14_30_53_621455",
                        "stack_id": "341dd1d4-13fe-4163-9921-a0587da31651",
                        "pipeline_id": "24db6395-669b-4e6d-8e60-cc2c4f6c47cf",
                        "runtime_configuration": {
                            "dag_filepath": "/zenml/examples/airflow_orchestration/run.py",
                            "run_name": "example_pipeline-16_Sep_22-14_30_53_621455",
                            "schedule": None,
                        },
                        "zenml_version": "0.13.2",
                        "git_sha": None,
                        "mlmd_id": 12,
                        "user": "3143dec6-450e-4909-bf3e-a5f389b2a566",
                        "created": "2022-09-15T11:43:29.994722",
                        "updated": "2022-09-15T11:43:29.994722",
                    },
                    {
                        "id": "0c4eac13-4691-4035-8836-ca12b5331eaa",
                        "name": "airflow_example_pipeline-16_Sep_22-14_31_05_349435",
                        "stack_id": "341dd1d4-13fe-4163-9921-a0587da31651",
                        "pipeline_id": "24db6395-669b-4e6d-8e60-cc2c4f6c47cf",
                        "runtime_configuration": {
                            "dag_filepath": "/examples/airflow_orchestration/run.py",
                            "run_name": "example_pipeline-16_Sep_22-14_31_05_349435",
                            "schedule": None,
                        },
                        "zenml_version": "0.13.2",
                        "git_sha": None,
                        "mlmd_id": 15,
                        "user": "3143dec6-450e-4909-bf3e-a5f389b2a566",
                        "created": "2022-09-15T11:43:29.994722",
                        "updated": "2022-09-15T11:43:29.994722",
                    },
                ],
            }
        }

    @classmethod
    def from_model(
        cls, pipeline_model: PipelineModel, num_runs: int = 3
    ) -> "HydratedPipelineModel":
        """Converts this model to a hydrated model.

        Returns:
            A hydrated model.
        """
        zen_store = GlobalConfiguration().zen_store

        project = zen_store.get_project(pipeline_model.project)
        user = zen_store.get_user(pipeline_model.user)
        runs = zen_store.list_runs(pipeline_id=pipeline_model.id)

        return cls(
            id=pipeline_model.id,
            name=pipeline_model.name,
            project=project,
            user=user,
            runs=runs[:num_runs],
            docstring=pipeline_model.docstring,
            configuration=pipeline_model.configuration,
            created=pipeline_model.created,
            updated=pipeline_model.updated,
        )
