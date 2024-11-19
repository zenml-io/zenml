#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
from contextlib import ExitStack as does_not_raise
from datetime import datetime
from uuid import uuid4

from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.models import (
    PipelineBuildResponse,
    PipelineBuildResponseBody,
    RunTemplateResponse,
    RunTemplateResponseBody,
    RunTemplateResponseMetadata,
    RunTemplateResponseResources,
)
from zenml.zen_server.template_execution.utils import (
    deployment_request_from_template,
)


def test_creating_deployment_request_from_template(
    clean_client_with_run, mocker
):
    mocker.patch(
        "zenml.zen_server.template_execution.utils.zen_store",
        return_value=clean_client_with_run.zen_store,
    )

    deployments = clean_client_with_run.list_deployments(hydrate=True)
    assert len(deployments) == 1

    deployment = deployments[0]

    build = PipelineBuildResponse(
        id=uuid4(),
        body=PipelineBuildResponseBody(
            created=datetime.utcnow(), updated=datetime.utcnow()
        ),
    )
    deployment.metadata.build = build

    template_response = RunTemplateResponse(
        id=uuid4(),
        name="template",
        body=RunTemplateResponseBody(
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
            user=deployment.user,
            runnable=True,
        ),
        metadata=RunTemplateResponseMetadata(workspace=deployment.workspace),
        resources=RunTemplateResponseResources(
            source_deployment=deployment, tags=[]
        ),
    )

    with does_not_raise():
        deployment_request_from_template(
            template=template_response,
            config=PipelineRunConfiguration(),
            user_id=deployment.user.id,
        )
