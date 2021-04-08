# Datasources

&lt;!DOCTYPE html&gt;

zenml.datasources package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.datasources.md)
  * * [zenml.datasources package](zenml.datasources.md)
      * [Submodules](zenml.datasources.md#submodules)
      * [zenml.datasources.base\_datasource module](zenml.datasources.md#module-zenml.datasources.base_datasource)
      * [zenml.datasources.base\_datasource\_test module](zenml.datasources.md#module-zenml.datasources.base_datasource_test)
      * [zenml.datasources.bq\_datasource module](zenml.datasources.md#module-zenml.datasources.bq_datasource)
      * [zenml.datasources.csv\_datasource module](zenml.datasources.md#module-zenml.datasources.csv_datasource)
      * [zenml.datasources.image\_datasource module](zenml.datasources.md#module-zenml.datasources.image_datasource)
      * [zenml.datasources.json\_datasource module](zenml.datasources.md#module-zenml.datasources.json_datasource)
      * [zenml.datasources.numpy\_datasource module](zenml.datasources.md#module-zenml.datasources.numpy_datasource)
      * [zenml.datasources.pandas\_datasource module](zenml.datasources.md#module-zenml.datasources.pandas_datasource)
      * [zenml.datasources.postgres\_datasource module](zenml.datasources.md#zenml-datasources-postgres-datasource-module)
      * [Module contents](zenml.datasources.md#module-zenml.datasources)
* [ « zenml.compone...](zenml.components/zenml.components.transform_simple.md)
* [ zenml.metadat... »](zenml.metadata.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.datasources.rst.txt)

## zenml.datasources package[¶](zenml.datasources.md#zenml-datasources-package)

### Submodules[¶](zenml.datasources.md#submodules)

### zenml.datasources.base\_datasource module[¶](zenml.datasources.md#module-zenml.datasources.base_datasource)

Base Class for all ZenML datasources _class_ `zenml.datasources.base_datasource.BaseDatasource`\(_name: str_, _\_id: str = None_, _\*args_, _\*\*kwargs_\)[¶](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)

Bases: `object`

Base class for all ZenML datasources. Every ZenML datasource should override this class. _classmethod_ `from_config`\(_config: Dict_\)[¶](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource.from_config)

Convert from Data Step config to ZenML Datasource object. Data step is also populated and configuration set to parameters set in the config file. :param config: a DataStep config in dict-form \(probably loaded from YAML\). _abstract_ `get_data_step`\(\)[¶](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource.get_data_step) `get_datapoints`\(\)[¶](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource.get_datapoints)

Gets total number of datapoints in datasource `sample_data`\(_sample\_size: int = 100000_\)[¶](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource.sample_data)

Sampels data from datasource as a pandas DataFrame. :param sample\_size: \# of rows to sample. `to_config`\(\)[¶](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource.to_config)

Converts datasource to ZenML config block. `view_schema`\(\)[¶](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource.view_schema)

View schema of data flowing in pipeline. `view_statistics`\(_port_\)[¶](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource.view_statistics)

View statistics of data flowing in pipeline.Parameters

**port** \(_int_\) – Port at which to launch the statistics facet.

### zenml.datasources.base\_datasource\_test module[¶](zenml.datasources.md#module-zenml.datasources.base_datasource_test)

 `zenml.datasources.base_datasource_test.test_datasource_create`\(_repo_\)[¶](zenml.datasources.md#zenml.datasources.base_datasource_test.test_datasource_create) `zenml.datasources.base_datasource_test.test_get_data_file_paths`\(_repo_\)[¶](zenml.datasources.md#zenml.datasources.base_datasource_test.test_get_data_file_paths) `zenml.datasources.base_datasource_test.test_get_datapoints`\(_repo_\)[¶](zenml.datasources.md#zenml.datasources.base_datasource_test.test_get_datapoints) `zenml.datasources.base_datasource_test.test_get_datastep`\(\)[¶](zenml.datasources.md#zenml.datasources.base_datasource_test.test_get_datastep) `zenml.datasources.base_datasource_test.test_get_one_pipeline`\(_repo_\)[¶](zenml.datasources.md#zenml.datasources.base_datasource_test.test_get_one_pipeline) `zenml.datasources.base_datasource_test.test_sample_data`\(_repo_\)[¶](zenml.datasources.md#zenml.datasources.base_datasource_test.test_sample_data) `zenml.datasources.base_datasource_test.test_to_from_config`\(_equal\_datasources_\)[¶](zenml.datasources.md#zenml.datasources.base_datasource_test.test_to_from_config)

### zenml.datasources.bq\_datasource module[¶](zenml.datasources.md#module-zenml.datasources.bq_datasource)

BigQuery Datasource definition _class_ `zenml.datasources.bq_datasource.BigQueryDatasource`\(_name: str_, _query\_project: str_, _query\_dataset: str_, _query\_table: str_, _gcs\_location: str_, _query\_limit: Optional\[int\] = None_, _dest\_project: str = None_, _schema: Dict = None_, _\*\*kwargs_\)[¶](zenml.datasources.md#zenml.datasources.bq_datasource.BigQueryDatasource)

Bases: [`zenml.datasources.base_datasource.BaseDatasource`](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)

ZenML BigQuery datasource definition.

Use this for BigQuery training pipelines. `get_data_step`\(\)[¶](zenml.datasources.md#zenml.datasources.bq_datasource.BigQueryDatasource.get_data_step)

### zenml.datasources.csv\_datasource module[¶](zenml.datasources.md#module-zenml.datasources.csv_datasource)

CSv Datasource definition _class_ `zenml.datasources.csv_datasource.CSVDatasource`\(_name: str_, _path: str_, _schema: Dict = None_, _\*\*kwargs_\)[¶](zenml.datasources.md#zenml.datasources.csv_datasource.CSVDatasource)

Bases: [`zenml.datasources.base_datasource.BaseDatasource`](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)

ZenML CSV datasource definition.

Use this for CSV training pipelines. `get_data_step`\(\)[¶](zenml.datasources.md#zenml.datasources.csv_datasource.CSVDatasource.get_data_step)

### zenml.datasources.image\_datasource module[¶](zenml.datasources.md#module-zenml.datasources.image_datasource)

Image Datasource definition _class_ `zenml.datasources.image_datasource.ImageDatasource`\(_name: str = None_, _base\_path: str = None_, _schema: Dict = None_, _\*\*kwargs_\)[¶](zenml.datasources.md#zenml.datasources.image_datasource.ImageDatasource)

Bases: [`zenml.datasources.base_datasource.BaseDatasource`](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)

ZenML Image datasource definition.

Use this for image training pipelines. `get_data_step`\(\)[¶](zenml.datasources.md#zenml.datasources.image_datasource.ImageDatasource.get_data_step)

### zenml.datasources.json\_datasource module[¶](zenml.datasources.md#module-zenml.datasources.json_datasource)

JSON Datasource definition _class_ `zenml.datasources.json_datasource.JSONDatasource`\(_name: str_, _json\_obj_, _\*\*kwargs_\)[¶](zenml.datasources.md#zenml.datasources.json_datasource.JSONDatasource)

Bases: [`zenml.datasources.base_datasource.BaseDatasource`](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)

ZenML JSON datasource definition.

### zenml.datasources.numpy\_datasource module[¶](zenml.datasources.md#module-zenml.datasources.numpy_datasource)

Numpy Datasource definition _class_ `zenml.datasources.numpy_datasource.NumpyDatasource`\(_name: str_, _np\_array_, _\*\*kwargs_\)[¶](zenml.datasources.md#zenml.datasources.numpy_datasource.NumpyDatasource)

Bases: [`zenml.datasources.base_datasource.BaseDatasource`](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)

ZenML Numpy datasource definition.

### zenml.datasources.pandas\_datasource module[¶](zenml.datasources.md#module-zenml.datasources.pandas_datasource)

Pandas Datasource definition _class_ `zenml.datasources.pandas_datasource.PandasDatasource`\(_name: str_, _df_, _\*\*kwargs_\)[¶](zenml.datasources.md#zenml.datasources.pandas_datasource.PandasDatasource)

Bases: [`zenml.datasources.base_datasource.BaseDatasource`](zenml.datasources.md#zenml.datasources.base_datasource.BaseDatasource)

ZenML Pandas datasource definition.

### zenml.datasources.postgres\_datasource module[¶](zenml.datasources.md#zenml-datasources-postgres-datasource-module)

### Module contents[¶](zenml.datasources.md#module-zenml.datasources)

 [Back to top](zenml.datasources.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


