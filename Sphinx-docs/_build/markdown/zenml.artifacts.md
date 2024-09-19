# zenml.artifacts package

## Submodules

## zenml.artifacts.artifact_config module

Artifact Config classes to support Model Control Plane feature.

### *class* zenml.artifacts.artifact_config.ArtifactConfig(\*, name: str | None = None, version: Annotated[int | str | None, \_PydanticGeneralMetadata(union_mode='smart')] = None, tags: List[str] | None = None, run_metadata: Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)] | None = None, model_name: str | None = None, model_version: Annotated[[ModelStages](zenml.md#zenml.enums.ModelStages) | str | int | None, \_PydanticGeneralMetadata(union_mode='smart')] = None, is_model_artifact: bool = False, is_deployment_artifact: bool = False)

Bases: `BaseModel`

Artifact configuration class.

Can be used in step definitions to define various artifact properties.

Example:

```
``
```

```
`
```

python
@step
def my_step() -> Annotated[

> int, ArtifactConfig(
> : name=”my_artifact”,  # override the default artifact name
>   version=42,  # set a custom version
>   tags=[“tag1”, “tag2”],  # set custom tags
>   model_name=”my_model”,  # link the artifact to a model

> )

]:
: return …

```
``
```

```
`
```

Attributes:
: name: The name of the artifact.
  version: The version of the artifact.
  tags: The tags of the artifact.
  model_name: The name of the model to link artifact to.
  model_version: The identifier of a version of the model to link the artifact
  <br/>
  > to. It can be an exact version (“my_version”), exact version number
  > (42), stage (ModelStages.PRODUCTION or “production”), or
  > (ModelStages.LATEST or None) for the latest version (default).
  <br/>
  is_model_artifact: Whether the artifact is a model artifact.
  is_deployment_artifact: Whether the artifact is a deployment artifact.

#### artifact_config_validator() → [ArtifactConfig](#zenml.artifacts.artifact_config.ArtifactConfig)

Model validator for the artifact config.

Raises:
: ValueError: If both model_name and model_version is set incorrectly.

Returns:
: the validated instance.

#### is_deployment_artifact *: bool*

#### is_model_artifact *: bool*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'is_deployment_artifact': FieldInfo(annotation=bool, required=False, default=False), 'is_model_artifact': FieldInfo(annotation=bool, required=False, default=False), 'model_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'model_version': FieldInfo(annotation=Union[ModelStages, str, int, NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='smart')]), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'run_metadata': FieldInfo(annotation=Union[Dict[str, Union[str, int, float, bool, Dict[Any, Any], List[Any], Set[Any], Tuple[Any, ...], Uri, Path, DType, StorageSize]], NoneType], required=False, default=None), 'tags': FieldInfo(annotation=Union[List[str], NoneType], required=False, default=None), 'version': FieldInfo(annotation=Union[int, str, NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='smart')])}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_name *: str | None*

#### model_version *: [ModelStages](zenml.md#zenml.enums.ModelStages) | str | int | None*

#### name *: str | None*

#### run_metadata *: Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)] | None*

#### tags *: List[str] | None*

#### version *: int | str | None*

## zenml.artifacts.external_artifact module

External artifact definition.

### *class* zenml.artifacts.external_artifact.ExternalArtifact(\*, id: UUID | None = None, name: str | None = None, version: str | None = None, model: [Model](zenml.model.md#zenml.model.model.Model) | None = None, value: Any | None = None, materializer: Annotated[str | [Source](zenml.config.md#zenml.config.source.Source) | Type[[BaseMaterializer](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)] | None, \_PydanticGeneralMetadata(union_mode='left_to_right')] = None, store_artifact_metadata: bool = True, store_artifact_visualizations: bool = True)

Bases: [`ExternalArtifactConfiguration`](#zenml.artifacts.external_artifact_config.ExternalArtifactConfiguration)

External artifacts can be used to provide values as input to ZenML steps.

ZenML steps accept either artifacts (=outputs of other steps), parameters
(raw, JSON serializable values) or external artifacts. External artifacts
can be used to provide any value as input to a step without needing to
write an additional step that returns this value.

The external artifact needs to have either a value associated with it
that will be uploaded to the artifact store, or reference an artifact
that is already registered in ZenML.

There are several ways to reference an existing artifact:
- By providing an artifact ID.
- By providing an artifact name and version. If no version is provided,

> the latest version of that artifact will be used.

Args:
: value: The artifact value.
  id: The ID of an artifact that should be referenced by this external
  <br/>
  > artifact.
  <br/>
  materializer: The materializer to use for saving the artifact value
  : to the artifact store. Only used when value is provided.
  <br/>
  store_artifact_metadata: Whether metadata for the artifact should
  : be stored. Only used when value is provided.
  <br/>
  store_artifact_visualizations: Whether visualizations for the
  : artifact should be stored. Only used when value is provided.

Example:

```
``
```

\`
from zenml import step, pipeline
from zenml.artifacts.external_artifact import ExternalArtifact
import numpy as np

@step
def my_step(value: np.ndarray) -> None:

> print(value)

my_array = np.array([1, 2, 3])

@pipeline
def my_pipeline():

> my_step(value=ExternalArtifact(my_array))

```
``
```

```
`
```

#### *property* config *: [ExternalArtifactConfiguration](#zenml.artifacts.external_artifact_config.ExternalArtifactConfiguration)*

Returns the lightweight config without hard for JSON properties.

Returns:
: The config object to be evaluated in runtime by step interface.

#### external_artifact_validator() → [ExternalArtifact](#zenml.artifacts.external_artifact.ExternalArtifact)

Model validator for the external artifact.

Raises:
: ValueError: if the value, id and name fields are set incorrectly.

Returns:
: the validated instance.

#### id *: UUID | None*

#### materializer *: str | [Source](zenml.config.md#zenml.config.source.Source) | Type[[BaseMaterializer](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)] | None*

#### model *: [Model](zenml.md#zenml.Model) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'materializer': FieldInfo(annotation=Union[str, Source, Type[BaseMaterializer], NoneType], required=False, default=None, metadata=[_PydanticGeneralMetadata(union_mode='left_to_right')]), 'model': FieldInfo(annotation=Union[Model, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'store_artifact_metadata': FieldInfo(annotation=bool, required=False, default=True), 'store_artifact_visualizations': FieldInfo(annotation=bool, required=False, default=True), 'value': FieldInfo(annotation=Union[Any, NoneType], required=False, default=None), 'version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### store_artifact_metadata *: bool*

#### store_artifact_visualizations *: bool*

#### upload_by_value() → UUID

Uploads the artifact by value.

Returns:
: The uploaded artifact ID.

#### value *: Any | None*

#### version *: str | None*

## zenml.artifacts.external_artifact_config module

External artifact definition.

### *class* zenml.artifacts.external_artifact_config.ExternalArtifactConfiguration(\*, id: UUID | None = None, name: str | None = None, version: str | None = None, model: [Model](zenml.model.md#zenml.model.model.Model) | None = None)

Bases: `BaseModel`

External artifact configuration.

Lightweight class to pass in the steps for runtime inference.

#### external_artifact_validator() → [ExternalArtifactConfiguration](#zenml.artifacts.external_artifact_config.ExternalArtifactConfiguration)

Model validator for the external artifact configuration.

Raises:
: ValueError: if both version and model fields are set.

Returns:
: the validated instance.

#### get_artifact_version_id() → UUID

Get the artifact.

Returns:
: The artifact ID.

Raises:
: RuntimeError: If the artifact store of the referenced artifact
  : is not the same as the one in the active stack.
  <br/>
  RuntimeError: If neither the ID nor the name of the artifact was
  : provided.

#### id *: UUID | None*

#### model *: [Model](zenml.model.md#zenml.model.model.Model) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'id': FieldInfo(annotation=Union[UUID, NoneType], required=False, default=None), 'model': FieldInfo(annotation=Union[Model, NoneType], required=False, default=None), 'name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str | None*

#### version *: str | None*

## zenml.artifacts.unmaterialized_artifact module

Unmaterialized artifact class.

### *class* zenml.artifacts.unmaterialized_artifact.UnmaterializedArtifact(\*, body: [ArtifactVersionResponseBody](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponseBody) | None = None, metadata: [ArtifactVersionResponseMetadata](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponseMetadata) | None = None, resources: [ArtifactVersionResponseResources](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponseResources) | None = None, id: UUID, permission_denied: bool = False)

Bases: [`ArtifactVersionResponse`](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)

Unmaterialized artifact class.

Typing a step input to have this type will cause ZenML to not materialize
the artifact. This is useful for steps that need to access the artifact
metadata instead of the actual artifact data.

Usage example:

```
``
```

```
`
```

python
from zenml import step
from zenml.artifacts.unmaterialized_artifact import UnmaterializedArtifact

@step
def my_step(input_artifact: UnmaterializedArtifact):

> print(input_artifact.uri)

```
``
```

```
`
```

#### id *: UUID*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'ignore'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'body': FieldInfo(annotation=Union[ArtifactVersionResponseBody, NoneType], required=False, default=None, title='The body of the resource.'), 'id': FieldInfo(annotation=UUID, required=True, title='The unique resource id.'), 'metadata': FieldInfo(annotation=Union[ArtifactVersionResponseMetadata, NoneType], required=False, default=None, title='The metadata related to this resource.'), 'permission_denied': FieldInfo(annotation=bool, required=False, default=False), 'resources': FieldInfo(annotation=Union[ArtifactVersionResponseResources, NoneType], required=False, default=None, title='The resources related to this resource.')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_post_init(context: Any, /) → None

We need to both initialize private attributes and call the user-defined model_post_init
method.

#### permission_denied *: bool*

## zenml.artifacts.utils module

Utility functions for handling artifacts.

### zenml.artifacts.utils.download_artifact_files_from_response(artifact: [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse), path: str, overwrite: bool = False) → None

Download the given artifact into a file.

Args:
: artifact: The artifact to download.
  path: The path to which to download the artifact.
  overwrite: Whether to overwrite the file if it already exists.

Raises:
: FileExistsError: If the file already exists and overwrite is False.
  Exception: If the artifact could not be downloaded to the zip file.

### zenml.artifacts.utils.get_artifacts_versions_of_pipeline_run(pipeline_run: [PipelineRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.pipeline_run.PipelineRunResponse), only_produced: bool = False) → List[[ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)]

Get all artifact versions produced during a pipeline run.

Args:
: pipeline_run: The pipeline run.
  only_produced: If only artifact versions produced by the pipeline run
  <br/>
  > should be returned or also cached artifact versions.

Returns:
: A list of all artifact versions produced during the pipeline run.

### zenml.artifacts.utils.get_producer_step_of_artifact(artifact: [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)) → [StepRunResponse](zenml.models.v2.core.md#zenml.models.v2.core.step_run.StepRunResponse)

Get the step run that produced a given artifact.

Args:
: artifact: The artifact.

Returns:
: The step run that produced the artifact.

Raises:
: RuntimeError: If the run that created the artifact no longer exists.

### zenml.artifacts.utils.load_artifact(name_or_id: str | UUID, version: str | None = None) → Any

Load an artifact.

Args:
: name_or_id: The name or ID of the artifact to load.
  version: The version of the artifact to load, if name_or_id is a
  <br/>
  > name. If not provided, the latest version will be loaded.

Returns:
: The loaded artifact.

### zenml.artifacts.utils.load_artifact_from_response(artifact: [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)) → Any

Load the given artifact into memory.

Args:
: artifact: The artifact to load.

Returns:
: The artifact loaded into memory.

### zenml.artifacts.utils.load_artifact_visualization(artifact: [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse), index: int = 0, zen_store: [BaseZenStore](zenml.zen_stores.md#zenml.zen_stores.base_zen_store.BaseZenStore) | None = None, encode_image: bool = False) → [LoadedVisualization](zenml.models.v2.misc.md#zenml.models.v2.misc.loaded_visualization.LoadedVisualization)

Load a visualization of the given artifact.

Args:
: artifact: The artifact to visualize.
  index: The index of the visualization to load.
  zen_store: The ZenStore to use for finding the artifact store. If not
  <br/>
  > provided, the client’s ZenStore will be used.
  <br/>
  encode_image: Whether to base64 encode image visualizations.

Returns:
: The loaded visualization.

Raises:
: DoesNotExistException: If the artifact does not have the requested
  : visualization or if the visualization was not found in the artifact
    store.

### zenml.artifacts.utils.load_model_from_metadata(model_uri: str) → Any

Load a zenml model artifact from a json file.

This function is used to load information from a Yaml file that was created
by the save_model_metadata function. The information in the Yaml file is
used to load the model into memory in the inference environment.

Args:
: model_uri: the artifact to extract the metadata from.

Returns:
: The ML model object loaded into memory.

### zenml.artifacts.utils.log_artifact_metadata(metadata: Dict[str, MetadataType], artifact_name: str | None = None, artifact_version: str | None = None) → None

Log artifact metadata.

This function can be used to log metadata for either existing artifact
versions or artifact versions that are newly created in the same step.

Args:
: metadata: The metadata to log.
  artifact_name: The name of the artifact to log metadata for. Can
  <br/>
  > be omitted when being called inside a step with only one output.
  <br/>
  artifact_version: The version of the artifact to log metadata for. If
  : not provided, when being called inside a step that produces an
    artifact named artifact_name, the metadata will be associated to
    the corresponding newly created artifact. Or, if not provided when
    being called outside of a step, or in a step that does not produce
    any artifact named artifact_name, the metadata will be associated
    to the latest version of that artifact.

Raises:
: ValueError: If no artifact name is provided and the function is not
  : called inside a step with a single output, or, if neither an
    artifact nor an output with the given name exists.

### zenml.artifacts.utils.save_artifact(data: Any, name: str, version: int | str | None = None, tags: List[str] | None = None, extract_metadata: bool = True, include_visualizations: bool = True, has_custom_name: bool = True, user_metadata: Dict[str, MetadataType] | None = None, materializer: MaterializerClassOrSource | None = None, uri: str | None = None, is_model_artifact: bool = False, is_deployment_artifact: bool = False, manual_save: bool = True) → [ArtifactVersionResponse](zenml.models.md#zenml.models.ArtifactVersionResponse)

Upload and publish an artifact.

Args:
: name: The name of the artifact.
  data: The artifact data.
  version: The version of the artifact. If not provided, a new
  <br/>
  > auto-incremented version will be used.
  <br/>
  tags: Tags to associate with the artifact.
  extract_metadata: If artifact metadata should be extracted and returned.
  include_visualizations: If artifact visualizations should be generated.
  has_custom_name: If the artifact name is custom and should be listed in
  <br/>
  > the dashboard “Artifacts” tab.
  <br/>
  user_metadata: User-provided metadata to store with the artifact.
  materializer: The materializer to use for saving the artifact to the
  <br/>
  > artifact store.
  <br/>
  uri: The URI within the artifact store to upload the artifact
  : to. If not provided, the artifact will be uploaded to
    custom_artifacts/{name}/{version}.
  <br/>
  is_model_artifact: If the artifact is a model artifact.
  is_deployment_artifact: If the artifact is a deployment artifact.
  manual_save: If this function is called manually and should therefore
  <br/>
  > link the artifact to the current step run.

Returns:
: The saved artifact response.

Raises:
: RuntimeError: If artifact URI already exists.
  EntityExistsError: If artifact version already exists.

### zenml.artifacts.utils.save_model_metadata(model_artifact: [ArtifactVersionResponse](zenml.models.v2.core.md#zenml.models.v2.core.artifact_version.ArtifactVersionResponse)) → str

Save a zenml model artifact metadata to a YAML file.

This function is used to extract and save information from a zenml model
artifact such as the model type and materializer. The extracted information
will be the key to loading the model into memory in the inference
environment.

datatype: the model type. This is the path to the model class.
materializer: The path to the materializer class.

Args:
: model_artifact: the artifact to extract the metadata from.

Returns:
: The path to the temporary file where the model metadata is saved

## Module contents
