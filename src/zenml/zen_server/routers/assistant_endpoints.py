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
"""Endpoint definitions for plugin flavors."""

import json
import os
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Security
from fastapi.responses import StreamingResponse

from zenml.constants import (
    API,
    ASSISTANT,
    VERSION_1,
)
from zenml.enums import ModelStages
from zenml.model.model import Model
from zenml.models import ReportRequest
from zenml.models.v2.core.model_version import ModelVersionFilter
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.utils import (
    zen_store,
)

assistant_router = APIRouter(
    prefix=API + VERSION_1 + ASSISTANT,
    tags=["AI"],
    responses={401: error_response, 403: error_response},
)


@assistant_router.post(
    "/compare-model-versions",
)
def compare_model_versions(
    model_id: Optional[UUID] = None,
    model_version_ids: List[UUID] = [],
    persona: str = "",
    auth_context: AuthContext = Security(authorize),
) -> StreamingResponse:
    """Compare model versions using LLM assistant.

    Args:
        model_id: ID of the model to compare.
        model_version_ids: IDs of the model versions to compare.
        persona: The persona of the LLM assistant.
        auth_context: Auth context.

    Returns:
        The LLM assistant streaming response.

    Raises:
        HTTPException: If no model id is provided and no model versions are selected,
            or too few versions found for comparison.
    """
    # Fetch model versions, prepare data for LLM
    versions: List[Model] = []

    if model_version_ids:
        for id_ in model_version_ids:
            model_version = (
                zen_store()
                .get_model_version(model_version_id=id_)
                .to_model_class()
            )
            versions.append(model_version)
            if model_id and model_version.model_id != model_id:
                raise HTTPException(
                    status_code=422,
                    detail="Versions don't belong to same model",
                )
            elif not model_id:
                model_id = model_version.model_id
    else:
        if not model_id:
            raise HTTPException(
                status_code=422,
                detail="No model id provided and no model versions selected.",
            )
        versions = []
        for stage in [
            ModelStages.PRODUCTION,
            ModelStages.STAGING,
        ]:
            if (
                items := zen_store()
                .list_model_versions(
                    model_name_or_id=model_id,
                    model_version_filter_model=ModelVersionFilter(stage=stage),
                )
                .items
            ):
                versions.append(items[0].to_model_class())
        if (
            items := zen_store()
            .list_model_versions(
                model_name_or_id=model_id,
                model_version_filter_model=ModelVersionFilter(
                    size=1, sort_by="desc:created"
                ),
            )
            .items
        ):
            if items[0].id not in [
                model_version.id for model_version in versions
            ]:
                versions.append(items[0].to_model_class())
    if len(versions) < 2:
        raise HTTPException(
            status_code=422,
            detail="Not enough model versions to compare, try selecting more.",
        )

    from litellm import completion
    from litellm.types.utils import ModelResponse, StreamingChoices

    extracted_infos: List[Dict[str, Any]] = []
    for mv in versions:
        extracted_infos.append(mv._get_details_for_llm(is_all=True))

    if persona == "dev":
        prompt_preface = (
            "You are talking to a very technical person, "
            "show all the details!\n"
        )
    elif persona == "executive":
        prompt_preface = (
            "You are talking to a business person, "
            "keep only important details and be specific!\n"
        )
    else:
        prompt_preface = "You are talking to a semi-technical person, "
        "so try to keep important technical details, but don't be "
        "too technical in explaining the differences!\n"

    prompt_metadata = (
        f"{prompt_preface}Given this metadata information from {len(model_version_ids)} "
        "ML models compare them and highlight the main differences only "
        "using the metadata values, not the keys."
        "Always used the id given before the information to refer to models:"
    )
    query_metadata = prompt_metadata
    for info in extracted_infos:
        query_metadata += f"\n\n\"{info['model_name']}/{info['version']}\". {json.dumps(info['metadata'])} {json.dumps(info['artifacts'])}"

    prompt_pipelines = (
        f"{prompt_preface}Given this pipeline runs information from {len(model_version_ids)} "
        "ML models compare them and highlight the main differences. "
        "Always used the id given before the information to refer to models:"
    )
    query_pipelines = prompt_pipelines
    for info in extracted_infos:
        query_pipelines += f"\n\n\"{info['model_name']}/{info['version']}\". {json.dumps(info['pipeline_runs'])}"

    async def _iterator(
        queries: List[List[str]],
    ) -> AsyncIterator[str]:
        is_very_first = True
        for header, query in queries:
            # Send the query to the OpenAI API
            response = completion(
                model="azure/gpt-35-turbo",
                api_base="https://zentestgpt4.openai.azure.com/",
                api_version="2024-05-01-preview",
                api_key=os.getenv("OPENAI_API_KEY"),
                messages=[{"content": query, "role": "user"}],
                max_tokens=4096,
                stream=True,
            )
            if is_very_first:
                is_very_first = False
                yield f"# {header}\n\n"
            else:
                yield f"\n\n# {header}\n\n"
            for res in response:
                if isinstance(res, ModelResponse):
                    if isinstance(res.choices[0], StreamingChoices):
                        if content := res.choices[0].delta.content:
                            yield str(content)

    async def _create_report_wrapper(*args, **kwargs) -> AsyncIterator[str]:
        content = ""

        async for res in _iterator(*args, **kwargs):
            content += res
            yield res

        report_request = ReportRequest(
            user=auth_context.user.id,
            content=content,
            persona=persona,
            model_id=versions[0].model_id,
            model_version_ids=[
                version.model_version_id for version in versions
            ],
        )
        zen_store().create_report(report_request)

    return StreamingResponse(
        content=_create_report_wrapper(
            [
                ["Metadata analysis", query_metadata],
                ["Usage analysis", query_pipelines],
            ]
        ),
        media_type="text/event-stream",
    )
