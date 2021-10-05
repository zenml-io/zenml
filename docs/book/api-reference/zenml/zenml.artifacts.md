# Artifacts

&lt;!DOCTYPE html&gt;

zenml.artifacts package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.artifacts.md)
  * * [zenml.artifacts package](zenml.artifacts.md)
      * [Submodules](zenml.artifacts.md#submodules)
      * [zenml.artifacts.base\_artifact module](zenml.artifacts.md#module-zenml.artifacts.base_artifact)
      * [zenml.artifacts.data\_artifact module](zenml.artifacts.md#module-zenml.artifacts.data_artifact)
      * [zenml.artifacts.model\_artifact module](zenml.artifacts.md#module-zenml.artifacts.model_artifact)
      * [Module contents](zenml.artifacts.md#module-zenml.artifacts)
* [ « zenml.artifac...](zenml.artifact_stores.md)
* [ zenml.cli package »](zenml.cli.md)
*  [Source](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/_sources/zenml.artifacts.rst.txt)

## zenml.artifacts package[¶](zenml.artifacts.md#zenml-artifacts-package)

### Submodules[¶](zenml.artifacts.md#submodules)

### zenml.artifacts.base\_artifact module[¶](zenml.artifacts.md#module-zenml.artifacts.base_artifact)

 _class_ zenml.artifacts.base\_artifact.BaseArtifact\(_mlmd\_artifact\_type: Optional\[ml\_metadata.proto.metadata\_store\_pb2.ArtifactType\] = None_\)[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact)

Bases: `tfx.types.artifact.Artifact`

Base class for all ZenML artifacts.

Every implementation of an artifact needs to inherit this class.

While inheriting from this class there are a few things to consider:

* Upon creation, each artifact class needs to be given a unique TYPE\_NAME.
* Your artifact can feature different properties under the parameter

  PROPERTIES which will be tracked throughout your pipeline runs.

* TODO \[MEDIUM\]: Write about the materializers

 PROPERTIES _= {}_[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact.PROPERTIES) TYPE\_NAME _= 'BaseArtifact'_[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact.TYPE_NAME) _property_ materializers_:_ [_zenml.materializers.materializer\_factory.MaterializerFactory_](zenml.materializers.md#zenml.materializers.materializer_factory.MaterializerFactory)[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact.materializers)

### zenml.artifacts.data\_artifact module[¶](zenml.artifacts.md#module-zenml.artifacts.data_artifact)

 _class_ zenml.artifacts.data\_artifact.DataArtifact\(_mlmd\_artifact\_type: Optional\[ml\_metadata.proto.metadata\_store\_pb2.ArtifactType\] = None_\)[¶](zenml.artifacts.md#zenml.artifacts.data_artifact.DataArtifact)

Bases: [`zenml.artifacts.base_artifact.BaseArtifact`](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact)

Base class for any ZenML data artifact

The custom properties include a property to hold split names PROPERTIES _= {'split\_names': PropertyType.STRING}_[¶](zenml.artifacts.md#zenml.artifacts.data_artifact.DataArtifact.PROPERTIES) TYPE\_NAME _= 'data\_artifact'_[¶](zenml.artifacts.md#zenml.artifacts.data_artifact.DataArtifact.TYPE_NAME)

### zenml.artifacts.model\_artifact module[¶](zenml.artifacts.md#module-zenml.artifacts.model_artifact)

 _class_ zenml.artifacts.model\_artifact.ModelArtifact\(_mlmd\_artifact\_type: Optional\[ml\_metadata.proto.metadata\_store\_pb2.ArtifactType\] = None_\)[¶](zenml.artifacts.md#zenml.artifacts.model_artifact.ModelArtifact)

Bases: [`zenml.artifacts.base_artifact.BaseArtifact`](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact) TYPE\_NAME _= 'model\_artifact'_[¶](zenml.artifacts.md#zenml.artifacts.model_artifact.ModelArtifact.TYPE_NAME)

### Module contents[¶](zenml.artifacts.md#module-zenml.artifacts)

 [Back to top](zenml.artifacts.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


