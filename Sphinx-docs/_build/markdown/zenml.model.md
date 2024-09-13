# zenml.model package

## Submodules

## zenml.model.lazy_load module

Model Version Data Lazy Loader definition.

### *class* zenml.model.lazy_load.ModelVersionDataLazyLoader(\*, model: [Model](#zenml.model.model.Model), artifact_name: str | None = None, artifact_version: str | None = None, metadata_name: str | None = None)

Bases: `BaseModel`

Model Version Data Lazy Loader helper class.

It helps the inner codes to fetch proper artifact,
model version metadata or artifact metadata from the
model version during runtime time of the step.

#### artifact_name *: str | None*

#### artifact_version *: str | None*

#### metadata_name *: str | None*

#### model *: [Model](#zenml.model.model.Model)*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'artifact_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'artifact_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'metadata_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'model': FieldInfo(annotation=Model, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

## zenml.model.model module

Model user facing interface to pass into pipeline or step.

### *class* zenml.model.model.Model(\*, name: str, license: str | None = None, description: str | None = None, audience: str | None = None, use_cases: str | None = None, limitations: str | None = None, trade_offs: str | None = None, ethics: str | None = None, tags: List[str] | None = None, version: Annotated[[ModelStages](zenml.md#zenml.enums.ModelStages) | int | str | None, \_PydanticGeneralMetadata(union_mode='smart')] = None, save_models_to_registry: bool = True, model_version_id: UUID | None = None, suppress_class_validation_warnings: bool = False, was_created_in_this_run: bool = False)

Bases: `BaseModel`

Model class to pass into pipeline or step to set it into a model context.

name: The name of the model.
license: The license under which the model is created.
description: The description of the model.
audience: The target audience of the model.
use_cases: The use cases of the model.
limitations: The known limitations of the model.
trade_offs: The tradeoffs of the model.
ethics: The ethical implications of the model.
tags: Tags associated with the model.
version: The version name, version number or stage is optional and points model context

> to a specific version/stage. If skipped new version will be created.

save_models_to_registry: Whether to save all ModelArtifacts to Model Registry,
: if available in active stack.

model_version_id: The ID of a specific Model Version, if given - it will override
: name and version settings. Used mostly internally.

#### audience *: str | None*

#### delete_all_artifacts(only_link: bool = True, delete_from_artifact_store: bool = False) → None

Delete all artifacts linked to this model version.

Args:
: only_link: Whether to only delete the link to the artifact.
  delete_from_artifact_store: Whether to delete the artifact from
  <br/>
  > the artifact store.

#### delete_artifact(name: str, version: str | None = None, only_link: bool = True, delete_metadata: bool = True, delete_from_artifact_store: bool = False) → None

Delete the artifact linked to this model version.

Args:
: name: The name of the artifact to delete.
  version: The version of the artifact to delete (None for
  <br/>
  > latest/non-versioned)
  <br/>
  only_link: Whether to only delete the link to the artifact.
  delete_metadata: Whether to delete the metadata of the artifact.
  delete_from_artifact_store: Whether to delete the artifact from the
  <br/>
  > artifact store.

#### description *: str | None*

#### ethics *: str | None*

#### get_artifact(name: str, version: str | None = None) → [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse) | None

Get the artifact linked to this model version.

Args:
: name: The name of the artifact to retrieve.
  version: The version of the artifact to retrieve (None for
  <br/>
  > latest/non-versioned)

Returns:
: Specific version of the artifact or placeholder in the design time
  : of the pipeline.

#### get_data_artifact(name: str, version: str | None = None) → [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse) | None

Get the data artifact linked to this model version.

Args:
: name: The name of the data artifact to retrieve.
  version: The version of the data artifact to retrieve (None for
  <br/>
  > latest/non-versioned)

Returns:
: Specific version of the data artifact or placeholder in the design
  time of the pipeline.

#### get_deployment_artifact(name: str, version: str | None = None) → [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse) | None

Get the deployment artifact linked to this model version.

Args:
: name: The name of the deployment artifact to retrieve.
  version: The version of the deployment artifact to retrieve (None
  <br/>
  > for latest/non-versioned)

Returns:
: Specific version of the deployment artifact or placeholder in the
  design time of the pipeline.

#### get_model_artifact(name: str, version: str | None = None) → [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse) | None

Get the model artifact linked to this model version.

Args:
: name: The name of the model artifact to retrieve.
  version: The version of the model artifact to retrieve (None for
  <br/>
  > latest/non-versioned)

Returns:
: Specific version of the model artifact or placeholder in the design
  : time of the pipeline.

#### get_pipeline_run(name: str) → [PipelineRunResponse](zenml.models.md#zenml.models.PipelineRunResponse)

Get pipeline run linked to this version.

Args:
: name: The name of the pipeline run to retrieve.

Returns:
: PipelineRun as PipelineRunResponse

#### *property* id *: UUID*

Get version id from the Model Control Plane.

Returns:
: ID of the model version or None, if model version
  : doesn’t exist and can only be read given current
    config (you used stage name or number as
    a version name).

Raises:
: RuntimeError: if model version doesn’t exist and
  : cannot be fetched from the Model Control Plane.

#### license *: str | None*

#### limitations *: str | None*

#### load_artifact(name: str, version: str | None = None) → Any

Load artifact from the Model Control Plane.

Args:
: name: Name of the artifact to load.
  version: Version of the artifact to load.

Returns:
: The loaded artifact.

Raises:
: ValueError: if the model version is not linked to any artifact with
  : the given name and version.

#### log_metadata(metadata: Dict[str, MetadataType]) → None

Log model version metadata.

This function can be used to log metadata for current model version.

Args:
: metadata: The metadata to log.

#### *property* metadata *: Dict[str, MetadataType]*

DEPRECATED, use run_metadata instead.

Returns:
: The model version run metadata.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'audience': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'ethics': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'license': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'limitations': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'model_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'name': FieldInfo(annotation=str, required=True), 'save_models_to_registry': FieldInfo(annotation=bool, required=False, default=True), 'suppress_class_validation_warnings': FieldInfo(annotation=bool, required=False, default=False), 'tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None), 'trade_offs': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'use_cases': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'version': FieldInfo(annotation=Union[ModelStages, int, str, NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='smart')]), 'was_created_in_this_run': FieldInfo(annotation=bool, required=False, default=False)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### *property* model_id *: UUID*

Get model id from the Model Control Plane.

Returns:
: The UUID of the model containing this model version.

#### model_post_init(context: Any, /) → None

This function is meant to behave like a BaseModel method to initialise private attributes.

It takes context as an argument since that’s what pydantic-core passes when calling it.

Args:
: self: The BaseModel instance.
  context: The context.

#### model_version_id *: UUID | None*

#### name *: str*

#### *property* number *: int*

Get version number from  the Model Control Plane.

Returns:
: Number of the model version or None, if model version
  : doesn’t exist and can only be read given current
    config (you used stage name or number as
    a version name).

#### *property* run_metadata *: Dict[str, [RunMetadataResponse](zenml.models.md#zenml.models.RunMetadataResponse)]*

Get model version run metadata.

Returns:
: The model version run metadata.

Raises:
: RuntimeError: If the model version run metadata cannot be fetched.

#### save_models_to_registry *: bool*

#### set_stage(stage: str | [ModelStages](zenml.md#zenml.enums.ModelStages), force: bool = False) → None

Sets this Model to a desired stage.

Args:
: stage: the target stage for model version.
  force: whether to force archiving of current model version in
  <br/>
  > target stage or raise.

#### *property* stage *: [ModelStages](zenml.md#zenml.enums.ModelStages) | None*

Get version stage from  the Model Control Plane.

Returns:
: Stage of the model version or None, if model version
  : doesn’t exist and can only be read given current
    config (you used stage name or number as
    a version name).

#### suppress_class_validation_warnings *: bool*

#### tags *: List[str] | None*

#### trade_offs *: str | None*

#### use_cases *: str | None*

#### version *: [ModelStages](zenml.md#zenml.enums.ModelStages) | int | str | None*

#### was_created_in_this_run *: bool*

## zenml.model.model_version module

DEPRECATED, use from zenml import Model instead.

### *class* zenml.model.model_version.ModelVersion(\*args: Any, name: str, license: str | None = None, description: str | None = None, audience: str | None = None, use_cases: str | None = None, limitations: str | None = None, trade_offs: str | None = None, ethics: str | None = None, tags: List[str] | None = None, version: Annotated[[ModelStages](zenml.md#zenml.enums.ModelStages) | int | str | None, \_PydanticGeneralMetadata(union_mode='smart')] = None, save_models_to_registry: bool = True, model_version_id: UUID | None = None, suppress_class_validation_warnings: bool = False, was_created_in_this_run: bool = False)

Bases: [`Model`](#zenml.model.model.Model)

DEPRECATED, use from zenml import Model instead.

#### audience *: str | None*

#### description *: str | None*

#### ethics *: str | None*

#### license *: str | None*

#### limitations *: str | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'audience': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'ethics': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'license': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'limitations': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'model_version_id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'name': FieldInfo(annotation=str, required=True), 'save_models_to_registry': FieldInfo(annotation=bool, required=False, default=True), 'suppress_class_validation_warnings': FieldInfo(annotation=bool, required=False, default=False), 'tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None), 'trade_offs': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'use_cases': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'version': FieldInfo(annotation=Union[ModelStages, int, str, NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='smart')]), 'was_created_in_this_run': FieldInfo(annotation=bool, required=False, default=False)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### model_version_id *: UUID | None*

#### name *: str*

#### save_models_to_registry *: bool*

#### suppress_class_validation_warnings *: bool*

#### tags *: List[str] | None*

#### trade_offs *: str | None*

#### use_cases *: str | None*

#### version *: [ModelStages](zenml.md#zenml.enums.ModelStages) | int | str | None*

#### was_created_in_this_run *: bool*

## zenml.model.utils module

Utility functions for linking step outputs to model versions.

### zenml.model.utils.link_artifact_config_to_model(artifact_config: [ArtifactConfig](zenml.artifacts.md#zenml.artifacts.artifact_config.ArtifactConfig), artifact_version_id: UUID, model: [Model](#zenml.model.model.Model) | None = None) → None

Link an artifact config to its model version.

Args:
: artifact_config: The artifact config to link.
  artifact_version_id: The ID of the artifact to link.
  model: The model version from the step or pipeline context.

### zenml.model.utils.link_artifact_to_model(artifact_version_id: UUID, model: [Model](#zenml.model.model.Model) | None = None, is_model_artifact: bool = False, is_deployment_artifact: bool = False) → None

Link the artifact to the model.

Args:
: artifact_version_id: The ID of the artifact version.
  model: The model to link to.
  is_model_artifact: Whether the artifact is a model artifact.
  is_deployment_artifact: Whether the artifact is a deployment artifact.

Raises:
: RuntimeError: If called outside of a step.

### zenml.model.utils.link_service_to_model(service_id: UUID, model: [Model](#zenml.model.model.Model) | None = None, model_version_id: UUID | None = None) → None

Links a service to a model.

Args:
: service_id: The ID of the service to link to the model.
  model: The model to link the service to.
  model_version_id: The ID of the model version to link the service to.

Raises:
: RuntimeError: If no model is provided and the model context cannot be
  : identified.

### zenml.model.utils.link_step_artifacts_to_model(artifact_version_ids: Dict[str, UUID]) → None

Links the output artifacts of a step to the model.

Args:
: artifact_version_ids: The IDs of the published output artifacts.

Raises:
: RuntimeError: If called outside of a step.

### zenml.model.utils.log_model_metadata(metadata: Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)], model_name: str | None = None, model_version: [ModelStages](zenml.md#zenml.enums.ModelStages) | str | int | None = None) → None

Log model version metadata.

This function can be used to log metadata for existing model versions.

Args:
: metadata: The metadata to log.
  model_name: The name of the model to log metadata for. Can
  <br/>
  > be omitted when being called inside a step with configured
  > model in decorator.
  <br/>
  model_version: The version of the model to log metadata for. Can
  : be omitted when being called inside a step with configured
    model in decorator.

Raises:
: ValueError: If no model name/version is provided and the function is not
  : called inside a step with configured model in decorator.

### zenml.model.utils.log_model_version_metadata(metadata: Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)], model_name: str | None = None, model_version: [ModelStages](zenml.md#zenml.enums.ModelStages) | str | int | None = None) → None

Log model version metadata.

This function can be used to log metadata for existing model versions.

Args:
: metadata: The metadata to log.
  model_name: The name of the model to log metadata for. Can
  <br/>
  > be omitted when being called inside a step with configured
  > model in decorator.
  <br/>
  model_version: The version of the model to log metadata for. Can
  : be omitted when being called inside a step with configured
    model in decorator.

## Module contents

Concepts related to the Model Control Plane feature.
