# zenml.materializers package

## Submodules

## zenml.materializers.base_materializer module

Metaclass implementation for registering ZenML BaseMaterializer subclasses.

### *class* zenml.materializers.base_materializer.BaseMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: `object`

Base Materializer to realize artifact data.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'BaseArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= ()*

#### SKIP_REGISTRATION *: ClassVar[bool]* *= False*

#### *property* artifact_store *: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)*

Returns the artifact store used to store this artifact.

It either comes from the configuration of the materializer or from the
active stack.

Returns:
: The artifact store used to store this artifact.

#### *classmethod* can_handle_type(data_type: Type[Any]) → bool

Whether the materializer can read/write a certain type.

Args:
: data_type: The type to check.

Returns:
: Whether the materializer can read/write the given type.

#### extract_full_metadata(data: Any) → Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)]

Extract both base and custom metadata from the given data.

Args:
: data: The data to extract metadata from.

Returns:
: A dictionary of metadata.

#### extract_metadata(data: Any) → Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)]

Extract metadata from the given data.

This metadata will be tracked and displayed alongside the artifact.

Example:

```
``
```

\`
return {

> “some_attribute_i_want_to_track”: self.some_attribute,
> “pi”: 3.14,

### }

Args:
: data: The data to extract metadata from.

Returns:
: A dictionary of metadata.

#### load(data_type: Type[Any]) → Any

Write logic here to load the data of an artifact.

Args:
: data_type: What type the artifact data should be loaded as.

Returns:
: The data of the artifact.

#### save(data: Any) → None

Write logic here to save the data of an artifact.

Args:
: data: The data of the artifact to save.

#### save_visualizations(data: Any) → Dict[str, [VisualizationType](zenml.md#zenml.enums.VisualizationType)]

Save visualizations of the given data.

If this method is not overridden, no visualizations will be saved.

When overriding this method, make sure to save all visualizations to
files within self.uri.

Example:

```
``
```

\`
visualization_uri = os.path.join(self.uri, “visualization.html”)
with self.artifact_store.open(visualization_uri, “w”) as f:

> f.write(“<html><body>data</body></html>”)

visualization_uri_2 = os.path.join(self.uri, “visualization.png”)
data.save_as_png(visualization_uri_2)

return {
: visualization_uri: ArtifactVisualizationType.HTML,
  visualization_uri_2: ArtifactVisualizationType.IMAGE

### }

Args:
: data: The data of the artifact to visualize.

Returns:
: A dictionary of visualization URIs and their types.

#### validate_type_compatibility(data_type: Type[Any]) → None

Checks whether the materializer can read/write the given type.

Args:
: data_type: The type to check.

Raises:
: TypeError: If the materializer cannot read/write the given type.

### *class* zenml.materializers.base_materializer.BaseMaterializerMeta(name: str, bases: Tuple[Type[Any], ...], dct: Dict[str, Any])

Bases: `type`

Metaclass responsible for registering different BaseMaterializer subclasses.

Materializers are used for reading/writing artifacts.

## zenml.materializers.built_in_materializer module

Implementation of ZenML’s builtin materializer.

### *class* zenml.materializers.built_in_materializer.BuiltInContainerMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Handle built-in container types (dict, list, set, tuple).

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'BaseArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'dict'>, <class 'list'>, <class 'set'>, <class 'tuple'>)*

#### extract_metadata(data: Any) → Dict[str, MetadataType]

Extract metadata from the given built-in container object.

Args:
: data: The built-in container object to extract metadata from.

Returns:
: The extracted metadata as a dictionary.

#### load(data_type: Type[Any]) → Any

Reads a materialized built-in container object.

If the data was serialized to JSON, deserialize it.

Otherwise, reconstruct all elements according to the metadata file:
: 1. Resolve the data type using find_type_by_str(),
  2. Get the materializer via the default_materializer_registry,
  3. Initialize the materializer with the desired path,
  4. Use load() of that materializer to load the element.

Args:
: data_type: The type of the data to read.

Returns:
: The data read.

Raises:
: RuntimeError: If the data was not found.

#### save(data: Any) → None

Materialize a built-in container object.

If the object can be serialized to JSON, serialize it.

Otherwise, use the default_materializer_registry to find the correct
materializer for each element and materialize each element into a
subdirectory.

Tuples and sets are cast to list before materialization.

For non-serializable dicts, materialize keys/values as separate lists.

Args:
: data: The built-in container object to materialize.

Raises:
: Exception: If any exception occurs, it is raised after cleanup.

### *class* zenml.materializers.built_in_materializer.BuiltInMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Handle JSON-serializable basic types (bool, float, int, str).

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'bool'>, <class 'float'>, <class 'int'>, <class 'str'>, <class 'NoneType'>)*

#### extract_metadata(data: bool | float | int | str) → Dict[str, MetadataType]

Extract metadata from the given built-in container object.

Args:
: data: The built-in container object to extract metadata from.

Returns:
: The extracted metadata as a dictionary.

#### load(data_type: Type[bool] | Type[float] | Type[int] | Type[str]) → Any

Reads basic primitive types from JSON.

Args:
: data_type: The type of the data to read.

Returns:
: The data read.

#### save(data: bool | float | int | str) → None

Serialize a basic type to JSON.

Args:
: data: The data to store.

### *class* zenml.materializers.built_in_materializer.BytesMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Handle bytes data type, which is not JSON serializable.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'bytes'>,)*

#### load(data_type: Type[Any]) → Any

Reads a bytes object from file.

Args:
: data_type: The type of the data to read.

Returns:
: The data read.

#### save(data: Any) → None

Save a bytes object to file.

Args:
: data: The data to store.

### zenml.materializers.built_in_materializer.find_materializer_registry_type(type_: Type[Any]) → Type[Any]

For a given type, find the type registered in the registry.

This can be either the type itself, or a superclass of the type.

Args:
: ```
  type_
  ```
  <br/>
  : The type to find.

Returns:
: The type registered in the registry.

Raises:
: RuntimeError: If the type could not be resolved.

### zenml.materializers.built_in_materializer.find_type_by_str(type_str: str) → Type[Any]

Get a Python type, given its string representation.

E.g., “<class ‘int’>” should resolve to int.

Currently this is implemented by checking all artifact types registered in
the default_materializer_registry. This means, only types in the registry
can be found. Any other types will cause a RunTimeError.

Args:
: type_str: The string representation of a type.

Raises:
: RuntimeError: If the type could not be resolved.

Returns:
: The type whose string representation is type_str.

## zenml.materializers.cloudpickle_materializer module

Implementation of ZenML’s cloudpickle materializer.

### *class* zenml.materializers.cloudpickle_materializer.CloudpickleMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Materializer using cloudpickle.

This materializer can materialize (almost) any object, but does so in a
non-reproducble way since artifacts cannot be loaded from other Python
versions. It is recommended to use this materializer only as a last resort.

That is also why it has SKIP_REGISTRATION set to True and is currently
only used as a fallback materializer inside the materializer registry.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'object'>,)*

#### SKIP_REGISTRATION *: ClassVar[bool]* *= False*

#### load(data_type: Type[Any]) → Any

Reads an artifact from a cloudpickle file.

Args:
: data_type: The data type of the artifact.

Returns:
: The loaded artifact data.

#### save(data: Any) → None

Saves an artifact to a cloudpickle file.

Args:
: data: The data to save.

## zenml.materializers.materializer_registry module

Implementation of a default materializer registry.

### *class* zenml.materializers.materializer_registry.MaterializerRegistry

Bases: `object`

Matches a Python type to a default materializer.

#### get_default_materializer() → Type[[BaseMaterializer](#zenml.materializers.base_materializer.BaseMaterializer)]

Get the default materializer that is used if no other is found.

Returns:
: The default materializer.

#### get_materializer_types() → Dict[Type[Any], Type[[BaseMaterializer](#zenml.materializers.base_materializer.BaseMaterializer)]]

Get all registered materializer types.

Returns:
: A dictionary of registered materializer types.

#### is_registered(key: Type[Any]) → bool

Returns if a materializer class is registered for the given type.

Args:
: key: Indicates the type of object.

Returns:
: True if a materializer is registered for the given type, False
  otherwise.

#### register_and_overwrite_type(key: Type[Any], type_: Type[[BaseMaterializer](#zenml.materializers.base_materializer.BaseMaterializer)]) → None

Registers a new materializer and also overwrites a default if set.

Args:
: key: Indicates the type of object.
  <br/>
  ```
  type_
  ```
  <br/>
  : A BaseMaterializer subclass.

#### register_materializer_type(key: Type[Any], type_: Type[[BaseMaterializer](#zenml.materializers.base_materializer.BaseMaterializer)]) → None

Registers a new materializer.

Args:
: key: Indicates the type of object.
  <br/>
  ```
  type_
  ```
  <br/>
  : A BaseMaterializer subclass.

## zenml.materializers.numpy_materializer module

Placeholder for importing the Numpy Materializer from its former path.

## zenml.materializers.pandas_materializer module

Placeholder for importing the Pandas Materializer from its former path.

## zenml.materializers.pydantic_materializer module

Implementation of ZenML’s pydantic materializer.

### *class* zenml.materializers.pydantic_materializer.PydanticMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Handle Pydantic BaseModel objects.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'pydantic.main.BaseModel'>,)*

#### extract_metadata(data: BaseModel) → Dict[str, MetadataType]

Extract metadata from the given BaseModel object.

Args:
: data: The BaseModel object to extract metadata from.

Returns:
: The extracted metadata as a dictionary.

#### load(data_type: Type[BaseModel]) → Any

Reads BaseModel from JSON.

Args:
: data_type: The type of the data to read.

Returns:
: The data read.

#### save(data: BaseModel) → None

Serialize a BaseModel to JSON.

Args:
: data: The data to store.

## zenml.materializers.service_materializer module

Implementation of a materializer to read and write ZenML service instances.

### *class* zenml.materializers.service_materializer.ServiceMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Materializer to read/write service instances.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'ServiceArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'zenml.services.service.BaseService'>,)*

#### extract_metadata(service: [BaseService](zenml.services.md#zenml.services.service.BaseService)) → Dict[str, MetadataType]

Extract metadata from the given service.

Args:
: service: The service to extract metadata from.

Returns:
: The extracted metadata as a dictionary.

#### load(data_type: Type[Any]) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Creates and returns a service.

This service is instantiated from the serialized service configuration
and last known status information saved as artifact.

Args:
: data_type: The type of the data to read.

Returns:
: A ZenML service instance.

#### save(service: [BaseService](zenml.services.md#zenml.services.service.BaseService)) → None

Writes a ZenML service.

The configuration and last known status of the input service instance
are serialized and saved as an artifact.

Args:
: service: A ZenML service instance.

## zenml.materializers.structured_string_materializer module

Implementation of HTMLString materializer.

### *class* zenml.materializers.structured_string_materializer.StructuredStringMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Materializer for HTML or Markdown strings.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataAnalysisArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'zenml.types.CSVString'>, <class 'zenml.types.HTMLString'>, <class 'zenml.types.MarkdownString'>)*

#### load(data_type: Type[[CSVString](zenml.md#zenml.types.CSVString) | [HTMLString](zenml.md#zenml.types.HTMLString) | [MarkdownString](zenml.md#zenml.types.MarkdownString)]) → [CSVString](zenml.md#zenml.types.CSVString) | [HTMLString](zenml.md#zenml.types.HTMLString) | [MarkdownString](zenml.md#zenml.types.MarkdownString)

Loads the data from the HTML or Markdown file.

Args:
: data_type: The type of the data to read.

Returns:
: The loaded data.

#### save(data: [CSVString](zenml.md#zenml.types.CSVString) | [HTMLString](zenml.md#zenml.types.HTMLString) | [MarkdownString](zenml.md#zenml.types.MarkdownString)) → None

Save data as an HTML or Markdown file.

Args:
: data: The data to save as an HTML or Markdown file.

#### save_visualizations(data: [CSVString](zenml.md#zenml.types.CSVString) | [HTMLString](zenml.md#zenml.types.HTMLString) | [MarkdownString](zenml.md#zenml.types.MarkdownString)) → Dict[str, [VisualizationType](zenml.md#zenml.enums.VisualizationType)]

Save visualizations for the given data.

Args:
: data: The data to save visualizations for.

Returns:
: A dictionary of visualization URIs and their types.

## Module contents

Initialization of ZenML materializers.

Materializers are used to convert a ZenML artifact into a specific format. They
are most often used to handle the input or output of ZenML steps, and can be
extended by building on the BaseMaterializer class.

### *class* zenml.materializers.BuiltInContainerMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Handle built-in container types (dict, list, set, tuple).

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'BaseArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'dict'>, <class 'list'>, <class 'set'>, <class 'tuple'>)*

#### extract_metadata(data: Any) → Dict[str, MetadataType]

Extract metadata from the given built-in container object.

Args:
: data: The built-in container object to extract metadata from.

Returns:
: The extracted metadata as a dictionary.

#### load(data_type: Type[Any]) → Any

Reads a materialized built-in container object.

If the data was serialized to JSON, deserialize it.

Otherwise, reconstruct all elements according to the metadata file:
: 1. Resolve the data type using find_type_by_str(),
  2. Get the materializer via the default_materializer_registry,
  3. Initialize the materializer with the desired path,
  4. Use load() of that materializer to load the element.

Args:
: data_type: The type of the data to read.

Returns:
: The data read.

Raises:
: RuntimeError: If the data was not found.

#### save(data: Any) → None

Materialize a built-in container object.

If the object can be serialized to JSON, serialize it.

Otherwise, use the default_materializer_registry to find the correct
materializer for each element and materialize each element into a
subdirectory.

Tuples and sets are cast to list before materialization.

For non-serializable dicts, materialize keys/values as separate lists.

Args:
: data: The built-in container object to materialize.

Raises:
: Exception: If any exception occurs, it is raised after cleanup.

### *class* zenml.materializers.BuiltInMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Handle JSON-serializable basic types (bool, float, int, str).

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'bool'>, <class 'float'>, <class 'int'>, <class 'str'>, <class 'NoneType'>)*

#### extract_metadata(data: bool | float | int | str) → Dict[str, MetadataType]

Extract metadata from the given built-in container object.

Args:
: data: The built-in container object to extract metadata from.

Returns:
: The extracted metadata as a dictionary.

#### load(data_type: Type[bool] | Type[float] | Type[int] | Type[str]) → Any

Reads basic primitive types from JSON.

Args:
: data_type: The type of the data to read.

Returns:
: The data read.

#### save(data: bool | float | int | str) → None

Serialize a basic type to JSON.

Args:
: data: The data to store.

### *class* zenml.materializers.BytesMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Handle bytes data type, which is not JSON serializable.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'bytes'>,)*

#### load(data_type: Type[Any]) → Any

Reads a bytes object from file.

Args:
: data_type: The type of the data to read.

Returns:
: The data read.

#### save(data: Any) → None

Save a bytes object to file.

Args:
: data: The data to store.

### *class* zenml.materializers.CloudpickleMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Materializer using cloudpickle.

This materializer can materialize (almost) any object, but does so in a
non-reproducble way since artifacts cannot be loaded from other Python
versions. It is recommended to use this materializer only as a last resort.

That is also why it has SKIP_REGISTRATION set to True and is currently
only used as a fallback materializer inside the materializer registry.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'object'>,)*

#### SKIP_REGISTRATION *: ClassVar[bool]* *= False*

#### load(data_type: Type[Any]) → Any

Reads an artifact from a cloudpickle file.

Args:
: data_type: The data type of the artifact.

Returns:
: The loaded artifact data.

#### save(data: Any) → None

Saves an artifact to a cloudpickle file.

Args:
: data: The data to save.

### *class* zenml.materializers.PydanticMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Handle Pydantic BaseModel objects.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'pydantic.main.BaseModel'>,)*

#### extract_metadata(data: BaseModel) → Dict[str, MetadataType]

Extract metadata from the given BaseModel object.

Args:
: data: The BaseModel object to extract metadata from.

Returns:
: The extracted metadata as a dictionary.

#### load(data_type: Type[BaseModel]) → Any

Reads BaseModel from JSON.

Args:
: data_type: The type of the data to read.

Returns:
: The data read.

#### save(data: BaseModel) → None

Serialize a BaseModel to JSON.

Args:
: data: The data to store.

### *class* zenml.materializers.ServiceMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Materializer to read/write service instances.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'ServiceArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'zenml.services.service.BaseService'>,)*

#### extract_metadata(service: [BaseService](zenml.services.md#zenml.services.service.BaseService)) → Dict[str, MetadataType]

Extract metadata from the given service.

Args:
: service: The service to extract metadata from.

Returns:
: The extracted metadata as a dictionary.

#### load(data_type: Type[Any]) → [BaseService](zenml.services.md#zenml.services.service.BaseService)

Creates and returns a service.

This service is instantiated from the serialized service configuration
and last known status information saved as artifact.

Args:
: data_type: The type of the data to read.

Returns:
: A ZenML service instance.

#### save(service: [BaseService](zenml.services.md#zenml.services.service.BaseService)) → None

Writes a ZenML service.

The configuration and last known status of the input service instance
are serialized and saved as an artifact.

Args:
: service: A ZenML service instance.

### *class* zenml.materializers.StructuredStringMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](#zenml.materializers.base_materializer.BaseMaterializer)

Materializer for HTML or Markdown strings.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataAnalysisArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'zenml.types.CSVString'>, <class 'zenml.types.HTMLString'>, <class 'zenml.types.MarkdownString'>)*

#### load(data_type: Type[[CSVString](zenml.md#zenml.types.CSVString) | [HTMLString](zenml.md#zenml.types.HTMLString) | [MarkdownString](zenml.md#zenml.types.MarkdownString)]) → [CSVString](zenml.md#zenml.types.CSVString) | [HTMLString](zenml.md#zenml.types.HTMLString) | [MarkdownString](zenml.md#zenml.types.MarkdownString)

Loads the data from the HTML or Markdown file.

Args:
: data_type: The type of the data to read.

Returns:
: The loaded data.

#### save(data: [CSVString](zenml.md#zenml.types.CSVString) | [HTMLString](zenml.md#zenml.types.HTMLString) | [MarkdownString](zenml.md#zenml.types.MarkdownString)) → None

Save data as an HTML or Markdown file.

Args:
: data: The data to save as an HTML or Markdown file.

#### save_visualizations(data: [CSVString](zenml.md#zenml.types.CSVString) | [HTMLString](zenml.md#zenml.types.HTMLString) | [MarkdownString](zenml.md#zenml.types.MarkdownString)) → Dict[str, [VisualizationType](zenml.md#zenml.enums.VisualizationType)]

Save visualizations for the given data.

Args:
: data: The data to save visualizations for.

Returns:
: A dictionary of visualization URIs and their types.
