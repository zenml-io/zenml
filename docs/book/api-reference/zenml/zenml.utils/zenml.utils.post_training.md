# Post training

&lt;!DOCTYPE html&gt;

zenml.utils.post\_training package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.utils.post_training.md)
  * * [zenml.utils.post\_training package](zenml.utils.post_training.md)
      * [Submodules](zenml.utils.post_training.md#submodules)
      * [zenml.utils.post\_training.compare module](zenml.utils.post_training.md#module-zenml.utils.post_training.compare)
      * [zenml.utils.post\_training.post\_training\_utils module](zenml.utils.post_training.md#module-zenml.utils.post_training.post_training_utils)
      * [Module contents](zenml.utils.post_training.md#module-zenml.utils.post_training)
* [ « zenml.utils package](./)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.utils.post_training.rst.txt)

## zenml.utils.post\_training package[¶](zenml.utils.post_training.md#zenml-utils-post-training-package)

### Submodules[¶](zenml.utils.post_training.md#submodules)

### zenml.utils.post\_training.compare module[¶](zenml.utils.post_training.md#module-zenml.utils.post_training.compare)

 _class_ `zenml.utils.post_training.compare.Application`\(_\*\*params_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.compare.Application)

Bases: `param.parameterized.Parameterized`

params\(hyperparameter\_selector=ListSelector, performance\_metric\_selector=ObjectSelector, pipeline\_run\_selector=ListSelector, slicing\_metric\_selector=ObjectSelector, name=String\) \[1;32mParameters of ‘Application’ =========================== \[0m \[1;31mParameters changed from their default values are marked in red.\[0m \[1;36mSoft bound values are marked in cyan.\[0m C/V= Constant/Variable, RO/RW = ReadOnly/ReadWrite, AN=Allow None

\[1;34mName Value Type Mode \[0m

hyperparameter\_selector \[\] ListSelector V RW performance\_metric\_selector None ObjectSelector V RW pipeline\_run\_selector \[\] ListSelector V RW slicing\_metric\_selector ‘’ ObjectSelector V RW

\[1;32mParameter docstrings: =====================\[0m

\[1;34mhyperparameter\_selector: &lt; No docstring available &gt;\[0m \[1;31mperformance\_metric\_selector: &lt; No docstring available &gt;\[0m \[1;34mpipeline\_run\_selector: &lt; No docstring available &gt;\[0m \[1;31mslicing\_metric\_selector: &lt; No docstring available &gt;\[0m `hyperparameter_selector` _= \[\]_[¶](zenml.utils.post_training.md#zenml.utils.post_training.compare.Application.hyperparameter_selector) `name` _= 'Application'_[¶](zenml.utils.post_training.md#zenml.utils.post_training.compare.Application.name) `parameter_graph`\(\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.compare.Application.parameter_graph) `performance_graph`\(\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.compare.Application.performance_graph) `performance_metric_selector` _= None_[¶](zenml.utils.post_training.md#zenml.utils.post_training.compare.Application.performance_metric_selector) `pipeline_run_selector` _= \[\]_[¶](zenml.utils.post_training.md#zenml.utils.post_training.compare.Application.pipeline_run_selector) `slicing_metric_selector` _= ''_[¶](zenml.utils.post_training.md#zenml.utils.post_training.compare.Application.slicing_metric_selector) `zenml.utils.post_training.compare.generate_interface`\(\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.compare.generate_interface) `zenml.utils.post_training.compare.parse_metrics`\(_d_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.compare.parse_metrics)

### zenml.utils.post\_training.post\_training\_utils module[¶](zenml.utils.post_training.md#module-zenml.utils.post_training.post_training_utils)

 `zenml.utils.post_training.post_training_utils.convert_data_to_numpy`\(_dataset_, _sample\_size_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.convert_data_to_numpy)

Takes tf.data.Dataset and converts to numpy array.Parameters

* **dataset** – a tf.data.Dataset object
* **sample\_size** – number of rows to limit to

 `zenml.utils.post_training.post_training_utils.convert_raw_dataset_to_pandas`\(_dataset_, _spec_, _sample\_size_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.convert_raw_dataset_to_pandas)

Takes tf.data.Dataset and converts to a Pandas DataFrame.Parameters

* **dataset** – a tf.data.Dataset object
* **spec** – the spec to parse from
* **sample\_size** – number of rows to limit to

 `zenml.utils.post_training.post_training_utils.create_new_cell`\(_contents_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.create_new_cell)

Creates new cell in jupyter notebook.Parameters

**contents** – contents of cell. `zenml.utils.post_training.post_training_utils.detect_anomalies`\(_stats\_uri: str_, _schema\_uri: str_, _split\_name: str_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.detect_anomalies) `zenml.utils.post_training.post_training_utils.evaluate_single_pipeline`\(_pipeline_, _trainer\_component\_name: str = None_, _evaluator\_component\_name: str = None_, _magic: bool = False_, _port: int = 0_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.evaluate_single_pipeline)Parameters

* **pipeline** – A ZenML pipeline
* **trainer\_component\_name** – name of trainer component.
* **evaluator\_component\_name** – name of evaluator component.
* **magic** – Whether to create an in-place cell in a jupyter env or not.
* **port** – At which port to create the jupyter notebook.

 `zenml.utils.post_training.post_training_utils.get_eval_block`\(_eval\_dir_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.get_eval_block) `zenml.utils.post_training.post_training_utils.get_feature_spec_from_schema`\(_schema\_uri_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.get_feature_spec_from_schema)

Get schema artifact from pipelineParameters

**schema\_uri** – path to schema `zenml.utils.post_training.post_training_utils.get_parsed_dataset`\(_dataset_, _spec_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.get_parsed_dataset)

Takes tf.data.Dataset and parses it based on specParameters

* **dataset** – a tf.data.Dataset object
* **spec** – the spec to parse from

 `zenml.utils.post_training.post_training_utils.get_schema_proto`\(_artifact\_uri: str_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.get_schema_proto) `zenml.utils.post_training.post_training_utils.get_statistics_dataset_dict`\(_stats\_uri: str_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.get_statistics_dataset_dict)

Get DatasetFeatureStatisticsList from stats URI `zenml.utils.post_training.post_training_utils.get_statistics_html`\(_stats\_dict_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.get_statistics_html)Parameters

**stats\_dict** – `zenml.utils.post_training.post_training_utils.get_tensorboard_block`\(_log\_dir_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.get_tensorboard_block) `zenml.utils.post_training.post_training_utils.launch_compare_tool`\(_port: int = 0_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.launch_compare_tool)

Launches compare tool for comparing multiple training pipelines. `zenml.utils.post_training.post_training_utils.view_schema`\(_uri: str_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.view_schema)

View schema .Parameters

**uri** – URI to schema. `zenml.utils.post_training.post_training_utils.view_statistics`\(_artifact\_uri_, _magic: bool = False_, _port: int = 0_\)[¶](zenml.utils.post_training.md#zenml.utils.post_training.post_training_utils.view_statistics)

View statistics in HTML.Parameters

* **artifact\_uri** \(_Text_\) –
* **magic** \(_bool_\) –
* **port** \(_int_\) – Port at which to launch the visualization.

### Module contents[¶](zenml.utils.post_training.md#module-zenml.utils.post_training)

 [Back to top](zenml.utils.post_training.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


