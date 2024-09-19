# zenml.integrations.pillow.materializers package

## Submodules

## zenml.integrations.pillow.materializers.pillow_image_materializer module

Materializer for Pillow Image objects.

### *class* zenml.integrations.pillow.materializers.pillow_image_materializer.PillowImageMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`BaseMaterializer`](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)

Materializer for Image.Image objects.

This materializer takes a PIL image object and returns a PIL image object.
It handles all the source image formats supported by PIL as listed here:
[https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html).

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'DataArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'PIL.Image.Image'>,)*

#### extract_metadata(image: Image) → Dict[str, MetadataType]

Extract metadata from the given Image object.

Args:
: image: The Image object to extract metadata from.

Returns:
: The extracted metadata as a dictionary.

#### load(data_type: Type[Image]) → Image

Read from artifact store.

Args:
: data_type: An Image.Image type.

Returns:
: An Image.Image object.

#### save(image: Image) → None

Write to artifact store.

Args:
: image: An Image.Image object.

#### save_visualizations(image: Image) → Dict[str, [VisualizationType](zenml.md#zenml.enums.VisualizationType)]

Finds and saves the given image as a visualization.

Args:
: image: The image to save as a visualization.

Returns:
: A dictionary of visualization URIs and their types.

## Module contents

Initialization of the Pillow materializer.
