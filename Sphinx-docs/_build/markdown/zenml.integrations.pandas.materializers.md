# zenml.integrations.pandas.materializers package

## Submodules

## zenml.integrations.pandas.materializers.pandas_materializer module

Materializer for Pandas.

### *class* zenml.integrations.pandas.materializers.pandas_materializer.PandasMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)

Materializer to read data to and from pandas.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'pandas.core.frame.DataFrame'>, <class 'pandas.core.series.Series'>)*

#### extract_metadata(df: DataFrame | Series) → Dict[str, str | int | float | bool | Dict[Any, Any] | List[Any] | Set[Any] | Tuple[Any, ...] | [Uri](zenml.metadata.md#zenml.metadata.metadata_types.Uri) | [Path](zenml.metadata.md#zenml.metadata.metadata_types.Path) | [DType](zenml.metadata.md#zenml.metadata.metadata_types.DType) | [StorageSize](zenml.metadata.md#zenml.metadata.metadata_types.StorageSize)]

Extract metadata from the given pandas dataframe or series.

Args:
: df: The pandas dataframe or series to extract metadata from.

Returns:
: The extracted metadata as a dictionary.

#### load(data_type: Type[Any]) → DataFrame | Series

Reads pd.DataFrame or pd.Series from a .parquet or .csv file.

Args:
: data_type: The type of the data to read.

Raises:
: ImportError: If pyarrow or fastparquet is not installed.

Returns:
: The pandas dataframe or series.

#### save(df: DataFrame | Series) → None

Writes a pandas dataframe or series to the specified filename.

Args:
: df: The pandas dataframe or series to write.

#### save_visualizations(df: DataFrame | Series) → Dict[str, [VisualizationType](zenml.md#zenml.enums.VisualizationType)]

Save visualizations of the given pandas dataframe or series.

Args:
: df: The pandas dataframe or series to visualize.

Returns:
: A dictionary of visualization URIs and their types.

## Module contents

Initialization of the Pandas materializer.
