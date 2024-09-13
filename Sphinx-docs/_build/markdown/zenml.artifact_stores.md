# zenml.artifact_stores package

## Submodules

## zenml.artifact_stores.base_artifact_store module

The base interface to extend the ZenML artifact store.

### *class* zenml.artifact_stores.base_artifact_store.BaseArtifactStore(\*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent)

Base class for all ZenML artifact stores.

#### *property* config *: [BaseArtifactStoreConfig](#zenml.artifact_stores.base_artifact_store.BaseArtifactStoreConfig)*

Returns the BaseArtifactStoreConfig config.

Returns:
: The configuration.

#### *abstract* copyfile(src: bytes | str, dst: bytes | str, overwrite: bool = False) → None

Copy a file from the source to the destination.

Args:
: src: The source path.
  dst: The destination path.
  overwrite: Whether to overwrite the destination file if it exists.

#### *property* custom_cache_key *: bytes | None*

Custom cache key.

Any artifact store can override this property in case they need
additional control over the caching behavior.

Returns:
: Custom cache key.

#### *abstract* exists(path: bytes | str) → bool

Checks if a path exists.

Args:
: path: The path to check.

Returns:
: True if the path exists.

#### *abstract* glob(pattern: bytes | str) → List[bytes | str]

Gets the paths that match a glob pattern.

Args:
: pattern: The glob pattern.

Returns:
: The list of paths that match the pattern.

#### *abstract* isdir(path: bytes | str) → bool

Returns whether the given path points to a directory.

Args:
: path: The path to check.

Returns:
: True if the path points to a directory.

#### *abstract* listdir(path: bytes | str) → List[bytes | str]

Returns a list of files under a given directory in the filesystem.

Args:
: path: The path to list.

Returns:
: The list of files under the given path.

#### *abstract* makedirs(path: bytes | str) → None

Make a directory at the given path, recursively creating parents.

Args:
: path: The path to create.

#### *abstract* mkdir(path: bytes | str) → None

Make a directory at the given path; parent directory must exist.

Args:
: path: The path to create.

#### *abstract* open(name: bytes | str, mode: str = 'r') → Any

Open a file at the given path.

Args:
: name: The path of the file to open.
  mode: The mode to open the file.

Returns:
: The file object.

#### *property* path *: str*

The path to the artifact store.

Returns:
: The path.

#### *abstract* remove(path: bytes | str) → None

Remove the file at the given path. Dangerous operation.

Args:
: path: The path to remove.

#### *abstract* rename(src: bytes | str, dst: bytes | str, overwrite: bool = False) → None

Rename source file to destination file.

Args:
: src: The source path.
  dst: The destination path.
  overwrite: Whether to overwrite the destination file if it exists.

#### *abstract* rmtree(path: bytes | str) → None

Deletes dir recursively. Dangerous operation.

Args:
: path: The path to delete.

#### *abstract* size(path: bytes | str) → int | None

Get the size of a file in bytes.

Args:
: path: The path to the file.

Returns:
: The size of the file in bytes or None if the artifact store
  does not implement the size method.

#### *abstract* stat(path: bytes | str) → Any

Return the stat descriptor for a given file path.

Args:
: path: The path to check.

Returns:
: The stat descriptor.

#### *abstract* walk(top: bytes | str, topdown: bool = True, onerror: Callable[[...], None] | None = None) → Iterable[Tuple[bytes | str, List[bytes | str], List[bytes | str]]]

Return an iterator that walks the contents of the given directory.

Args:
: top: The path to walk.
  topdown: Whether to walk the top-down or bottom-up.
  onerror: The error handler.

Returns:
: The iterator that walks the contents of the given directory.

### *class* zenml.artifact_stores.base_artifact_store.BaseArtifactStoreConfig(warn_about_plain_text_secrets: bool = False, \*, path: str)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Config class for BaseArtifactStore.

#### IS_IMMUTABLE_FILESYSTEM *: ClassVar[bool]* *= False*

#### SUPPORTED_SCHEMES *: ClassVar[Set[str]]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'path': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### path *: str*

### *class* zenml.artifact_stores.base_artifact_store.BaseArtifactStoreFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for artifact store flavors.

#### *property* config_class *: Type[[StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)]*

Config class for this flavor.

Returns:
: The config class.

#### *abstract property* implementation_class *: Type[[BaseArtifactStore](#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)]*

Implementation class.

Returns:
: The implementation class.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.

## zenml.artifact_stores.local_artifact_store module

The local artifact store is a local implementation of the artifact store.

In ZenML, the inputs and outputs which go through any step is treated as an
artifact and as its name suggests, an ArtifactStore is a place where these
artifacts get stored.

### *class* zenml.artifact_stores.local_artifact_store.LocalArtifactStore(\*args: Any, \*\*kwargs: Any)

Bases: [`LocalFilesystem`](zenml.io.md#zenml.io.local_filesystem.LocalFilesystem), [`BaseArtifactStore`](#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)

Artifact Store for local artifacts.

All methods are inherited from the default LocalFilesystem.

#### *property* custom_cache_key *: bytes | None*

Custom cache key.

The client ID is returned here to invalidate caching when using the same
local artifact store on multiple client machines.

Returns:
: Custom cache key.

#### *static* get_default_local_path(id_: UUID) → str

Returns the default local path for a local artifact store.

Args:
: ```
  id_
  ```
  <br/>
  : The id of the local artifact store.

Returns:
: str: The default local path.

#### *property* local_path *: str | None*

Returns the local path of the artifact store.

Returns:
: The local path of the artifact store.

#### *property* path *: str*

Returns the path to the local artifact store.

If the user has not defined a path in the config, this will create a
sub-folder in the global config directory.

Returns:
: The path to the local artifact store.

### *class* zenml.artifact_stores.local_artifact_store.LocalArtifactStoreConfig(warn_about_plain_text_secrets: bool = False, \*, path: str = '')

Bases: [`BaseArtifactStoreConfig`](#zenml.artifact_stores.base_artifact_store.BaseArtifactStoreConfig)

Config class for the local artifact store.

Attributes:
: path: The path to the local artifact store.

#### SUPPORTED_SCHEMES *: ClassVar[Set[str]]* *= {''}*

#### *classmethod* ensure_path_local(path: str) → str

Pydantic validator which ensures that the given path is a local path.

Args:
: path: The path to validate.

Returns:
: str: The validated (local) path.

Raises:
: ArtifactStoreInterfaceError: If the given path is not a local path.

#### *property* is_local *: bool*

Checks if this stack component is running locally.

Returns:
: True if this config is for a local component, False otherwise.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'path': FieldInfo(annotation=str, required=False, default='')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### path *: str*

### *class* zenml.artifact_stores.local_artifact_store.LocalArtifactStoreFlavor

Bases: [`BaseArtifactStoreFlavor`](#zenml.artifact_stores.base_artifact_store.BaseArtifactStoreFlavor)

Class for the LocalArtifactStoreFlavor.

#### *property* config_class *: Type[[LocalArtifactStoreConfig](#zenml.artifact_stores.local_artifact_store.LocalArtifactStoreConfig)]*

Config class for this flavor.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[[LocalArtifactStore](#zenml.artifact_stores.local_artifact_store.LocalArtifactStore)]*

Implementation class.

Returns:
: The implementation class.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Returns the name of the artifact store flavor.

Returns:
: str: The name of the artifact store flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

## Module contents

ZenML’s artifact-store stores artifacts in a file system.

In ZenML, the inputs and outputs which go through any step is treated as an
artifact and as its name suggests, an ArtifactStore is a place where these
artifacts get stored.

Out of the box, ZenML comes with the BaseArtifactStore and
LocalArtifactStore implementations. While the BaseArtifactStore establishes
an interface for people who want to extend it to their needs, the
LocalArtifactStore is a simple implementation for a local setup.

Moreover, additional artifact stores can be found in specific integrations
modules, such as the GCPArtifactStore in the gcp integration and the
AzureArtifactStore in the azure integration.

### *class* zenml.artifact_stores.BaseArtifactStore(\*args: Any, \*\*kwargs: Any)

Bases: [`StackComponent`](zenml.stack.md#zenml.stack.stack_component.StackComponent)

Base class for all ZenML artifact stores.

#### *property* config *: [BaseArtifactStoreConfig](#zenml.artifact_stores.base_artifact_store.BaseArtifactStoreConfig)*

Returns the BaseArtifactStoreConfig config.

Returns:
: The configuration.

#### *abstract* copyfile(src: bytes | str, dst: bytes | str, overwrite: bool = False) → None

Copy a file from the source to the destination.

Args:
: src: The source path.
  dst: The destination path.
  overwrite: Whether to overwrite the destination file if it exists.

#### *property* custom_cache_key *: bytes | None*

Custom cache key.

Any artifact store can override this property in case they need
additional control over the caching behavior.

Returns:
: Custom cache key.

#### *abstract* exists(path: bytes | str) → bool

Checks if a path exists.

Args:
: path: The path to check.

Returns:
: True if the path exists.

#### *abstract* glob(pattern: bytes | str) → List[bytes | str]

Gets the paths that match a glob pattern.

Args:
: pattern: The glob pattern.

Returns:
: The list of paths that match the pattern.

#### *abstract* isdir(path: bytes | str) → bool

Returns whether the given path points to a directory.

Args:
: path: The path to check.

Returns:
: True if the path points to a directory.

#### *abstract* listdir(path: bytes | str) → List[bytes | str]

Returns a list of files under a given directory in the filesystem.

Args:
: path: The path to list.

Returns:
: The list of files under the given path.

#### *abstract* makedirs(path: bytes | str) → None

Make a directory at the given path, recursively creating parents.

Args:
: path: The path to create.

#### *abstract* mkdir(path: bytes | str) → None

Make a directory at the given path; parent directory must exist.

Args:
: path: The path to create.

#### *abstract* open(name: bytes | str, mode: str = 'r') → Any

Open a file at the given path.

Args:
: name: The path of the file to open.
  mode: The mode to open the file.

Returns:
: The file object.

#### *property* path *: str*

The path to the artifact store.

Returns:
: The path.

#### *abstract* remove(path: bytes | str) → None

Remove the file at the given path. Dangerous operation.

Args:
: path: The path to remove.

#### *abstract* rename(src: bytes | str, dst: bytes | str, overwrite: bool = False) → None

Rename source file to destination file.

Args:
: src: The source path.
  dst: The destination path.
  overwrite: Whether to overwrite the destination file if it exists.

#### *abstract* rmtree(path: bytes | str) → None

Deletes dir recursively. Dangerous operation.

Args:
: path: The path to delete.

#### *abstract* size(path: bytes | str) → int | None

Get the size of a file in bytes.

Args:
: path: The path to the file.

Returns:
: The size of the file in bytes or None if the artifact store
  does not implement the size method.

#### *abstract* stat(path: bytes | str) → Any

Return the stat descriptor for a given file path.

Args:
: path: The path to check.

Returns:
: The stat descriptor.

#### *abstract* walk(top: bytes | str, topdown: bool = True, onerror: Callable[[...], None] | None = None) → Iterable[Tuple[bytes | str, List[bytes | str], List[bytes | str]]]

Return an iterator that walks the contents of the given directory.

Args:
: top: The path to walk.
  topdown: Whether to walk the top-down or bottom-up.
  onerror: The error handler.

Returns:
: The iterator that walks the contents of the given directory.

### *class* zenml.artifact_stores.BaseArtifactStoreConfig(warn_about_plain_text_secrets: bool = False, \*, path: str)

Bases: [`StackComponentConfig`](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)

Config class for BaseArtifactStore.

#### IS_IMMUTABLE_FILESYSTEM *: ClassVar[bool]* *= False*

#### SUPPORTED_SCHEMES *: ClassVar[Set[str]]*

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'path': FieldInfo(annotation=str, required=True)}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### path *: str*

### *class* zenml.artifact_stores.BaseArtifactStoreFlavor

Bases: [`Flavor`](zenml.stack.md#zenml.stack.flavor.Flavor)

Base class for artifact store flavors.

#### *property* config_class *: Type[[StackComponentConfig](zenml.stack.md#zenml.stack.stack_component.StackComponentConfig)]*

Config class for this flavor.

Returns:
: The config class.

#### *abstract property* implementation_class *: Type[[BaseArtifactStore](#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)]*

Implementation class.

Returns:
: The implementation class.

#### *property* type *: [StackComponentType](zenml.md#zenml.enums.StackComponentType)*

Returns the flavor type.

Returns:
: The flavor type.

### *class* zenml.artifact_stores.LocalArtifactStore(\*args: Any, \*\*kwargs: Any)

Bases: [`LocalFilesystem`](zenml.io.md#zenml.io.local_filesystem.LocalFilesystem), [`BaseArtifactStore`](#zenml.artifact_stores.base_artifact_store.BaseArtifactStore)

Artifact Store for local artifacts.

All methods are inherited from the default LocalFilesystem.

#### *property* custom_cache_key *: bytes | None*

Custom cache key.

The client ID is returned here to invalidate caching when using the same
local artifact store on multiple client machines.

Returns:
: Custom cache key.

#### *static* get_default_local_path(id_: UUID) → str

Returns the default local path for a local artifact store.

Args:
: ```
  id_
  ```
  <br/>
  : The id of the local artifact store.

Returns:
: str: The default local path.

#### *property* local_path *: str | None*

Returns the local path of the artifact store.

Returns:
: The local path of the artifact store.

#### *property* path *: str*

Returns the path to the local artifact store.

If the user has not defined a path in the config, this will create a
sub-folder in the global config directory.

Returns:
: The path to the local artifact store.

### *class* zenml.artifact_stores.LocalArtifactStoreConfig(warn_about_plain_text_secrets: bool = False, \*, path: str = '')

Bases: [`BaseArtifactStoreConfig`](#zenml.artifact_stores.base_artifact_store.BaseArtifactStoreConfig)

Config class for the local artifact store.

Attributes:
: path: The path to the local artifact store.

#### SUPPORTED_SCHEMES *: ClassVar[Set[str]]* *= {''}*

#### *classmethod* ensure_path_local(path: str) → str

Pydantic validator which ensures that the given path is a local path.

Args:
: path: The path to validate.

Returns:
: str: The validated (local) path.

Raises:
: ArtifactStoreInterfaceError: If the given path is not a local path.

#### *property* is_local *: bool*

Checks if this stack component is running locally.

Returns:
: True if this config is for a local component, False otherwise.

#### model_computed_fields *: ClassVar[dict[str, ComputedFieldInfo]]* *= {}*

A dictionary of computed field names and their corresponding ComputedFieldInfo objects.

#### model_config *: ClassVar[ConfigDict]* *= {'extra': 'forbid', 'frozen': True}*

Configuration for the model, should be a dictionary conforming to [ConfigDict][pydantic.config.ConfigDict].

#### model_fields *: ClassVar[dict[str, FieldInfo]]* *= {'path': FieldInfo(annotation=str, required=False, default='')}*

Metadata about the fields defined on the model,
mapping of field names to [FieldInfo][pydantic.fields.FieldInfo].

This replaces Model._\_fields_\_ from Pydantic V1.

#### path *: str*

### *class* zenml.artifact_stores.LocalArtifactStoreFlavor

Bases: [`BaseArtifactStoreFlavor`](#zenml.artifact_stores.base_artifact_store.BaseArtifactStoreFlavor)

Class for the LocalArtifactStoreFlavor.

#### *property* config_class *: Type[[LocalArtifactStoreConfig](#zenml.artifact_stores.local_artifact_store.LocalArtifactStoreConfig)]*

Config class for this flavor.

Returns:
: The config class.

#### *property* docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.

#### *property* implementation_class *: Type[[LocalArtifactStore](#zenml.artifact_stores.local_artifact_store.LocalArtifactStore)]*

Implementation class.

Returns:
: The implementation class.

#### *property* logo_url *: str*

A url to represent the flavor in the dashboard.

Returns:
: The flavor logo.

#### *property* name *: str*

Returns the name of the artifact store flavor.

Returns:
: str: The name of the artifact store flavor.

#### *property* sdk_docs_url *: str | None*

A url to point at docs explaining this flavor.

Returns:
: A flavor docs url.
