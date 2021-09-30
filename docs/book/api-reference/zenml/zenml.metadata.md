# Metadata

&lt;!DOCTYPE html&gt;

zenml.metadata package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.metadata.md)
  * * [zenml.metadata package](zenml.metadata.md)
      * [Submodules](zenml.metadata.md#submodules)
      * [zenml.metadata.base\_metadata\_store module](zenml.metadata.md#module-zenml.metadata.base_metadata_store)
      * [zenml.metadata.base\_metadata\_wrapper\_test module](zenml.metadata.md#zenml-metadata-base-metadata-wrapper-test-module)
      * [zenml.metadata.mock\_metadata\_wrapper module](zenml.metadata.md#module-zenml.metadata.mock_metadata_wrapper)
      * [zenml.metadata.mysql\_metadata\_wrapper module](zenml.metadata.md#module-zenml.metadata.mysql_metadata_wrapper)
      * [zenml.metadata.sqlite\_metadata\_wrapper module](zenml.metadata.md#module-zenml.metadata.sqlite_metadata_wrapper)
      * [Module contents](zenml.metadata.md#module-zenml.metadata)
* [ « zenml.io package](zenml.io.md)
* [ zenml.orchest... »](zenml.orchestrators/)
*  [Source](https://github.com/zenml-io/zenml/tree/25d9c27ff1e23c67d7247993006f83f8404d83c4/docs/sphinx_docs/_build/html/_sources/zenml.metadata.rst.txt)

## zenml.metadata package[¶](zenml.metadata.md#zenml-metadata-package)

### Submodules[¶](zenml.metadata.md#submodules)

### zenml.metadata.base\_metadata\_store module[¶](zenml.metadata.md#module-zenml.metadata.base_metadata_store)

 _class_ zenml.metadata.base\_metadata\_store.BaseMetadataStore\(_\*_, _uuid: uuid.UUID = None_\)[¶](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore)

Bases: [`zenml.core.base_component.BaseComponent`](zenml.core.md#zenml.core.base_component.BaseComponent)

Metadata store base class to track metadata of zenml first class citizens. _class_ Config[¶](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore.Config)

Bases: `object`

Configuration of settings. env\_prefix _= 'zenml\_metadata\_store\_'_[¶](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore.Config.env_prefix) get\_artifacts\_by\_component\(_pipeline_, _component\_name: str_\)[¶](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore.get_artifacts_by_component)

Gets artifacts by component name.Parameters

* **pipeline** \([_BasePipeline_](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)\) – a ZenML pipeline object
* **component\_name** –
* **component\_name** – Text:

Returns: get\_components\_status\(_pipeline_\)[¶](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore.get_components_status)

Returns status of components in pipeline.Parameters

**pipeline** \([_BasePipeline_](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)\) – a ZenML pipeline object

Returns: dict of type { component\_name : component\_status }

Returns: get\_pipeline\_context\(_pipeline_\)[¶](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore.get_pipeline_context)

Get pipeline context.Parameters

**pipeline** –

Returns: get\_pipeline\_executions\(_pipeline_\)[¶](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore.get_pipeline_executions)

Get executions of pipeline.Parameters

**pipeline** \([_BasePipeline_](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)\) – a ZenML pipeline object

Returns: get\_pipeline\_status\(_pipeline_\) → str[¶](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore.get_pipeline_status)

Query metadata store to find status of pipeline.Parameters

**pipeline** \([_BasePipeline_](zenml.pipelines.md#zenml.pipelines.base_pipeline.BasePipeline)\) – a ZenML pipeline object

Returns: get\_serialization\_dir\(\)[¶](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore.get_serialization_dir)

Gets the local path where artifacts are stored. _abstract_ get\_tfx\_metadata\_config\(\)[¶](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore.get_tfx_metadata_config)

Return tfx metadata config. _property_ store[¶](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore.store)

General property that hooks into TFX metadata store.

### zenml.metadata.base\_metadata\_wrapper\_test module[¶](zenml.metadata.md#zenml-metadata-base-metadata-wrapper-test-module)

### zenml.metadata.mock\_metadata\_wrapper module[¶](zenml.metadata.md#module-zenml.metadata.mock_metadata_wrapper)

 _class_ zenml.metadata.mock\_metadata\_wrapper.MockMetadataStore\(_\*_, _uuid: uuid.UUID = None_\)[¶](zenml.metadata.md#zenml.metadata.mock_metadata_wrapper.MockMetadataStore)

Bases: [`zenml.metadata.base_metadata_store.BaseMetadataStore`](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore)

Mock metadata store. get\_tfx\_metadata\_config\(\)[¶](zenml.metadata.md#zenml.metadata.mock_metadata_wrapper.MockMetadataStore.get_tfx_metadata_config)

Return tfx metadata config for mock metadata store.

### zenml.metadata.mysql\_metadata\_wrapper module[¶](zenml.metadata.md#module-zenml.metadata.mysql_metadata_wrapper)

 _class_ zenml.metadata.mysql\_metadata\_wrapper.MySQLMetadataStore\(_\*_, _uuid: uuid.UUID = None_, _host: str_, _port: int_, _database: str_, _username: str_, _password: str_\)[¶](zenml.metadata.md#zenml.metadata.mysql_metadata_wrapper.MySQLMetadataStore)

Bases: [`zenml.metadata.base_metadata_store.BaseMetadataStore`](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore)

MySQL backend for ZenML metadata store. database_: str_[¶](zenml.metadata.md#zenml.metadata.mysql_metadata_wrapper.MySQLMetadataStore.database) get\_tfx\_metadata\_config\(\)[¶](zenml.metadata.md#zenml.metadata.mysql_metadata_wrapper.MySQLMetadataStore.get_tfx_metadata_config)

Return tfx metadata config for mysql metadata store. host_: str_[¶](zenml.metadata.md#zenml.metadata.mysql_metadata_wrapper.MySQLMetadataStore.host) password_: str_[¶](zenml.metadata.md#zenml.metadata.mysql_metadata_wrapper.MySQLMetadataStore.password) port_: int_[¶](zenml.metadata.md#zenml.metadata.mysql_metadata_wrapper.MySQLMetadataStore.port) username_: str_[¶](zenml.metadata.md#zenml.metadata.mysql_metadata_wrapper.MySQLMetadataStore.username)

### zenml.metadata.sqlite\_metadata\_wrapper module[¶](zenml.metadata.md#module-zenml.metadata.sqlite_metadata_wrapper)

 _class_ zenml.metadata.sqlite\_metadata\_wrapper.SQLiteMetadataStore\(_\*_, _uuid: uuid.UUID = None_, _uri: str_\)[¶](zenml.metadata.md#zenml.metadata.sqlite_metadata_wrapper.SQLiteMetadataStore)

Bases: [`zenml.metadata.base_metadata_store.BaseMetadataStore`](zenml.metadata.md#zenml.metadata.base_metadata_store.BaseMetadataStore)

SQLite backend for ZenML metadata store. get\_tfx\_metadata\_config\(\)[¶](zenml.metadata.md#zenml.metadata.sqlite_metadata_wrapper.SQLiteMetadataStore.get_tfx_metadata_config)

Return tfx metadata config for sqlite metadata store. uri_: str_[¶](zenml.metadata.md#zenml.metadata.sqlite_metadata_wrapper.SQLiteMetadataStore.uri) _classmethod_ uri\_must\_be\_local\(_v_\)[¶](zenml.metadata.md#zenml.metadata.sqlite_metadata_wrapper.SQLiteMetadataStore.uri_must_be_local)

Validator to ensure uri is local

### Module contents[¶](zenml.metadata.md#module-zenml.metadata)

 [Back to top](zenml.metadata.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


