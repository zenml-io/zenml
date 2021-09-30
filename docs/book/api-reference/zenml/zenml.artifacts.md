# Artifacts

&lt;!DOCTYPE html&gt;

zenml.artifacts package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.artifacts.md)
  * * [zenml.artifacts package](zenml.artifacts.md)
      * [Subpackages](zenml.artifacts.md#subpackages)
      * [Submodules](zenml.artifacts.md#submodules)
      * [zenml.artifacts.base\_artifact module](zenml.artifacts.md#module-zenml.artifacts.base_artifact)
      * [Module contents](zenml.artifacts.md#module-zenml.artifacts)
* [ « zenml.artifac...](zenml.artifact_stores.md)
* [ zenml.artifac... »](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/zenml.artifacts.data_artifacts.html)
*  [Source](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/_sources/zenml.artifacts.rst.txt)

## zenml.artifacts package[¶](zenml.artifacts.md#zenml-artifacts-package)

### Subpackages[¶](zenml.artifacts.md#subpackages)

* [zenml.artifacts.data\_artifacts package](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/zenml.artifacts.data_artifacts.html)
  * [Submodules](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/zenml.artifacts.data_artifacts.html#submodules)
  * [zenml.artifacts.data\_artifacts.base\_data\_artifact module](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/zenml.artifacts.data_artifacts.html#module-zenml.artifacts.data_artifacts.base_data_artifact)
  * [zenml.artifacts.data\_artifacts.text\_artifact module](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/zenml.artifacts.data_artifacts.html#module-zenml.artifacts.data_artifacts.text_artifact)
  * [Module contents](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/zenml.artifacts.data_artifacts.html#module-zenml.artifacts.data_artifacts)

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

* TODO: Write about the reader/writer factories

 PROPERTIES _= {}_[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact.PROPERTIES) READER\_FACTORY _= &lt;zenml.artifacts.base\_artifact.IOFactory object&gt;_[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact.READER_FACTORY) TYPE\_NAME _= 'BaseArtifact'_[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact.TYPE_NAME) WRITER\_FACTORY _= &lt;zenml.artifacts.base\_artifact.IOFactory object&gt;_[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact.WRITER_FACTORY) get\_reader\(_key_\)[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact.get_reader) get\_writer\(_key_\)[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact.get_writer) _classmethod_ register\_reader\(_key_, _func_\)[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact.register_reader) _classmethod_ register\_writer\(_key_, _func_\)[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.BaseArtifact.register_writer) _class_ zenml.artifacts.base\_artifact.IOFactory[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.IOFactory)

Bases: `object`

A factory class which is used by the ZenML artifacts to keep track of different read/write methods get\_single\_type\(_key_\)[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.IOFactory.get_single_type)

Get a single reader/writer based on the key :param key: str, which indicates which type of method will be used within

> the step

Returns

The corresponding writer function within the factory get\_types\(\)[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.IOFactory.get_types)

Get the whole reader/writer dictionary register\_type\(_key_, _type\__\)[¶](zenml.artifacts.md#zenml.artifacts.base_artifact.IOFactory.register_type)

Register a new writer in the factoryParameters

* **key** – str, which indicates which type of method
* **type** – a function which is used to read/write the artifact within the context of a step

### Module contents[¶](zenml.artifacts.md#module-zenml.artifacts)

 [Back to top](zenml.artifacts.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


