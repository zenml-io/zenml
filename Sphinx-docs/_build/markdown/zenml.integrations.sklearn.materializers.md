# zenml.integrations.sklearn.materializers package

## Submodules

## zenml.integrations.sklearn.materializers.sklearn_materializer module

Implementation of the sklearn materializer.

### *class* zenml.integrations.sklearn.materializers.sklearn_materializer.SklearnMaterializer(uri: str, artifact_store: [BaseArtifactStore](zenml.artifact_stores.md#zenml.artifact_stores.base_artifact_store.BaseArtifactStore) | None = None)

Bases: [`CloudpickleMaterializer`](zenml.materializers.md#zenml.materializers.cloudpickle_materializer.CloudpickleMaterializer)

Materializer to read data to and from sklearn.

#### ASSOCIATED_ARTIFACT_TYPE *: ClassVar[[ArtifactType](zenml.md#zenml.enums.ArtifactType)]* *= 'ModelArtifact'*

#### ASSOCIATED_TYPES *: ClassVar[Tuple[Type[Any], ...]]* *= (<class 'sklearn.base.BaseEstimator'>, <class 'sklearn.base.ClassifierMixin'>, <class 'sklearn.base.ClusterMixin'>, <class 'sklearn.base.BiclusterMixin'>, <class 'sklearn.base.OutlierMixin'>, <class 'sklearn.base.RegressorMixin'>, <class 'sklearn.base.MetaEstimatorMixin'>, <class 'sklearn.base.MultiOutputMixin'>, <class 'sklearn.base.DensityMixin'>, <class 'sklearn.base.TransformerMixin'>)*

## Module contents

Initialization of the sklearn materializer.
