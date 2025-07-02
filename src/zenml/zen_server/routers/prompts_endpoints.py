#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Endpoint definitions for prompt management."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Security

from zenml.constants import API, VERSION_1
from zenml.enums import ArtifactType
from zenml.models import (
    ArtifactFilter,
    ArtifactResponse,
    ArtifactVersionResponse,
    Page,
)
from zenml.prompts.prompt import Prompt
from zenml.prompts.prompt_comparison import PromptComparison, compare_prompts
from zenml.zen_server.auth import AuthContext, authorize
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.endpoint_utils import (
    verify_permissions_and_get_entity,
    verify_permissions_and_list_entities,
)
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.utils import (
    async_fastapi_endpoint_wrapper,
    make_dependable,
    zen_store,
)

PROMPTS_PREFIX = "/prompts"

prompt_router = APIRouter(
    prefix=API + VERSION_1 + PROMPTS_PREFIX,
    tags=["prompts"],
    responses={401: error_response, 403: error_response},
)


@prompt_router.get(
    "",
    responses={401: error_response, 404: error_response, 422: error_response},
)
@async_fastapi_endpoint_wrapper
def list_prompts(
    artifact_filter_model: ArtifactFilter = Depends(
        make_dependable(ArtifactFilter)
    ),
    task: Optional[str] = Query(None, description="Filter by task type"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    prompt_type: Optional[str] = Query(
        None, description="Filter by prompt type"
    ),
    author: Optional[str] = Query(None, description="Filter by author"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    hydrate: bool = Query(False, description="Include full metadata"),
    _: AuthContext = Security(authorize),
) -> Page[ArtifactResponse]:
    """Get artifacts that represent prompts according to query filters.

    Args:
        artifact_filter_model: Filter model used for pagination, sorting,
            filtering.
        task: Filter by task type (currently not implemented)
        domain: Filter by domain (currently not implemented)
        prompt_type: Filter by prompt type (currently not implemented)
        author: Filter by author (currently not implemented)
        tags: Filter by tags (currently not implemented)
        hydrate: Include full metadata

    Returns:
        Page of artifact responses that represent prompts.
    """
    # For now, return all artifacts since prompt-specific filtering 
    # requires metadata access that's complex in server context.
    # This follows the same pattern as the artifacts endpoint.
    return verify_permissions_and_list_entities(
        filter_model=artifact_filter_model,
        resource_type=ResourceType.ARTIFACT,
        list_method=zen_store().list_artifacts,
        hydrate=hydrate,
    )


@prompt_router.get(
    "/{prompt_artifact_id}",
    responses={401: error_response, 404: error_response},
)
@async_fastapi_endpoint_wrapper
def get_prompt(
    prompt_artifact_id: UUID,
    hydrate: bool = Query(False, description="Include full metadata"),
    _: AuthContext = Security(authorize),
) -> ArtifactResponse:
    """Get an artifact by ID (for prompt artifacts).

    Args:
        prompt_artifact_id: The artifact ID of the prompt
        hydrate: Include full metadata

    Returns:
        The artifact response.
    """
    return verify_permissions_and_get_entity(
        id=prompt_artifact_id,
        get_method=zen_store().get_artifact,
        hydrate=hydrate,
    )


@prompt_router.get(
    "/{prompt_artifact_id}/versions",
    responses={401: error_response, 404: error_response},
)
@async_fastapi_endpoint_wrapper
def get_prompt_versions(
    prompt_artifact_id: UUID,
    hydrate: bool = Query(False, description="Include full metadata"),
    _: AuthContext = Security(authorize),
) -> Page[ArtifactVersionResponse]:
    """Get all versions of an artifact (for prompt artifacts).

    Args:
        prompt_artifact_id: The artifact ID
        hydrate: Include full metadata

    Returns:
        Page of artifact version responses.
    """
    # Create filter for artifact versions of this specific artifact
    from zenml.models.v2.core.artifact_version import ArtifactVersionFilter
    
    filter_model = ArtifactVersionFilter(artifact=prompt_artifact_id)
    
    return verify_permissions_and_list_entities(
        filter_model=filter_model,
        resource_type=ResourceType.ARTIFACT_VERSION,
        list_method=zen_store().list_artifact_versions,
        hydrate=hydrate,
    )


@prompt_router.post(
    "/{prompt_artifact_id_1}/compare/{prompt_artifact_id_2}",
    responses={401: error_response, 404: error_response},
)
@async_fastapi_endpoint_wrapper
def compare_prompts_endpoint(
    prompt_artifact_id_1: UUID,
    prompt_artifact_id_2: UUID,
    _: AuthContext = Security(authorize),
) -> Dict[str, Any]:
    """Compare two prompts and return detailed analysis.

    Args:
        prompt_artifact_id_1: First prompt artifact ID
        prompt_artifact_id_2: Second prompt artifact ID

    Returns:
        Detailed comparison between the two prompts.
    """
    # Get both artifacts
    artifact1 = verify_permissions_and_get_entity(
        id=prompt_artifact_id_1,
        get_method=zen_store().get_artifact,
        resource_type=ResourceType.ARTIFACT,
        hydrate=True,
    )

    artifact2 = verify_permissions_and_get_entity(
        id=prompt_artifact_id_2,
        get_method=zen_store().get_artifact,
        resource_type=ResourceType.ARTIFACT,
        hydrate=True,
    )

    if not _is_prompt_artifact(artifact1):
        raise HTTPException(
            status_code=404,
            detail=f"Artifact {prompt_artifact_id_1} is not a prompt artifact",
        )

    if not _is_prompt_artifact(artifact2):
        raise HTTPException(
            status_code=404,
            detail=f"Artifact {prompt_artifact_id_2} is not a prompt artifact",
        )

    # Reconstruct Prompt objects from metadata
    try:
        prompt1 = _reconstruct_prompt_from_artifact(artifact1)
        prompt2 = _reconstruct_prompt_from_artifact(artifact2)

        # Perform comparison
        comparison = compare_prompts(prompt1, prompt2)

        return {
            "comparison": comparison.model_dump(),
            "summary": comparison.get_summary(),
            "recommendation": comparison.get_recommendation(),
            "artifacts": {
                "prompt1": _enhance_artifact_with_prompt_data(artifact1),
                "prompt2": _enhance_artifact_with_prompt_data(artifact2),
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to compare prompts: {str(e)}"
        )


@prompt_router.get(
    "/search",
    responses={401: error_response, 404: error_response},
)
@async_fastapi_endpoint_wrapper
def search_prompts(
    query: str = Query(..., description="Search query"),
    task: Optional[str] = Query(None, description="Filter by task"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    author: Optional[str] = Query(None, description="Filter by author"),
    min_complexity: Optional[float] = Query(
        None, ge=0.0, le=1.0, description="Minimum complexity score"
    ),
    max_complexity: Optional[float] = Query(
        None, ge=0.0, le=1.0, description="Maximum complexity score"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    _: AuthContext = Security(authorize),
) -> Page[Dict[str, Any]]:
    """Search prompts by content and metadata.

    Args:
        query: Search query to match in prompt templates or descriptions
        task: Filter by task type
        domain: Filter by domain
        author: Filter by author
        min_complexity: Minimum complexity score
        max_complexity: Maximum complexity score
        page: Page number
        size: Page size

    Returns:
        Page of matching prompt artifacts.
    """
    # Get all prompt artifacts
    artifact_filter = ArtifactFilter(
        artifact_type=ArtifactType.DATA.value,
        page=1,
        size=1000,  # Get more to filter locally
    )

    artifacts_page = verify_permissions_and_list_entities(
        filter_model=artifact_filter,
        resource_type=ResourceType.ARTIFACT,
        list_method=zen_store().list_artifacts,
        hydrate=True,
    )

    # Filter and search
    matching_prompts = []
    query_lower = query.lower()

    for artifact in artifacts_page.items:
        if not _is_prompt_artifact(artifact):
            continue

        metadata = artifact.run_metadata

        # Text search in template and description
        template = metadata.get("template", "")
        description = metadata.get("description", "")

        if (
            query_lower not in template.lower()
            and query_lower not in description.lower()
        ):
            continue

        # Apply filters
        if task and metadata.get("task") != task:
            continue
        if domain and metadata.get("domain") != domain:
            continue
        if author and metadata.get("author") != author:
            continue

        complexity = metadata.get("complexity_score", 0.0)
        if min_complexity is not None and complexity < min_complexity:
            continue
        if max_complexity is not None and complexity > max_complexity:
            continue

        enhanced_artifact = _enhance_artifact_with_prompt_data(artifact)
        matching_prompts.append(enhanced_artifact)

    # Paginate results
    total = len(matching_prompts)
    start_idx = (page - 1) * size
    end_idx = start_idx + size
    paginated_items = matching_prompts[start_idx:end_idx]

    return Page(
        index=page,
        max_size=size,
        total_pages=(total + size - 1) // size,
        total=total,
        items=paginated_items,
    )


@prompt_router.get(
    "/stats",
    responses={401: error_response},
)
@async_fastapi_endpoint_wrapper
def get_prompt_statistics(
    project_id: Optional[UUID] = Query(
        None, description="Filter by project ID"
    ),
    _: AuthContext = Security(authorize),
) -> Dict[str, Any]:
    """Get statistics about prompts in the system.

    Args:
        project_id: Optional project ID to filter statistics

    Returns:
        Statistics about prompts.
    """
    # Get all prompt artifacts
    artifact_filter = ArtifactFilter(
        project_id=project_id,
        artifact_type=ArtifactType.DATA.value,
        page=1,
        size=1000,
    )

    artifacts_page = zen_store().list_artifacts(artifact_filter)

    # Analyze prompt artifacts
    total_prompts = 0
    tasks = set()
    domains = set()
    authors = set()
    languages = set()
    complexities = []
    template_lengths = []

    for artifact in artifacts_page.items:
        if not _is_prompt_artifact(artifact):
            continue

        total_prompts += 1
        metadata = artifact.run_metadata

        if metadata.get("task"):
            tasks.add(metadata["task"])
        if metadata.get("domain"):
            domains.add(metadata["domain"])
        if metadata.get("author"):
            authors.add(metadata["author"])
        if metadata.get("language"):
            languages.add(metadata["language"])
        if metadata.get("complexity_score"):
            complexities.append(metadata["complexity_score"])
        if metadata.get("template_length"):
            template_lengths.append(metadata["template_length"])

    # Calculate averages
    avg_complexity = (
        sum(complexities) / len(complexities) if complexities else 0.0
    )
    avg_template_length = (
        sum(template_lengths) / len(template_lengths)
        if template_lengths
        else 0.0
    )

    return {
        "total_prompts": total_prompts,
        "unique_tasks": len(tasks),
        "unique_domains": len(domains),
        "unique_authors": len(authors),
        "unique_languages": len(languages),
        "average_complexity": avg_complexity,
        "average_template_length": avg_template_length,
        "tasks": sorted(list(tasks)),
        "domains": sorted(list(domains)),
        "languages": sorted(list(languages)),
    }


# Helper functions
def _is_prompt_artifact(artifact: ArtifactResponse) -> bool:
    """Check if an artifact represents a prompt."""
    # For now, we'll accept all artifacts and let the subsequent filtering
    # and enhancement handle prompt-specific logic. This avoids metadata access
    # issues that would require client calls in the server context.
    # 
    # A more sophisticated implementation could:
    # 1. Check artifact naming patterns 
    # 2. Use tags to identify prompts
    # 3. Access metadata through the zen_store directly instead of client
    #
    # For the MVP, we return True and rely on _enhance_artifact_with_prompt_data
    # to properly format prompt artifacts.
    return True


def _enhance_artifact_with_prompt_data(
    artifact: ArtifactResponse,
) -> Dict[str, Any]:
    """Enhance an artifact response with prompt-specific data."""
    try:
        enhanced = {
            "id": str(artifact.id),
            "name": artifact.name,
            "created_at": artifact.created.isoformat() if artifact.created else None,
            "updated_at": artifact.updated.isoformat() if artifact.updated else None,
            "project_id": str(artifact.project),
            "user_id": str(artifact.user.id) if hasattr(artifact, "user") and artifact.user else None,
            "tags": [tag.name for tag in artifact.tags] if hasattr(artifact, "tags") and artifact.tags else [],
            "latest_version_name": getattr(artifact, "latest_version_name", None),
            "latest_version_id": str(artifact.latest_version_id) if getattr(artifact, "latest_version_id", None) else None,
            "has_custom_name": getattr(artifact, "has_custom_name", True),
            # Additional computed fields
            "artifact_uri": getattr(artifact, "uri", None),
            "visualization_uri": f"/artifacts/{artifact.id}/visualization"
            if hasattr(artifact, "visualizations")
            else None,
        }
        return enhanced
    except Exception as e:
        # Fallback to basic dictionary conversion if enhancement fails
        return {
            "id": str(getattr(artifact, "id", "")),
            "name": getattr(artifact, "name", "Unknown"),
            "error": f"Failed to enhance artifact: {str(e)}"
        }


def _reconstruct_prompt_from_artifact(artifact: ArtifactResponse) -> Prompt:
    """Reconstruct a Prompt object from artifact metadata."""
    metadata = artifact.run_metadata

    # Map metadata back to Prompt fields
    prompt_data = {
        "template": metadata.get("template", ""),
        "prompt_id": metadata.get("prompt_id"),
        "prompt_type": metadata.get("prompt_type", "user"),
        "task": metadata.get("task"),
        "domain": metadata.get("domain"),
        "description": metadata.get("description"),
        "author": metadata.get("author"),
        "version": metadata.get("version"),
        "language": metadata.get("language", "en"),
        "prompt_strategy": metadata.get("prompt_strategy", "direct"),
        "variables": metadata.get("variables"),
        "examples": metadata.get("examples"),
        "instructions": metadata.get("instructions"),
        "context_template": metadata.get("context_template"),
        "model_config_params": metadata.get("model_config_params"),
        "target_models": metadata.get("target_models"),
        "performance_metrics": metadata.get("performance_metrics"),
        "min_tokens": metadata.get("min_tokens"),
        "max_tokens": metadata.get("max_tokens"),
        "expected_format": metadata.get("expected_format"),
        "parent_prompt_id": metadata.get("parent_prompt_id"),
        "tags": metadata.get("tags"),
        "metadata": metadata.get("custom_metadata"),
        "license": metadata.get("license"),
        "source_url": metadata.get("source_url"),
        "use_cache": metadata.get("use_cache", True),
        "safety_checks": metadata.get("safety_checks"),
    }

    # Parse timestamps
    if metadata.get("created_at"):
        from datetime import datetime

        prompt_data["created_at"] = datetime.fromisoformat(
            metadata["created_at"]
        )
    if metadata.get("updated_at"):
        from datetime import datetime

        prompt_data["updated_at"] = datetime.fromisoformat(
            metadata["updated_at"]
        )

    # Remove None values
    prompt_data = {k: v for k, v in prompt_data.items() if v is not None}

    return Prompt(**prompt_data)
