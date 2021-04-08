# Metadata

&lt;!DOCTYPE html&gt;

zenml.metadata package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.metadata.md)
  * * [zenml.metadata package](zenml.metadata.md)
      * [Submodules](zenml.metadata.md#submodules)
      * [zenml.metadata.metadata\_wrapper module](zenml.metadata.md#module-zenml.metadata.metadata_wrapper)
      * [zenml.metadata.metadata\_wrapper\_factory module](zenml.metadata.md#module-zenml.metadata.metadata_wrapper_factory)
      * [zenml.metadata.metadata\_wrapper\_test module](zenml.metadata.md#module-zenml.metadata.metadata_wrapper_test)
      * [zenml.metadata.mock\_metadata\_wrapper module](zenml.metadata.md#module-zenml.metadata.mock_metadata_wrapper)
      * [zenml.metadata.mysql\_metadata\_wrapper module](zenml.metadata.md#module-zenml.metadata.mysql_metadata_wrapper)
      * [zenml.metadata.sqlite\_metadata\_wrapper module](zenml.metadata.md#module-zenml.metadata.sqlite_metadata_wrapper)
      * [Module contents](zenml.metadata.md#module-zenml.metadata)
* [ « zenml.datasou...](zenml.datasources.md)
* [ zenml.pipelin... »](zenml.pipelines.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.metadata.rst.txt)

## zenml.metadata package[¶](zenml.metadata.md#zenml-metadata-package)

### Submodules[¶](zenml.metadata.md#submodules)

### zenml.metadata.metadata\_wrapper module[¶](zenml.metadata.md#module-zenml.metadata.metadata_wrapper)

 _class_ `zenml.metadata.metadata_wrapper.ZenMLMetadataStore`[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore)

Bases: `object` `RUN_TYPE_PROPERTY_NAME` _= 'run'_[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.RUN_TYPE_PROPERTY_NAME) `STORE_TYPE` _= None_[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.STORE_TYPE) _classmethod_ `from_config`\(_config: Dict_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.from_config)

Converts ZenML config to ZenML Metadata Store.Parameters

**config** \(_dict_\) – ZenML config block for metadata. `get_artifacts_by_component`\(_pipeline_, _component\_name: str_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.get_artifacts_by_component)Parameters

* **pipeline** \([_BasePipeline_](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)\) – a ZenML pipeline object
* **component\_name** –

 `get_artifacts_by_execution`\(_execution\_id_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.get_artifacts_by_execution)Parameters

**execution\_id** – `get_component_execution`\(_pipeline_, _component\_name: str_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.get_component_execution) `get_components_status`\(_pipeline_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.get_components_status)

Returns status of components in pipeline.Parameters

**pipeline** \([_BasePipeline_](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)\) – a ZenML pipeline object

Returns: dict of type { component\_name : component\_status } `get_pipeline_context`\(_pipeline_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.get_pipeline_context) `get_pipeline_executions`\(_pipeline_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.get_pipeline_executions)

Get executions of pipeline.Parameters

**pipeline** \([_BasePipeline_](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)\) – a ZenML pipeline object `get_pipeline_status`\(_pipeline_\) → str[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.get_pipeline_status)

Query metadata store to find status of pipeline.Parameters

**pipeline** \([_BasePipeline_](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)\) – a ZenML pipeline object _abstract_ `get_tfx_metadata_config`\(\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.get_tfx_metadata_config) _property_ `store`[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.store) `to_config`\(\) → Dict[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore.to_config)

Converts from ZenML Metadata store back to config.

### zenml.metadata.metadata\_wrapper\_factory module[¶](zenml.metadata.md#module-zenml.metadata.metadata_wrapper_factory)

Factory to register metadata\_wrapper classes to metadata\_wrappers _class_ `zenml.metadata.metadata_wrapper_factory.MetadataWrapperFactory`[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_factory.MetadataWrapperFactory)

Bases: `object`

Definition of MetadataWrapperFactory to track all metadata\_wrappers.

All metadata\_wrappers \(including custom metadata\_wrappers\) are to be registered here. `get_metadata_wrappers`\(\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_factory.MetadataWrapperFactory.get_metadata_wrappers) `get_single_metadata_wrapper`\(_key_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_factory.MetadataWrapperFactory.get_single_metadata_wrapper) `register_metadata_wrapper`\(_key_, _metadata\_wrapper\__\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_factory.MetadataWrapperFactory.register_metadata_wrapper)

### zenml.metadata.metadata\_wrapper\_test module[¶](zenml.metadata.md#module-zenml.metadata.metadata_wrapper_test)

 `zenml.metadata.metadata_wrapper_test.test_from_config`\(\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_test.test_from_config) `zenml.metadata.metadata_wrapper_test.test_get_artifacts_by_component`\(_repo_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_test.test_get_artifacts_by_component) `zenml.metadata.metadata_wrapper_test.test_get_artifacts_by_execution`\(\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_test.test_get_artifacts_by_execution) `zenml.metadata.metadata_wrapper_test.test_get_component_execution`\(_repo_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_test.test_get_component_execution) `zenml.metadata.metadata_wrapper_test.test_get_components_status`\(_repo_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_test.test_get_components_status) `zenml.metadata.metadata_wrapper_test.test_get_pipeline_context`\(_repo_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_test.test_get_pipeline_context) `zenml.metadata.metadata_wrapper_test.test_get_pipeline_executions`\(_repo_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_test.test_get_pipeline_executions) `zenml.metadata.metadata_wrapper_test.test_get_pipeline_status`\(_repo_\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_test.test_get_pipeline_status) `zenml.metadata.metadata_wrapper_test.test_metadata_init`\(\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_test.test_metadata_init) `zenml.metadata.metadata_wrapper_test.test_to_config`\(\)[¶](zenml.metadata.md#zenml.metadata.metadata_wrapper_test.test_to_config)

### zenml.metadata.mock\_metadata\_wrapper module[¶](zenml.metadata.md#module-zenml.metadata.mock_metadata_wrapper)

 _class_ `zenml.metadata.mock_metadata_wrapper.MockMetadataStore`[¶](zenml.metadata.md#zenml.metadata.mock_metadata_wrapper.MockMetadataStore)

Bases: [`zenml.metadata.metadata_wrapper.ZenMLMetadataStore`](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore) `STORE_TYPE` _= 'mock'_[¶](zenml.metadata.md#zenml.metadata.mock_metadata_wrapper.MockMetadataStore.STORE_TYPE) `get_tfx_metadata_config`\(\)[¶](zenml.metadata.md#zenml.metadata.mock_metadata_wrapper.MockMetadataStore.get_tfx_metadata_config)

### zenml.metadata.mysql\_metadata\_wrapper module[¶](zenml.metadata.md#module-zenml.metadata.mysql_metadata_wrapper)

 _class_ `zenml.metadata.mysql_metadata_wrapper.MySQLMetadataStore`\(_host: str_, _port: int_, _database: str_, _username: str_, _password: str_\)[¶](zenml.metadata.md#zenml.metadata.mysql_metadata_wrapper.MySQLMetadataStore)

Bases: [`zenml.metadata.metadata_wrapper.ZenMLMetadataStore`](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore) `STORE_TYPE` _= 'mysql'_[¶](zenml.metadata.md#zenml.metadata.mysql_metadata_wrapper.MySQLMetadataStore.STORE_TYPE) `get_tfx_metadata_config`\(\)[¶](zenml.metadata.md#zenml.metadata.mysql_metadata_wrapper.MySQLMetadataStore.get_tfx_metadata_config)

### zenml.metadata.sqlite\_metadata\_wrapper module[¶](zenml.metadata.md#module-zenml.metadata.sqlite_metadata_wrapper)

 _class_ `zenml.metadata.sqlite_metadata_wrapper.SQLiteMetadataStore`\(_uri: str_\)[¶](zenml.metadata.md#zenml.metadata.sqlite_metadata_wrapper.SQLiteMetadataStore)

Bases: [`zenml.metadata.metadata_wrapper.ZenMLMetadataStore`](zenml.metadata.md#zenml.metadata.metadata_wrapper.ZenMLMetadataStore) `STORE_TYPE` _= 'sqlite'_[¶](zenml.metadata.md#zenml.metadata.sqlite_metadata_wrapper.SQLiteMetadataStore.STORE_TYPE) `get_tfx_metadata_config`\(\)[¶](zenml.metadata.md#zenml.metadata.sqlite_metadata_wrapper.SQLiteMetadataStore.get_tfx_metadata_config)

### Module contents[¶](zenml.metadata.md#module-zenml.metadata)

 [Back to top](zenml.metadata.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


