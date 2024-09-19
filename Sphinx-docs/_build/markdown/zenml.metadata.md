# zenml.metadata package

## Submodules

## zenml.metadata.lazy_load module

Run Metadata Lazy Loader definition.

### *class* zenml.metadata.lazy_load.RunMetadataLazyGetter(\_lazy_load_model: [Model](zenml.md#zenml.Model), \_lazy_load_artifact_name: str | None, \_lazy_load_artifact_version: str | None)

Bases: `object`

Run Metadata Lazy Getter helper class.

It serves the purpose to feed back to the user the metadata
lazy loader wrapper for any given key, if called inside a pipeline
design time context.

## zenml.metadata.metadata_types module

Custom types that can be used as metadata of ZenML artifacts.

### *class* zenml.metadata.metadata_types.DType

Bases: `str`

Special string class to indicate a data type.

### *class* zenml.metadata.metadata_types.MetadataTypeEnum(value, names=None, \*, module=None, qualname=None, type=None, start=1, boundary=None)

Bases: [`StrEnum`](zenml.utils.md#zenml.utils.enum_utils.StrEnum)

String Enum of all possible types that metadata can have.

#### BOOL *= 'bool'*

#### DICT *= 'dict'*

#### DTYPE *= 'DType'*

#### FLOAT *= 'float'*

#### INT *= 'int'*

#### LIST *= 'list'*

#### PATH *= 'Path'*

#### SET *= 'set'*

#### STORAGE_SIZE *= 'StorageSize'*

#### STRING *= 'str'*

#### TUPLE *= 'tuple'*

#### URI *= 'Uri'*

### *class* zenml.metadata.metadata_types.Path

Bases: `str`

Special string class to indicate a path.

### *class* zenml.metadata.metadata_types.StorageSize

Bases: `int`

Special int class to indicate the storage size in number of bytes.

### *class* zenml.metadata.metadata_types.Uri

Bases: `str`

Special string class to indicate a URI.

### zenml.metadata.metadata_types.cast_to_metadata_type(value: object, type_: [MetadataTypeEnum](#zenml.metadata.metadata_types.MetadataTypeEnum)) → str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](#zenml.metadata.metadata_types.Uri) | [Path](#zenml.metadata.metadata_types.Path) | [DType](#zenml.metadata.metadata_types.DType) | [StorageSize](#zenml.metadata.metadata_types.StorageSize)

Cast an object to a metadata type.

Args:
: value: The object to cast.
  <br/>
  ```
  type_
  ```
  <br/>
  : The metadata type to cast to.

Returns:
: The value cast to the given metadata type.

### zenml.metadata.metadata_types.get_metadata_type(object_: object) → [MetadataTypeEnum](#zenml.metadata.metadata_types.MetadataTypeEnum)

Get the metadata type enum for a given object.

Args:
: ```
  object_
  ```
  <br/>
  : The object to get the metadata type for.

Returns:
: The corresponding metadata type enum.

Raises:
: ValueError: If the metadata type is not supported.

## Module contents

Initialization of ZenML metadata.

ZenML metadata is any additional, dynamic information that is associated with
your pipeline runs and artifacts at runtime.
