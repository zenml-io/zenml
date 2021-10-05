# Materializers

&lt;!DOCTYPE html&gt;

zenml.materializers package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.materializers.md)
  * * [zenml.materializers package](zenml.materializers.md)
      * [Submodules](zenml.materializers.md#submodules)
      * [zenml.materializers.base\_materializer module](zenml.materializers.md#module-zenml.materializers.base_materializer)
      * [zenml.materializers.beam\_materializer module](zenml.materializers.md#module-zenml.materializers.beam_materializer)
      * [zenml.materializers.json\_materializer module](zenml.materializers.md#module-zenml.materializers.json_materializer)
      * [zenml.materializers.keras\_meterializer module](zenml.materializers.md#module-zenml.materializers.keras_meterializer)
      * [zenml.materializers.materializer\_factory module](zenml.materializers.md#module-zenml.materializers.materializer_factory)
      * [zenml.materializers.pandas\_materializer module](zenml.materializers.md#module-zenml.materializers.pandas_materializer)
      * [Module contents](zenml.materializers.md#module-zenml.materializers)
* [ « zenml.io package](zenml.io.md)
* [ zenml.metadat... »](zenml.metadata.md)
*  [Source](https://github.com/zenml-io/zenml/tree/154f041af2db9874b351cccd305478a173a7e939/docs/sphinx_docs/_build/html/_sources/zenml.materializers.rst.txt)

## zenml.materializers package[¶](zenml.materializers.md#zenml-materializers-package)

### Submodules[¶](zenml.materializers.md#submodules)

### zenml.materializers.base\_materializer module[¶](zenml.materializers.md#module-zenml.materializers.base_materializer)

 _class_ zenml.materializers.base\_materializer.BaseMaterializer\(_artifact_\)[¶](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)

Bases: `object`

Base Materializer to realize artifact data. TYPE\_NAME _= 'base'_[¶](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer.TYPE_NAME) _class_ zenml.materializers.base\_materializer.BaseMaterializerMeta\(_name_, _bases_, _dct_\)[¶](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializerMeta)

Bases: `type`

### zenml.materializers.beam\_materializer module[¶](zenml.materializers.md#module-zenml.materializers.beam_materializer)

 _class_ zenml.materializers.beam\_materializer.BeamMaterializer\(_artifact_\)[¶](zenml.materializers.md#zenml.materializers.beam_materializer.BeamMaterializer)

Bases: [`zenml.materializers.base_materializer.BaseMaterializer`](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)

Read to and from Beam artifacts. TYPE\_NAME _= 'beam'_[¶](zenml.materializers.md#zenml.materializers.beam_materializer.BeamMaterializer.TYPE_NAME) read\_text\(_pipeline_, _read\_header: bool = True_\)[¶](zenml.materializers.md#zenml.materializers.beam_materializer.BeamMaterializer.read_text)

Read from text write\_text\(_pipeline_, _shard\_name\_template=None_, _header=None_\)[¶](zenml.materializers.md#zenml.materializers.beam_materializer.BeamMaterializer.write_text)

Write from text

### zenml.materializers.json\_materializer module[¶](zenml.materializers.md#module-zenml.materializers.json_materializer)

 _class_ zenml.materializers.json\_materializer.JsonMaterializer\(_artifact_\)[¶](zenml.materializers.md#zenml.materializers.json_materializer.JsonMaterializer)

Bases: [`zenml.materializers.base_materializer.BaseMaterializer`](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)

Read data to and from JSON. TYPE\_NAME _= 'json'_[¶](zenml.materializers.md#zenml.materializers.json_materializer.JsonMaterializer.TYPE_NAME) read\_file\(_filename=None_\)[¶](zenml.materializers.md#zenml.materializers.json_materializer.JsonMaterializer.read_file)

Read JSON from filename. write\_file\(_data_, _filename=None_\)[¶](zenml.materializers.md#zenml.materializers.json_materializer.JsonMaterializer.write_file)

Write JSON to filename.

### zenml.materializers.keras\_meterializer module[¶](zenml.materializers.md#module-zenml.materializers.keras_meterializer)

 _class_ zenml.materializers.keras\_meterializer.KerasMaterializer\(_artifact_\)[¶](zenml.materializers.md#zenml.materializers.keras_meterializer.KerasMaterializer)

Bases: [`zenml.materializers.base_materializer.BaseMaterializer`](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)

Materializer to read Keras model. TYPE\_NAME _= 'keras'_[¶](zenml.materializers.md#zenml.materializers.keras_meterializer.KerasMaterializer.TYPE_NAME) read\_model\(\)[¶](zenml.materializers.md#zenml.materializers.keras_meterializer.KerasMaterializer.read_model) write\_model\(_model_\)[¶](zenml.materializers.md#zenml.materializers.keras_meterializer.KerasMaterializer.write_model)

### zenml.materializers.materializer\_factory module[¶](zenml.materializers.md#module-zenml.materializers.materializer_factory)

 _class_ zenml.materializers.materializer\_factory.MaterializerFactory\(_artifact_\)[¶](zenml.materializers.md#zenml.materializers.materializer_factory.MaterializerFactory)

Bases: `object`

A factory class which is used by the ZenML artifacts to keep track of different materializers get\_types\(\)[¶](zenml.materializers.md#zenml.materializers.materializer_factory.MaterializerFactory.get_types)

Get the materializer dictionary materializer\_types _= {'beam': &lt;class 'zenml.materializers.beam\_materializer.BeamMaterializer'&gt;, 'json': &lt;class 'zenml.materializers.json\_materializer.JsonMaterializer'&gt;, 'keras': &lt;class 'zenml.materializers.keras\_meterializer.KerasMaterializer'&gt;, 'pandas': &lt;class 'zenml.materializers.pandas\_materializer.PandasMaterializer'&gt;}_[¶](zenml.materializers.md#zenml.materializers.materializer_factory.MaterializerFactory.materializer_types) _classmethod_ register\_type\(_key_, _type\__\)[¶](zenml.materializers.md#zenml.materializers.materializer_factory.MaterializerFactory.register_type)

Register a new materializer in the factoryParameters

* **key** – str, which indicates the materializer used within the step
* **type** – a ZenML materializer object

### zenml.materializers.pandas\_materializer module[¶](zenml.materializers.md#module-zenml.materializers.pandas_materializer)

 _class_ zenml.materializers.pandas\_materializer.PandasMaterializer\(_artifact_\)[¶](zenml.materializers.md#zenml.materializers.pandas_materializer.PandasMaterializer)

Bases: [`zenml.materializers.base_materializer.BaseMaterializer`](zenml.materializers.md#zenml.materializers.base_materializer.BaseMaterializer)

Materializer to read data to and from pandas. TYPE\_NAME _= 'pandas'_[¶](zenml.materializers.md#zenml.materializers.pandas_materializer.PandasMaterializer.TYPE_NAME) read\_dataframe\(_filename=None_\)[¶](zenml.materializers.md#zenml.materializers.pandas_materializer.PandasMaterializer.read_dataframe) write\_dataframe\(_df_, _filename=None_\)[¶](zenml.materializers.md#zenml.materializers.pandas_materializer.PandasMaterializer.write_dataframe)

### Module contents[¶](zenml.materializers.md#module-zenml.materializers)

 [Back to top](zenml.materializers.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


