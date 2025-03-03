#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Utility functions for tags."""

from typing import (
    TYPE_CHECKING,
    Any,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    overload,
)
from uuid import UUID

from pydantic import BaseModel

from zenml.enums import ColorVariants, TaggableResourceTypes
from zenml.logger import get_logger

if TYPE_CHECKING:
    from zenml.models import TagRequest
    from zenml.zen_stores.schemas.base_schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

logger = get_logger(__name__)


class Tag(BaseModel):
    """A tag is a label that can be applied to a pipeline run."""

    name: str
    color: Optional[ColorVariants] = None
    singleton: Optional[bool] = None
    hierarchical: Optional[bool] = None

    def to_request(self) -> "TagRequest":
        """Convert the tag to a TagRequest.

        Returns:
            The tag as a TagRequest.
        """
        from zenml.models import TagRequest

        request = TagRequest(name=self.name)
        if self.color is not None:
            request.color = self.color

        if self.singleton is not None:
            request.singleton = self.singleton
        return request


def get_schema_from_resource_type(
    resource_type: TaggableResourceTypes,
) -> Any:
    """Get the schema for a resource type.

    Args:
        resource_type: The type of the resource.

    Returns:
        The schema for the resource type.
    """
    from zenml.zen_stores.schemas import (
        ArtifactSchema,
        ArtifactVersionSchema,
        ModelSchema,
        ModelVersionSchema,
        PipelineRunSchema,
        PipelineSchema,
        RunTemplateSchema,
    )

    resource_type_to_schema_mapping = {
        TaggableResourceTypes.ARTIFACT: ArtifactSchema,
        TaggableResourceTypes.ARTIFACT_VERSION: ArtifactVersionSchema,
        TaggableResourceTypes.MODEL: ModelSchema,
        TaggableResourceTypes.MODEL_VERSION: ModelVersionSchema,
        TaggableResourceTypes.PIPELINE: PipelineSchema,
        TaggableResourceTypes.PIPELINE_RUN: PipelineRunSchema,
        TaggableResourceTypes.RUN_TEMPLATE: RunTemplateSchema,
    }

    return resource_type_to_schema_mapping[resource_type]


def get_resource_type_from_schema(
    schema: Type["AnySchema"],
) -> TaggableResourceTypes:
    """Get the resource type from a schema.

    Args:
        schema: The schema of the resource.

    Returns:
        The resource type for the schema.
    """
    from zenml.zen_stores.schemas import (
        ArtifactSchema,
        ArtifactVersionSchema,
        ModelSchema,
        ModelVersionSchema,
        PipelineRunSchema,
        PipelineSchema,
        RunTemplateSchema,
    )

    schema_to_resource_type_mapping = {
        ArtifactSchema: TaggableResourceTypes.ARTIFACT,
        ArtifactVersionSchema: TaggableResourceTypes.ARTIFACT_VERSION,
        ModelSchema: TaggableResourceTypes.MODEL,
        ModelVersionSchema: TaggableResourceTypes.MODEL_VERSION,
        PipelineSchema: TaggableResourceTypes.PIPELINE,
        PipelineRunSchema: TaggableResourceTypes.PIPELINE_RUN,
        RunTemplateSchema: TaggableResourceTypes.RUN_TEMPLATE,
    }
    return schema_to_resource_type_mapping[schema]


@overload
def add_tags(
    tags: List[str],
    singleton: Optional[bool] = None,
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[str],
    run: Union[UUID, str],
    singleton: Optional[bool] = None,
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[str],
    artifact_version_id: UUID,
    singleton: Optional[bool] = None,
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[str],
    artifact_name: str,
    artifact_version: Optional[str] = None,
    singleton: Optional[bool] = None,
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[str],
    infer_artifact: bool = False,
    artifact_name: Optional[str] = None,
    singleton: Optional[bool] = None,
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[str],
    pipeline: Union[UUID, str],
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[str],
    run_template: Union[UUID, str],
    singleton: Optional[bool] = None,
) -> None: ...


def add_tags(
    tags: List[str],
    singleton: Optional[bool] = None,
    # Pipelines
    pipeline: Optional[Union[UUID, str]] = None,
    # Runs
    run: Optional[Union[UUID, str]] = None,
    # Run Templates
    run_template: Optional[Union[UUID, str]] = None,
    # Artifacts
    artifact_version_id: Optional[UUID] = None,
    artifact_name: Optional[str] = None,
    artifact_version: Optional[str] = None,
    infer_artifact: bool = False,
) -> None:
    """Add tags to various resource types in a generalized way.

    Args:
        tags: The tags to add.
        singleton: Whether the tag is a singleton. Only applicable to
            pipeline runs, artifact versions and run templates.
        run: The id, name or prefix of the run.
        artifact_version_id: The ID of the artifact version.
        artifact_name: The name of the artifact.
        artifact_version: The version of the artifact.
        infer_artifact: Flag deciding whether the artifact version should be
            inferred from the step context.
        pipeline: The ID or the name of the pipeline.
        run_template: The ID or the name of the run template.

    Raises:
        ValueError: If no identifiers are provided and the function is not
            called from within a step, or if singleton is provided for a
            resource type that doesn't support it.
    """
    from zenml.client import Client
    from zenml.models.v2.misc.tag import TagResource

    client = Client()
    resource_id = None
    resource_type = None

    # Tag a pipeline
    if pipeline is not None:
        pipeline_model = client.get_pipeline(name_id_or_prefix=pipeline)
        resource_id = pipeline_model.id
        resource_type = TaggableResourceTypes.PIPELINE

    # Tag a run by ID
    elif run is not None:
        run_model = client.get_pipeline_run(name_id_or_prefix=run)
        resource_id = run_model.id
        resource_type = TaggableResourceTypes.PIPELINE_RUN

    # Tag a run template
    elif run_template is not None:
        run_template_model = client.get_run_template(
            name_id_or_prefix=run_template
        )
        resource_id = run_template_model.id
        resource_type = TaggableResourceTypes.RUN_TEMPLATE

    # Tag an artifact version by its name and version
    elif artifact_name is not None and artifact_version is not None:
        artifact_version_model = client.get_artifact_version(
            name_id_or_prefix=artifact_name, version=artifact_version
        )
        resource_id = artifact_version_model.id
        resource_type = TaggableResourceTypes.ARTIFACT_VERSION

    # Tag an artifact version by its ID
    elif artifact_version_id is not None:
        resource_id = artifact_version_id
        resource_type = TaggableResourceTypes.ARTIFACT_VERSION

    # Tag an artifact version through the step context
    elif infer_artifact is True:
        try:
            from zenml.steps.step_context import get_step_context

            step_context = get_step_context()
        except RuntimeError:
            raise ValueError(
                "When you are using the `infer_artifact` option when you call "
                "`add_tags`, it must be called inside a step with outputs."
                "Otherwise, you can provide a `artifact_version_id` or a "
                "combination of `artifact_name` and `artifact_version`."
            )

        step_output_names = list(step_context._outputs.keys())

        if artifact_name is not None:
            # If a name provided, ensure it is in the outputs
            if artifact_name not in step_output_names:
                raise ValueError(
                    f"The provided artifact name`{artifact_name}` does not "
                    f"exist in the step outputs: {step_output_names}."
                )
        else:
            # If no name provided, ensure there is only one output
            if len(step_output_names) > 1:
                raise ValueError(
                    "There is more than one output. If you would like to use "
                    "the `infer_artifact` option, you need to define an "
                    "`artifact_name`."
                )

            if len(step_output_names) == 0:
                raise ValueError("The step does not have any outputs.")

            artifact_name = step_output_names[0]

        step_context.add_output_tags(
            tags=tags,
            output_name=artifact_name,
        )
        return

    # If every additional value is None, that means we are calling it bare bones
    # and this call needs to happen during a step execution. We will use the
    # step context to fetch the run and attach the tags accordingly.
    elif all(
        v is None
        for v in [
            run,
            artifact_version_id,
            artifact_name,
            artifact_version,
            pipeline,
            run_template,
        ]
    ):
        try:
            step_context = get_step_context()
        except RuntimeError:
            raise ValueError(
                """
                You are calling 'add_tags()' outside of a step execution. 
                If you would like to add tags to a ZenML entity outside 
                of the step execution, please provide the required 
                identifiers.
                
                # Automatic tagging to a pipeline run (within a step)
                add_tags(tags=[...])
                
                # Manual tagging to a pipeline run
                add_tags(tags=[...], run_id_name_or_prefix=..., singleton=...)
                
                # Manual tagging to a pipeline
                add_tags(tags=[...], pipeline_id=...)
                
                # Manual tagging to a run template
                add_tags(tags=[...], run_template_id=..., singleton=...)
                
                # Automatic tagging to a model (within a step)
                add_tags(tags=[...], infer_model=True)
                
                # Manual tagging to a model
                add_tags(tags=[...], model_name=..., model_version=...)
                add_tags(tags=[...], model_version_id=...)
                
                # Automatic tagging to an artifact (within a step)
                add_tags(tags=[...], infer_artifact=True, singleton=...)  # step with single output
                add_tags(tags=[...], artifact_name=..., infer_artifact=True, singleton=...)  # specific output of a step
            
                # Manual tagging to an artifact
                add_tags(tags=[...], artifact_name=..., artifact_version=..., singleton=...)
                add_tags(tags=[...], artifact_version_id=..., singleton=...)
                """
            )

        # Tag the pipeline run, not the step
        resource_id = step_context.pipeline_run.id
        resource_type = TaggableResourceTypes.PIPELINE_RUN

    else:
        raise ValueError(
            """
            Unsupported way to call the `add_tags`. Possible combinations "
            include:
            
            # Automatic tagging to a pipeline run (within a step)
            add_tags(tags=[...])
            
            # Manual tagging to a pipeline run
            add_tags(tags=[...], run_id_name_or_prefix=..., singleton=...)
            
            # Manual tagging to a pipeline
            add_tags(tags=[...], pipeline_id=...)
            
            # Manual tagging to a run template
            add_tags(tags=[...], run_template_id=..., singleton=...)
            
            # Automatic tagging to a model (within a step)
            add_tags(tags=[...], infer_model=True)
            
            # Manual tagging to a model
            add_tags(tags=[...], model_name=..., model_version=...)
            add_tags(tags=[...], model_version_id=...)
            
            # Automatic tagging to an artifact (within a step)
            add_tags(tags=[...], infer_artifact=True, singleton=...)  # step with single output
            add_tags(tags=[...], artifact_name=..., infer_artifact=True, singleton=...)  # specific output of a step
            
            # Manual tagging to an artifact
            add_tags(tags=[...], artifact_name=..., artifact_version=..., singleton=...)
            add_tags(tags=[...], artifact_version_id=..., singleton=...)
            """
        )

    # Validate singleton parameter for resource type
    if singleton and resource_type not in [
        TaggableResourceTypes.PIPELINE_RUN,
        TaggableResourceTypes.ARTIFACT_VERSION,
        TaggableResourceTypes.RUN_TEMPLATE,
    ]:
        raise ValueError(
            f"Singleton tags are only applicable to pipeline runs, "
            f"artifact versions and run templates, not {resource_type}."
        )

    # Create tag resources and add tags
    for tag_name in tags:
        try:
            tag_model = client.get_tag(tag_name)

            if singleton != tag_model.singleton:
                raise ValueError(
                    f"The tag `{tag_name}` is a "
                    f"{'singleton' if tag_model.singleton else 'non-singleton'} "
                    "tag. Please update it before attaching it to a resource."
                )

            client.attach_tag(
                tag_name_or_id=tag_model.name,
                resources=[TagResource(id=resource_id, type=resource_type)],
            )

        except KeyError:
            tag_model = client.create_tag(
                name=tag_name,
                singleton=singleton,
            )
            client.attach_tag(
                tag_name_or_id=tag_model.name,
                resources=[TagResource(id=resource_id, type=resource_type)],
            )


@overload
def remove_tags(
    tags: List[str],
) -> None: ...


@overload
def remove_tags(
    *,
    tags: List[str],
    pipeline: Union[UUID, str],
) -> None: ...


@overload
def remove_tags(
    *,
    tags: List[str],
    run: Union[UUID, str],
) -> None: ...


@overload
def remove_tags(
    *,
    tags: List[str],
    run_template: Union[UUID, str],
) -> None: ...


@overload
def remove_tags(
    *,
    tags: List[str],
    artifact_version_id: UUID,
) -> None: ...


@overload
def remove_tags(
    *,
    tags: List[str],
    artifact_name: str,
    artifact_version: Optional[str] = None,
) -> None: ...


@overload
def remove_tags(
    *,
    tags: List[str],
    infer_artifact: bool = False,
    artifact_name: Optional[str] = None,
) -> None: ...


def remove_tags(
    tags: List[str],
    # Pipelines
    pipeline: Optional[Union[UUID, str]] = None,
    # Runs
    run: Optional[Union[UUID, str]] = None,
    # Run Templates
    run_template: Optional[Union[UUID, str]] = None,
    # Artifacts
    artifact_version_id: Optional[UUID] = None,
    artifact_name: Optional[str] = None,
    artifact_version: Optional[str] = None,
    infer_artifact: bool = False,
) -> None:
    """Remove tags from various resource types in a generalized way.

    Args:
        tags: The tags to remove.
        run: The id, name or prefix of the run.
        artifact_version_id: The ID of the artifact version.
        artifact_name: The name of the artifact.
        artifact_version: The version of the artifact.
        infer_artifact: Flag deciding whether the artifact version should be
            inferred from the step context.
        pipeline: The ID or the name of the pipeline.
        run_template: The ID or the name of the run template.

    Raises:
        ValueError: If no identifiers are provided and the function is not
            called from within a step.
    """
    from zenml.client import Client
    from zenml.models.v2.misc.tag import TagResource

    client = Client()
    resource_id = None
    resource_type = None

    # Tag a pipeline
    if pipeline is not None:
        pipeline_model = client.get_pipeline(name_id_or_prefix=pipeline)
        resource_id = pipeline_model.id
        resource_type = TaggableResourceTypes.PIPELINE

    # Tag a run template
    elif run_template is not None:
        run_template_model = client.get_run_template(
            name_id_or_prefix=run_template
        )
        resource_id = run_template_model.id
        resource_type = TaggableResourceTypes.RUN_TEMPLATE

    # Tag a run by ID
    elif run is not None:
        run_model = client.get_pipeline_run(name_id_or_prefix=run)
        resource_id = run_model.id
        resource_type = TaggableResourceTypes.PIPELINE_RUN

    # Tag an artifact version by its name and version
    elif artifact_name is not None and artifact_version is not None:
        artifact_version_model = client.get_artifact_version(
            name_id_or_prefix=artifact_name, version=artifact_version
        )
        resource_id = artifact_version_model.id
        resource_type = TaggableResourceTypes.ARTIFACT_VERSION

    # Tag an artifact version by its ID
    elif artifact_version_id is not None:
        resource_id = artifact_version_id
        resource_type = TaggableResourceTypes.ARTIFACT_VERSION

    # Tag an artifact version through the step context
    elif infer_artifact is True:
        try:
            from zenml.steps.step_context import get_step_context

            step_context = get_step_context()
        except RuntimeError:
            raise ValueError(
                "When you are using the `infer_artifact` option when you call "
                "`remove_tags`, it must be called inside a step with outputs."
                "Otherwise, you can provide a `artifact_version_id` or a "
                "combination of `artifact_name` and `artifact_version`."
            )

        step_output_names = list(step_context._outputs.keys())

        if artifact_name is not None:
            # If a name provided, ensure it is in the outputs
            if artifact_name not in step_output_names:
                raise ValueError(
                    f"The provided artifact name`{artifact_name}` does not "
                    f"exist in the step outputs: {step_output_names}."
                )
        else:
            # If no name provided, ensure there is only one output
            if len(step_output_names) > 1:
                raise ValueError(
                    "There is more than one output. If you would like to use "
                    "the `infer_artifact` option, you need to define an "
                    "`artifact_name`."
                )

            if len(step_output_names) == 0:
                raise ValueError("The step does not have any outputs.")

            artifact_name = step_output_names[0]

        step_context.remove_output_tags(
            tags=tags,
            artifact_name=artifact_name,
        )
        return

    # If every additional value is None, that means we are calling it bare bones
    # and this call needs to happen during a step execution. We will use the
    # step context to fetch the run and attach the tags accordingly.
    elif all(
        v is None
        for v in [
            run,
            artifact_version_id,
            artifact_name,
            artifact_version,
            pipeline,
            run_template,
        ]
    ):
        try:
            from zenml.steps.step_context import get_step_context

            step_context = get_step_context()
        except RuntimeError:
            raise ValueError(
                """
                You are calling 'remove_tags()' outside of a step execution. 
                If you would like to remove tags from a ZenML entity outside 
                of the step execution, please provide the required 
                identifiers.
                
                # Automatic tag removal from a pipeline run (within a step)
                remove_tags(tags=[...])
                
                # Manual tag removal from a pipeline run
                remove_tags(tags=[...], run_id_name_or_prefix=...)
                
                # Manual tag removal from a pipeline
                remove_tags(tags=[...], pipeline_id=...)
                
                # Manual tag removal from a run template
                remove_tags(tags=[...], run_template_id=...)
                
                # Automatic tag removal from a model (within a step)
                remove_tags(tags=[...], infer_model=True)
                
                # Manual tag removal from a model
                remove_tags(tags=[...], model_name=..., model_version=...)
                remove_tags(tags=[...], model_version_id=...)
                
                # Automatic tag removal from an artifact (within a step)
                remove_tags(tags=[...], infer_artifact=True)  # step with single output
                remove_tags(tags=[...], artifact_name=..., infer_artifact=True)  # specific output of a step
            
                # Manual tag removal from an artifact
                remove_tags(tags=[...], artifact_name=..., artifact_version=...)
                remove_tags(tags=[...], artifact_version_id=...)
                """
            )

        # Tag the pipeline run, not the step
        resource_id = step_context.pipeline_run.id
        resource_type = TaggableResourceTypes.PIPELINE_RUN

    else:
        raise ValueError(
            """
            Unsupported way to call the `remove_tags`. Possible combinations "
            include:
            
            # Automatic tag removal from a pipeline run (within a step)
            remove_tags(tags=[...])
            
            # Manual tag removal from a pipeline run
            remove_tags(tags=[...], run_id_name_or_prefix=...)
            
            # Manual tag removal from a pipeline
            remove_tags(tags=[...], pipeline_id=...)
            
            # Manual tag removal from a run template
            remove_tags(tags=[...], run_template_id=...)
            
            # Automatic tag removal from a model (within a step)
            remove_tags(tags=[...], infer_model=True)
            
            # Manual tag removal from a model
            remove_tags(tags=[...], model_name=..., model_version=...)
            remove_tags(tags=[...], model_version_id=...)
            
            # Automatic tag removal from an artifact (within a step)
            remove_tags(tags=[...], infer_artifact=True)  # step with single output
            remove_tags(tags=[...], artifact_name=..., infer_artifact=True)  # specific output of a step
            
            # Manual tag removal from an artifact
            remove_tags(tags=[...], artifact_name=..., artifact_version=...)
            remove_tags(tags=[...], artifact_version_id=...)
            """
        )

    # Remove tags from resource
    for tag_name in tags:
        try:
            # Get the tag
            tag = client.get_tag(tag_name)

            # Detach tag from resources
            client.detach_tag(
                tag_name_or_id=tag.id,
                resources=[TagResource(id=resource_id, type=resource_type)],
            )

        except KeyError:
            # Tag doesn't exist, nothing to remove
            pass
