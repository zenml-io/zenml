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
    List,
    Optional,
    TypeVar,
    Union,
    overload,
)
from uuid import UUID

from pydantic import BaseModel

from zenml.enums import ColorVariants, TaggableResourceTypes
from zenml.logger import get_logger

add_tags_warning = """
# Automatic tagging to a pipeline run (within a step)
add_tags(tags=[...])

# Manual tagging to a pipeline run
add_tags(tags=[...], run=...)

# Manual tagging to a pipeline
add_tags(tags=[...], pipeline=...)

# Manual tagging to a run template
add_tags(tags=[...], run_template=...)

# Manual tagging to an artifact
add_tags(tags=[...], artifact=...)

# Automatic tagging to an artifact version(within a step)
add_tags(tags=[...], infer_artifact=True)  # step with single output
add_tags(tags=[...], artifact_name=..., infer_artifact=True)  # specific output of a step

# Manual tagging to an artifact version
add_tags(tags=[...], artifact_name=..., artifact_version=...)
add_tags(tags=[...], artifact_version_id=...)
"""

remove_tags_warning = """
# Automatic tag removal from a pipeline run (within a step)
remove_tags(tags=[...])

# Manual tag removal from a pipeline run
remove_tags(tags=[...], run=...)

# Manual tag removal from a pipeline
remove_tags(tags=[...], pipeline=...)

# Manual tag removal from a run template
remove_tags(tags=[...], run_template=...)

# Manual tag removal from an artifact
remove_tags(tags=[...], artifact=...)

# Automatic tag removal from an artifact version (within a step)
remove_tags(tags=[...], infer_artifact=True)  # step with single output
remove_tags(tags=[...], artifact_name=..., infer_artifact=True)  # specific output of a step

# Manual tag removal from an artifact version
remove_tags(tags=[...], artifact_name=..., artifact_version=...)
remove_tags(tags=[...], artifact_version_id=...)
"""


if TYPE_CHECKING:
    from zenml.models import TagRequest
    from zenml.zen_stores.schemas.base_schemas import BaseSchema

    AnySchema = TypeVar("AnySchema", bound=BaseSchema)

logger = get_logger(__name__)


class Tag(BaseModel):
    """A model representing a tag."""

    name: str
    color: Optional[ColorVariants] = None
    exclusive: Optional[bool] = None
    cascade: Optional[bool] = None

    def to_request(self) -> "TagRequest":
        """Convert the tag to a TagRequest.

        Returns:
            The tag as a TagRequest.
        """
        from zenml.models import TagRequest

        request = TagRequest(name=self.name)
        if self.color is not None:
            request.color = self.color

        if self.exclusive is not None:
            request.exclusive = self.exclusive
        return request


@overload
def add_tags(
    tags: List[Union[str, Tag]],
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[Union[str, Tag]],
    run: Union[UUID, str],
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[Union[str, Tag]],
    artifact: Union[UUID, str],
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[Union[str, Tag]],
    artifact_version_id: UUID,
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[Union[str, Tag]],
    artifact_name: str,
    artifact_version: Optional[str] = None,
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[Union[str, Tag]],
    infer_artifact: bool = False,
    artifact_name: Optional[str] = None,
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[Union[str, Tag]],
    pipeline: Union[UUID, str],
) -> None: ...


@overload
def add_tags(
    *,
    tags: List[Union[str, Tag]],
    run_template: Union[UUID, str],
) -> None: ...


def add_tags(
    tags: List[Union[str, Tag]],
    # Pipelines
    pipeline: Optional[Union[UUID, str]] = None,
    # Runs
    run: Optional[Union[UUID, str]] = None,
    # Run Templates
    run_template: Optional[Union[UUID, str]] = None,
    # Artifacts
    artifact: Optional[Union[UUID, str]] = None,
    # Artifact Versions
    artifact_version_id: Optional[UUID] = None,
    artifact_name: Optional[str] = None,
    artifact_version: Optional[str] = None,
    infer_artifact: bool = False,
) -> None:
    """Add tags to various resource types in a generalized way.

    Args:
        tags: The tags to add.
        pipeline: The ID or the name of the pipeline.
        run: The id, name or prefix of the run.
        run_template: The ID or the name of the run template.
        artifact: The ID or the name of the artifact.
        artifact_version_id: The ID of the artifact version.
        artifact_name: The name of the artifact.
        artifact_version: The version of the artifact.
        infer_artifact: Flag deciding whether the artifact version should be
            inferred from the step context.

    Raises:
        ValueError: If no identifiers are provided and the function is not
            called from within a step, or if exclusive is provided for a
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

    # Tag an artifact
    elif artifact is not None:
        artifact_model = client.get_artifact(name_id_or_prefix=artifact)
        resource_id = artifact_model.id
        resource_type = TaggableResourceTypes.ARTIFACT

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
        resource_type = TaggableResourceTypes.ARTIFACT_VERSION

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
            tags=[t.name if isinstance(t, Tag) else t for t in tags],
            output_name=artifact_name,
        )

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
                f"""
                You are calling 'add_tags()' outside of a step execution. 
                If you would like to add tags to a ZenML entity outside 
                of the step execution, please provide the required 
                identifiers.\n{add_tags_warning}
                """
            )

        # Tag the pipeline run, not the step
        resource_id = step_context.pipeline_run.id
        resource_type = TaggableResourceTypes.PIPELINE_RUN

    else:
        raise ValueError(
            f"""
            Unsupported way to call the `add_tags`. Possible combinations "
            include: \n{add_tags_warning}
            """
        )

    # Create tag resources and add tags
    for tag in tags:
        try:
            if isinstance(tag, Tag):
                tag_model = client.get_tag(tag.name)

                if bool(tag.exclusive) != tag_model.exclusive:
                    raise ValueError(
                        f"The tag `{tag.name}` is "
                        f"{'an exclusive' if tag_model.exclusive else 'a non-exclusive'} "
                        "tag. Please update it before attaching it to a resource."
                    )
                if tag.cascade is not None:
                    raise ValueError(
                        "Cascading tags can only be used with the "
                        "pipeline decorator."
                    )
            else:
                tag_model = client.get_tag(tag)

        except KeyError:
            if isinstance(tag, Tag):
                tag_model = client.create_tag(
                    name=tag.name,
                    exclusive=tag.exclusive
                    if tag.exclusive is not None
                    else False,
                )

                if tag.cascade is not None:
                    raise ValueError(
                        "Cascading tags can only be used with the "
                        "pipeline decorator."
                    )
            else:
                tag_model = client.create_tag(name=tag)

        if resource_id:
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
    artifact: Union[UUID, str],
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
    artifact: Optional[Union[UUID, str]] = None,
    # Artifact Versions
    artifact_version_id: Optional[UUID] = None,
    artifact_name: Optional[str] = None,
    artifact_version: Optional[str] = None,
    infer_artifact: bool = False,
) -> None:
    """Remove tags from various resource types in a generalized way.

    Args:
        tags: The tags to remove.
        pipeline: The ID or the name of the pipeline.
        run: The id, name or prefix of the run.
        run_template: The ID or the name of the run template.
        artifact: The ID or the name of the artifact.
        artifact_version_id: The ID of the artifact version.
        artifact_name: The name of the artifact.
        artifact_version: The version of the artifact.
        infer_artifact: Flag deciding whether the artifact version should be
            inferred from the step context.

    Raises:
        ValueError: If no identifiers are provided and the function is not
            called from within a step.
    """
    from zenml.client import Client
    from zenml.models.v2.misc.tag import TagResource

    client = Client()
    resource_id = None
    resource_type = None

    # Remove tags from a pipeline
    if pipeline is not None:
        pipeline_model = client.get_pipeline(name_id_or_prefix=pipeline)
        resource_id = pipeline_model.id
        resource_type = TaggableResourceTypes.PIPELINE

    # Remove tags from a run template
    elif run_template is not None:
        run_template_model = client.get_run_template(
            name_id_or_prefix=run_template
        )
        resource_id = run_template_model.id
        resource_type = TaggableResourceTypes.RUN_TEMPLATE

    # Remove tags from a run
    elif run is not None:
        run_model = client.get_pipeline_run(name_id_or_prefix=run)
        resource_id = run_model.id
        resource_type = TaggableResourceTypes.PIPELINE_RUN

    # Remove tags from an artifact
    elif artifact is not None:
        artifact_model = client.get_artifact(name_id_or_prefix=artifact)
        resource_id = artifact_model.id
        resource_type = TaggableResourceTypes.ARTIFACT

    # Remove tags from an artifact version by its name and version
    elif artifact_name is not None and artifact_version is not None:
        artifact_version_model = client.get_artifact_version(
            name_id_or_prefix=artifact_name, version=artifact_version
        )
        resource_id = artifact_version_model.id
        resource_type = TaggableResourceTypes.ARTIFACT_VERSION

    # Remove tags from an artifact version by its ID
    elif artifact_version_id is not None:
        resource_id = artifact_version_id
        resource_type = TaggableResourceTypes.ARTIFACT_VERSION

    # Remove tags from an artifact version through the step context
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
            output_name=artifact_name,
        )
        return

    # If every additional value is None, that means we are calling it bare bones
    # and this call needs to happen during a step execution. We will use the
    # step context to fetch the run and detach the tags accordingly.
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
                f"""
                You are calling 'remove_tags()' outside of a step execution. 
                If you would like to remove tags from a ZenML entity outside 
                of the step execution, please provide the required 
                identifiers. \n{remove_tags_warning}
                """
            )

        # Tag the pipeline run, not the step
        resource_id = step_context.pipeline_run.id
        resource_type = TaggableResourceTypes.PIPELINE_RUN

    else:
        raise ValueError(
            f"""
            Unsupported way to call the `remove_tags`. Possible combinations "
            include: \n{remove_tags_warning}
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
