# zenml.integrations.pillow package

## Subpackages

* [zenml.integrations.pillow.materializers package](zenml.integrations.pillow.materializers.md)
  * [Submodules](zenml.integrations.pillow.materializers.md#submodules)
  * [zenml.integrations.pillow.materializers.pillow_image_materializer module](zenml.integrations.pillow.materializers.md#module-zenml.integrations.pillow.materializers.pillow_image_materializer)
    * [`PillowImageMaterializer`](zenml.integrations.pillow.materializers.md#zenml.integrations.pillow.materializers.pillow_image_materializer.PillowImageMaterializer)
      * [`PillowImageMaterializer.ASSOCIATED_ARTIFACT_TYPE`](zenml.integrations.pillow.materializers.md#zenml.integrations.pillow.materializers.pillow_image_materializer.PillowImageMaterializer.ASSOCIATED_ARTIFACT_TYPE)
      * [`PillowImageMaterializer.ASSOCIATED_TYPES`](zenml.integrations.pillow.materializers.md#zenml.integrations.pillow.materializers.pillow_image_materializer.PillowImageMaterializer.ASSOCIATED_TYPES)
      * [`PillowImageMaterializer.extract_metadata()`](zenml.integrations.pillow.materializers.md#zenml.integrations.pillow.materializers.pillow_image_materializer.PillowImageMaterializer.extract_metadata)
      * [`PillowImageMaterializer.load()`](zenml.integrations.pillow.materializers.md#zenml.integrations.pillow.materializers.pillow_image_materializer.PillowImageMaterializer.load)
      * [`PillowImageMaterializer.save()`](zenml.integrations.pillow.materializers.md#zenml.integrations.pillow.materializers.pillow_image_materializer.PillowImageMaterializer.save)
      * [`PillowImageMaterializer.save_visualizations()`](zenml.integrations.pillow.materializers.md#zenml.integrations.pillow.materializers.pillow_image_materializer.PillowImageMaterializer.save_visualizations)
  * [Module contents](zenml.integrations.pillow.materializers.md#module-zenml.integrations.pillow.materializers)

## Module contents

Initialization of the Pillow integration.

### *class* zenml.integrations.pillow.PillowIntegration

Bases: [`Integration`](zenml.integrations.md#zenml.integrations.integration.Integration)

Definition of Pillow integration for ZenML.

#### NAME *= 'pillow'*

#### REQUIREMENTS *: List[str]* *= ['Pillow>=9.2.0']*

#### *classmethod* activate() → None

Activates the integration.
