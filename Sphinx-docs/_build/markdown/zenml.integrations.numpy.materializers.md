# zenml.integrations.numpy.materializers package

## Submodules

## zenml.integrations.numpy.materializers.numpy_materializer module

Implementation of the ZenML NumPy materializer.

### *class* zenml.integrations.numpy.materializers.numpy_materializer.NumpyMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)

Materializer to read data to and from pandas.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'numpy.ndarray'>,)*

#### extract_metadata(arr: NDArray[Any]) → Dict[str, MetadataType]

Extract metadata from the given numpy array.

Args:
: arr: The numpy array to extract metadata from.

Returns:
: The extracted metadata as a dictionary.

#### load(data_type: Type[Any]) → Any

Reads a numpy array from a .npy file.

Args:
: data_type: The type of the data to read.

Raises:
: ImportError: If pyarrow is not installed.

Returns:
: The numpy array.

#### save(arr: NDArray[Any]) → None

Writes a np.ndarray to the artifact store as a .npy file.

Args:
: arr: The numpy array to write.

#### save_visualizations(arr: NDArray[Any]) → Dict[str, [VisualizationType](zenml.md#zenml.enums.VisualizationType)]

Saves visualizations for a numpy array.

If the array is 1D, a histogram is saved. If the array is 2D or 3D with
3 or 4 channels, an image is saved.

Args:
: arr: The numpy array to visualize.

Returns:
: A dictionary of visualization URIs and their types.

## Module contents

Initialization of the Numpy materializer.
