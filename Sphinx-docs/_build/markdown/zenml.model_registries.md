# zenml.model_registries package

## Submodules

## zenml.model_registries.base_model_registry module

Base class for all ZenML model registries.

### *class* zenml.model_registries.base_model_registry.BaseModelRegistry(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML model registries.

#### *property* config *: [BaseModelRegistryConfig](#zenml.model_registries.base_model_registry.BaseModelRegistryConfig)*

Returns the config of the model registries.

Returns:
: The config of the model registries.

#### *abstract* delete_model(name: str) → None

Deletes a registered model from the model registry.

Args:
: name: The name of the registered model.

Raises:
: KeyError: If the model does not exist.
  RuntimeError: If deletion fails.

#### *abstract* delete_model_version(name: str, version: str) → None

Deletes a model version from the model registry.

Args:
: name: The name of the registered model.
  version: The version of the model version to delete.

Raises:
: KeyError: If the model version does not exist.
  RuntimeError: If deletion fails.

#### get_latest_model_version(name: str, stage: [ModelVersionStage](#zenml.model_registries.base_model_registry.ModelVersionStage) | None = None) → [RegistryModelVersion](#zenml.model_registries.base_model_registry.RegistryModelVersion) | None

Gets the latest model version for a registered model.

This method is used to get the latest model version for a registered
model. If no stage is provided, the latest model version across all
stages is returned. If a stage is provided, the latest model version
for that stage is returned.

Args:
: name: The name of the registered model.
  stage: The stage of the model version.

Returns:
: The latest model version.

#### *abstract* get_model(name: str) → [RegisteredModel](#zenml.model_registries.base_model_registry.RegisteredModel)

Gets a registered model from the model registry.

Args:
: name: The name of the registered model.

Returns:
: The registered model.

Raises:
: zenml.exceptions.EntityExistsError: If the model does not exist.
  RuntimeError: If retrieval fails.

#### *abstract* get_model_uri_artifact_store(model_version: [RegistryModelVersion](#zenml.model_registries.base_model_registry.RegistryModelVersion)) → str

Gets the URI artifact store for a model version.

This method retrieves the URI of the artifact store for a specific model
version. Its purpose is to ensure that the URI is in the correct format
for the specific artifact store being used. This is essential for the
model serving component, which relies on the URI to serve the model
version. In some cases, the URI may be stored in a different format by
certain model registry integrations. This method allows us to obtain the
URI in the correct format, regardless of the integration being used.

Note: In some cases the URI artifact store may not be available to the
user, the method should save the target model in one of the other
artifact stores supported by ZenML and return the URI of that artifact
store.

Args:
: model_version: The model version for which to get the URI artifact
  : store.

Returns:
: The URI artifact store for the model version.

#### *abstract* get_model_version(name: str, version: str) → [RegistryModelVersion](#zenml.model_registries.base_model_registry.RegistryModelVersion)

Gets a model version for a registered model.

Args:
: name: The name of the registered model.
  version: The version of the model version to get.

Returns:
: The model version.

Raises:
: KeyError: If the model version does not exist.
  RuntimeError: If retrieval fails.

#### *abstract* list_model_versions(name: str | None = None, model_source_uri: str | None = None, metadata: [ModelRegistryModelMetadata](#zenml.model_registries.base_model_registry.ModelRegistryModelMetadata) | None = None, stage: [ModelVersionStage](#zenml.model_registries.base_model_registry.ModelVersionStage) | None = None, count: int | None = None, created_after: datetime | None = None, created_before: datetime | None = None, order_by_date: str | None = None, \*\*kwargs: Any) → List[[RegistryModelVersion](#zenml.model_registries.base_model_registry.RegistryModelVersion)] | None

Lists all model versions for a registered model.

Args:
: name: The name of the registered model.
  model_source_uri: The model source URI of the registered model.
  metadata: Metadata associated with this model version.
  stage: The stage of the model version.
  count: The number of model versions to return.
  created_after: The timestamp after which to list model versions.
  created_before: The timestamp before which to list model versions.
  order_by_date: Whether to sort by creation time, this can
  <br/>
  > be “asc” or “desc”.
  <br/>
  kwargs: Additional keyword arguments.

Returns:
: A list of model versions.

#### *abstract* list_models(name: str | None = None, metadata: Dict[str, str] | None = None) → List[[RegisteredModel](#zenml.model_registries.base_model_registry.RegisteredModel)]

Lists all registered models in the model registry.

Args:
: name: The name of the registered model.
  metadata: The metadata associated with the registered model.

Returns:
: A list of registered models.

#### *abstract* load_model_version(name: str, version: str, \*\*kwargs: Any) → Any

Loads a model version from the model registry.

Args:
: name: The name of the registered model.
  version: The version of the model version to load.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments.

Returns:
: The loaded model version.

Raises:
: KeyError: If the model version does not exist.
  RuntimeError: If loading fails.

#### *abstract* register_model(name: str, description: str | None = None, metadata: Dict[str, str] | None = None) → [RegisteredModel](#zenml.model_registries.base_model_registry.RegisteredModel)

Registers a model in the model registry.

Args:
: name: The name of the registered model.
  description: The description of the registered model.
  metadata: The metadata associated with the registered model.

Returns:
: The registered model.

Raises:
: zenml.exceptions.EntityExistsError: If a model with the same name already exists.
  RuntimeError: If registration fails.

#### *abstract* register_model_version(name: str, version: str | None = None, model_source_uri: str | None = None, description: str | None = None, metadata: [ModelRegistryModelMetadata](#zenml.model_registries.base_model_registry.ModelRegistryModelMetadata) | None = None, \*\*kwargs: Any) → [RegistryModelVersion](#zenml.model_registries.base_model_registry.RegistryModelVersion)

Registers a model version in the model registry.

Args:
: name: The name of the registered model.
  model_source_uri: The source URI of the model.
  version: The version of the model version.
  description: The description of the model version.
  metadata: The metadata associated with the model
  <br/>
  > version.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments.

Returns:
: The registered model version.

Raises:
: RuntimeError: If registration fails.

#### *abstract* update_model(name: str, description: str | None = None, metadata: Dict[str, str] | None = None, remove_metadata: List[str] | None = None) → [RegisteredModel](#zenml.model_registries.base_model_registry.RegisteredModel)

Updates a registered model in the model registry.

Args:
: name: The name of the registered model.
  description: The description of the registered model.
  metadata: The metadata associated with the registered model.
  remove_metadata: The metadata to remove from the registered model.

Raises:
: KeyError: If the model does not exist.
  RuntimeError: If update fails.

#### *abstract* update_model_version(name: str, version: str, description: str | None = None, metadata: [ModelRegistryModelMetadata](#zenml.model_registries.base_model_registry.ModelRegistryModelMetadata) | None = None, remove_metadata: List[str] | None = None, stage: [ModelVersionStage](#zenml.model_registries.base_model_registry.ModelVersionStage) | None = None) → [RegistryModelVersion](#zenml.model_registries.base_model_registry.RegistryModelVersion)

Updates a model version in the model registry.

Args:
: name: The name of the registered model.
  version: The version of the model version to update.
  description: The description of the model version.
  metadata: Metadata associated with this model version.
  remove_metadata: The metadata to remove from the model version.
  stage: The stage of the model version.

Returns:
: The updated model version.

Raises:
: KeyError: If the model version does not exist.
  RuntimeError: If update fails.

### *class* zenml.model_registries.base_model_registry.BaseModelRegistryConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for model registries.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.model_registries.base_model_registry.BaseModelRegistryFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for all ZenML model registry flavors.

#### *property* config_class *: Type[[BaseModelRegistryConfig](#zenml.model_registries.base_model_registry.BaseModelRegistryConfig)]*

Config class for this flavor.

Returns:
: The config class for this flavor.

#### *abstract property* implementation_class *: Type[[StackComponent](zenml.stack.md#zenml.stack.stack_component.StackComponent)]*

Returns the implementation class for this flavor.

Returns:
: The implementation class for this flavor.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Type of the flavor.

Returns:
: StackComponentType: The type of the flavor.

### *class* zenml.model_registries.base_model_registry.ModelRegistryModelMetadata(\*, zenml_version: str | None = None, zenml_run_name: str | None = None, zenml_pipeline_name: str | None = None, zenml_pipeline_uuid: str | None = None, zenml_pipeline_run_uuid: str | None = None, zenml_step_name: str | None = None, zenml_workspace: str | None = None, \*\*extra_data: Any)

Bases: `BaseModel`

Base class for all ZenML model registry model metadata.

The ModelRegistryModelMetadata class represents metadata associated with
a registered model version, including information such as the associated
pipeline name, pipeline run ID, step name, ZenML version, and custom
attributes. It serves as a blueprint for creating concrete model metadata
implementations in a registry, and provides a record of the history of a
model and its development process.

#### *property* custom_attributes *: Dict[str, str]*

Returns a dictionary of custom attributes.

Returns:
: A dictionary of custom attributes.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'allow'}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_dump(\*, exclude_unset: bool = False, exclude_none: bool = True, \*\*kwargs: Any) → Dict[str, str]

Returns a dictionary representation of the metadata.

This method overrides the default Pydantic model_dump method to allow
for the exclusion of fields with a value of None.

Args:
: exclude_unset: Whether to exclude unset attributes.
  exclude_none: Whether to exclude None attributes.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments.

Returns:
: A dictionary representation of the metadata.

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'zenml_pipeline_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'zenml_pipeline_run_uuid': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'zenml_pipeline_uuid': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'zenml_run_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'zenml_step_name': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'zenml_version': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'zenml_workspace': FieldInfo(annotation=Union[str, NoneType], required=False, default=None)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### zenml_pipeline_name *: str | None*

#### zenml_pipeline_run_uuid *: str | None*

#### zenml_pipeline_uuid *: str | None*

#### zenml_run_name *: str | None*

#### zenml_step_name *: str | None*

#### zenml_version *: str | None*

#### zenml_workspace *: str | None*

### *class* zenml.model_registries.base_model_registry.ModelVersionStage(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: `Enum`

Enum of the possible stages of a registered model.

#### ARCHIVED *= 'Archived'*

#### NONE *= 'None'*

#### PRODUCTION *= 'Production'*

#### STAGING *= 'Staging'*

### *class* zenml.model_registries.base_model_registry.RegisteredModel(\*, name: str, description: str | None = None, metadata: Dict[str, str] | None = None)

Bases: `BaseModel`

Base class for all ZenML registered models.

Model Registration are the top-level entities in the model registry.
They serve as a container for all the versions of a model.

Attributes:
: name: Name of the registered model.
  description: Description of the registered model.
  metadata: metadata associated with the registered model.

#### description *: str | None*

#### metadata *: Dict[str, str] | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'metadata': FieldInfo(annotation=Union[Dict[str, str], NoneType], required=False, default=None), 'name': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### name *: str*

### *class* zenml.model_registries.base_model_registry.RegistryModelVersion(\*, version: str, model_source_uri: str, model_format: str, model_library: str | None = None, registered_model: [RegisteredModel](#zenml.model_registries.base_model_registry.RegisteredModel), description: str | None = None, created_at: datetime | None = None, last_updated_at: datetime | None = None, stage: [ModelVersionStage](#zenml.model_registries.base_model_registry.ModelVersionStage) = ModelVersionStage.NONE, metadata: [ModelRegistryModelMetadata](#zenml.model_registries.base_model_registry.ModelRegistryModelMetadata) | None = None)

Bases: `BaseModel`

Base class for all ZenML model versions.

The RegistryModelVersion class represents a version or snapshot of a registered
model, including information such as the associated ModelBundle, version
number, creation time, pipeline run information, and metadata. It serves as
a blueprint for creating concrete model version implementations in a registry,
and provides a record of the history of a model and its development process.

All model registries must extend this class with their own specific fields.

Attributes:
: registered_model: The registered model associated with this model
  model_source_uri: The URI of the model bundle associated with this model,
  <br/>
  > The model source can not be changed after the model version is created.
  > If the model source is changed, a new model version must be created.
  <br/>
  model_format: The format of the model bundle associated with this model,
  : The model format is set automatically by the model registry integration
    and can not be changed after the model version is created.
  <br/>
  model_library: The library used to create the model bundle associated with
  : this model, The model library refers to the library used to create the
    model source, e.g. TensorFlow, PyTorch, etc. For some model registries,
    the model library is set retrieved automatically by the model registry.
  <br/>
  version: The version number of this model version
  description: The description of this model version
  created_at: The creation time of this model version
  last_updated_at: The last updated time of this model version
  stage: The current stage of this model version
  metadata: Metadata associated with this model version

#### created_at *: datetime | None*

#### description *: str | None*

#### last_updated_at *: datetime | None*

#### metadata *: [ModelRegistryModelMetadata](#zenml.model_registries.base_model_registry.ModelRegistryModelMetadata) | None*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'protected_namespaces': ()}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'created_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'description': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'last_updated_at': FieldInfo(annotation=Union[datetime, NoneType], required=False, default=None), 'metadata': FieldInfo(annotation=Union[ModelRegistryModelMetadata, NoneType], required=False, default=None), 'model_format': FieldInfo(annotation=str, required=True), 'model_library': FieldInfo(annotation=Union[str, NoneType], required=False, default=None), 'model_source_uri': FieldInfo(annotation=str, required=True), 'registered_model': FieldInfo(annotation=RegisteredModel, required=True), 'stage': FieldInfo(annotation=ModelVersionStage, required=False, default=<ModelVersionStage.NONE: 'None'>), 'version': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### model_format *: str*

#### model_library *: str | None*

#### model_source_uri *: str*

#### registered_model *: [RegisteredModel](#zenml.model_registries.base_model_registry.RegisteredModel)*

#### stage *: [ModelVersionStage](#zenml.model_registries.base_model_registry.ModelVersionStage)*

#### version *: str*

## Module contents

Initialization of the MLflow Service.

Model registries are centralized repositories that facilitate the collaboration
and management of machine learning models. They provide functionalities such as
version control, metadata tracking, and storage of model artifacts, enabling 
data scientists to efficiently share and keep track of their models within
a team or organization.

### *class* zenml.model_registries.BaseModelRegistry(name: str, id: UUID, config: [StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig), flavor: str, type: [StackComponentType](zenml.md#zenml.enums.StackComponentType), user: UUID | None, workspace: UUID, created: datetime, updated: datetime, labels: Dict[str, Any] | None = None, connector_requirements: [ServiceConnectorRequirements](zenml.models.v2.misc.md#zenml.models.v2.misc.service_connector_type.ServiceConnectorRequirements) | None = None, connector: UUID | None = None, connector_resource_id: str | None = None, \*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent), `ABC`

Base class for all ZenML model registries.

#### *property* config *: [BaseModelRegistryConfig](#zenml.model_registries.base_model_registry.BaseModelRegistryConfig)*

Returns the config of the model registries.

Returns:
: The config of the model registries.

#### *abstract* delete_model(name: str) → None

Deletes a registered model from the model registry.

Args:
: name: The name of the registered model.

Raises:
: KeyError: If the model does not exist.
  RuntimeError: If deletion fails.

#### *abstract* delete_model_version(name: str, version: str) → None

Deletes a model version from the model registry.

Args:
: name: The name of the registered model.
  version: The version of the model version to delete.

Raises:
: KeyError: If the model version does not exist.
  RuntimeError: If deletion fails.

#### get_latest_model_version(name: str, stage: [ModelVersionStage](#zenml.model_registries.base_model_registry.ModelVersionStage) | None = None) → [RegistryModelVersion](#zenml.model_registries.base_model_registry.RegistryModelVersion) | None

Gets the latest model version for a registered model.

This method is used to get the latest model version for a registered
model. If no stage is provided, the latest model version across all
stages is returned. If a stage is provided, the latest model version
for that stage is returned.

Args:
: name: The name of the registered model.
  stage: The stage of the model version.

Returns:
: The latest model version.

#### *abstract* get_model(name: str) → [RegisteredModel](#zenml.model_registries.base_model_registry.RegisteredModel)

Gets a registered model from the model registry.

Args:
: name: The name of the registered model.

Returns:
: The registered model.

Raises:
: zenml.exceptions.EntityExistsError: If the model does not exist.
  RuntimeError: If retrieval fails.

#### *abstract* get_model_uri_artifact_store(model_version: [RegistryModelVersion](#zenml.model_registries.base_model_registry.RegistryModelVersion)) → str

Gets the URI artifact store for a model version.

This method retrieves the URI of the artifact store for a specific model
version. Its purpose is to ensure that the URI is in the correct format
for the specific artifact store being used. This is essential for the
model serving component, which relies on the URI to serve the model
version. In some cases, the URI may be stored in a different format by
certain model registry integrations. This method allows us to obtain the
URI in the correct format, regardless of the integration being used.

Note: In some cases the URI artifact store may not be available to the
user, the method should save the target model in one of the other
artifact stores supported by ZenML and return the URI of that artifact
store.

Args:
: model_version: The model version for which to get the URI artifact
  : store.

Returns:
: The URI artifact store for the model version.

#### *abstract* get_model_version(name: str, version: str) → [RegistryModelVersion](#zenml.model_registries.base_model_registry.RegistryModelVersion)

Gets a model version for a registered model.

Args:
: name: The name of the registered model.
  version: The version of the model version to get.

Returns:
: The model version.

Raises:
: KeyError: If the model version does not exist.
  RuntimeError: If retrieval fails.

#### *abstract* list_model_versions(name: str | None = None, model_source_uri: str | None = None, metadata: [ModelRegistryModelMetadata](#zenml.model_registries.base_model_registry.ModelRegistryModelMetadata) | None = None, stage: [ModelVersionStage](#zenml.model_registries.base_model_registry.ModelVersionStage) | None = None, count: int | None = None, created_after: datetime | None = None, created_before: datetime | None = None, order_by_date: str | None = None, \*\*kwargs: Any) → List[[RegistryModelVersion](#zenml.model_registries.base_model_registry.RegistryModelVersion)] | None

Lists all model versions for a registered model.

Args:
: name: The name of the registered model.
  model_source_uri: The model source URI of the registered model.
  metadata: Metadata associated with this model version.
  stage: The stage of the model version.
  count: The number of model versions to return.
  created_after: The timestamp after which to list model versions.
  created_before: The timestamp before which to list model versions.
  order_by_date: Whether to sort by creation time, this can
  <br/>
  > be “asc” or “desc”.
  <br/>
  kwargs: Additional keyword arguments.

Returns:
: A list of model versions.

#### *abstract* list_models(name: str | None = None, metadata: Dict[str, str] | None = None) → List[[RegisteredModel](#zenml.model_registries.base_model_registry.RegisteredModel)]

Lists all registered models in the model registry.

Args:
: name: The name of the registered model.
  metadata: The metadata associated with the registered model.

Returns:
: A list of registered models.

#### *abstract* load_model_version(name: str, version: str, \*\*kwargs: Any) → Any

Loads a model version from the model registry.

Args:
: name: The name of the registered model.
  version: The version of the model version to load.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments.

Returns:
: The loaded model version.

Raises:
: KeyError: If the model version does not exist.
  RuntimeError: If loading fails.

#### *abstract* register_model(name: str, description: str | None = None, metadata: Dict[str, str] | None = None) → [RegisteredModel](#zenml.model_registries.base_model_registry.RegisteredModel)

Registers a model in the model registry.

Args:
: name: The name of the registered model.
  description: The description of the registered model.
  metadata: The metadata associated with the registered model.

Returns:
: The registered model.

Raises:
: zenml.exceptions.EntityExistsError: If a model with the same name already exists.
  RuntimeError: If registration fails.

#### *abstract* register_model_version(name: str, version: str | None = None, model_source_uri: str | None = None, description: str | None = None, metadata: [ModelRegistryModelMetadata](#zenml.model_registries.base_model_registry.ModelRegistryModelMetadata) | None = None, \*\*kwargs: Any) → [RegistryModelVersion](#zenml.model_registries.base_model_registry.RegistryModelVersion)

Registers a model version in the model registry.

Args:
: name: The name of the registered model.
  model_source_uri: The source URI of the model.
  version: The version of the model version.
  description: The description of the model version.
  metadata: The metadata associated with the model
  <br/>
  > version.
  <br/>
  ```
  **
  ```
  <br/>
  kwargs: Additional keyword arguments.

Returns:
: The registered model version.

Raises:
: RuntimeError: If registration fails.

#### *abstract* update_model(name: str, description: str | None = None, metadata: Dict[str, str] | None = None, remove_metadata: List[str] | None = None) → [RegisteredModel](#zenml.model_registries.base_model_registry.RegisteredModel)

Updates a registered model in the model registry.

Args:
: name: The name of the registered model.
  description: The description of the registered model.
  metadata: The metadata associated with the registered model.
  remove_metadata: The metadata to remove from the registered model.

Raises:
: KeyError: If the model does not exist.
  RuntimeError: If update fails.

#### *abstract* update_model_version(name: str, version: str, description: str | None = None, metadata: [ModelRegistryModelMetadata](#zenml.model_registries.base_model_registry.ModelRegistryModelMetadata) | None = None, remove_metadata: List[str] | None = None, stage: [ModelVersionStage](#zenml.model_registries.base_model_registry.ModelVersionStage) | None = None) → [RegistryModelVersion](#zenml.model_registries.base_model_registry.RegistryModelVersion)

Updates a model version in the model registry.

Args:
: name: The name of the registered model.
  version: The version of the model version to update.
  description: The description of the model version.
  metadata: Metadata associated with this model version.
  remove_metadata: The metadata to remove from the model version.
  stage: The stage of the model version.

Returns:
: The updated model version.

Raises:
: KeyError: If the model version does not exist.
  RuntimeError: If update fails.

### *class* zenml.model_registries.BaseModelRegistryConfig(warn_about_plain_text_secrets: bool = False)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Base config for model registries.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

### *class* zenml.model_registries.BaseModelRegistryFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for all ZenML model registry flavors.

#### *property* config_class *: Type[[BaseModelRegistryConfig](#zenml.model_registries.base_model_registry.BaseModelRegistryConfig)]*

Config class for this flavor.

Returns:
: The config class for this flavor.

#### *abstract property* implementation_class *: Type[[StackComponent](zenml.stack.md#zenml.stack.stack_component.StackComponent)]*

Returns the implementation class for this flavor.

Returns:
: The implementation class for this flavor.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Type of the flavor.

Returns:
: StackComponentType: The type of the flavor.
