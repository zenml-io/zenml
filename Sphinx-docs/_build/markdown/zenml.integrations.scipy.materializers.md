# zenml.integrations.scipy.materializers package

## Submodules

## zenml.integrations.scipy.materializers.sparse_materializer module

Implementation of the Scipy Sparse Materializer.

### *class* zenml.integrations.scipy.materializers.sparse_materializer.SparseMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)

Materializer to read and write scipy sparse matrices.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'scipy.sparse._matrix.spmatrix'>,)*

#### extract_metadata(mat: spmatrix) → Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)]

Extract metadata from the given spmatrix object.

Args:
: mat: The spmatrix object to extract metadata from.

Returns:
: The extracted metadata as a dictionary.

#### load(data_type: Type[Any]) → spmatrix

Reads spmatrix from npz file.

Args:
: data_type: The type of the spmatrix to load.

Returns:
: A spmatrix object.

#### save(mat: spmatrix) → None

Writes a spmatrix to the artifact store as a npz file.

Args:
: mat: The spmatrix to write.

## Module contents

Initialization of the Scipy materializers.
