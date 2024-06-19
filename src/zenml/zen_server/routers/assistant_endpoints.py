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
from typing import Any, AsyncIterator, Dict, List
from uuid import UUID

from fastapi import APIRouter, Security
from fastapi.responses import StreamingResponse

from zenml.constants import (
    API,
    ASSISTANT,
    VERSION_1,
)
from zenml.model.model import Model
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


@assistant_router.post("/compare-model-versions")
async def compare_model_versions(
    model_version_ids: List[UUID],
    persona: str = "",
    _: AuthContext = Security(authorize),
) -> StreamingResponse:
    # Fetch model versions, prepare data

    model_id = None
    versions: List[Model] = []
    for id_ in model_version_ids:
        model_version = (
            zen_store()
            .get_model_version(model_version_id=id_)
            .to_model_class()
        )
        versions.append(model_version)
        if model_id and model_version.model_id != model_id:
            raise ValueError("Versions don't belong to same model")

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

    return StreamingResponse(
        content=_iterator(
            [
                ["Metadata analysis", query_metadata],
                ["Usage analysis", query_pipelines],
            ]
        ),
        media_type="text/event-stream",
    )
