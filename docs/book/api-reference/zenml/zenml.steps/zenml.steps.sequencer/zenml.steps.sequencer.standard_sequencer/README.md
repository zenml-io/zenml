# Standard sequencer

&lt;!DOCTYPE html&gt;

zenml.steps.sequencer.standard\_sequencer package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](./)
  * * [zenml.steps.sequencer.standard\_sequencer package](./)
      * [Subpackages](./#subpackages)
      * [Submodules](./#submodules)
      * [zenml.steps.sequencer.standard\_sequencer.standard\_sequencer module](./#module-zenml.steps.sequencer.standard_sequencer.standard_sequencer)
      * [zenml.steps.sequencer.standard\_sequencer.utils module](./#module-zenml.steps.sequencer.standard_sequencer.utils)
      * [Module contents](./#module-zenml.steps.sequencer.standard_sequencer)
* [ « zenml.steps.s...](../)
* [ zenml.steps.s... »](zenml.steps.sequencer.standard_sequencer.methods.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.steps.sequencer.standard_sequencer.rst.txt)

## zenml.steps.sequencer.standard\_sequencer package[¶](./#zenml-steps-sequencer-standard-sequencer-package)

### Subpackages[¶](./#subpackages)

* [zenml.steps.sequencer.standard\_sequencer.methods package](zenml.steps.sequencer.standard_sequencer.methods.md)
  * [Submodules](zenml.steps.sequencer.standard_sequencer.methods.md#submodules)
  * [zenml.steps.sequencer.standard\_sequencer.methods.methods\_filling module](zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods.methods_filling)
  * [zenml.steps.sequencer.standard\_sequencer.methods.methods\_resampling module](zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods.methods_resampling)
  * [zenml.steps.sequencer.standard\_sequencer.methods.standard\_methods module](zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods.standard_methods)
  * [Module contents](zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods)

### Submodules[¶](./#submodules)

### zenml.steps.sequencer.standard\_sequencer.standard\_sequencer module[¶](./#module-zenml.steps.sequencer.standard_sequencer.standard_sequencer)

 _class_ `zenml.steps.sequencer.standard_sequencer.standard_sequencer.StandardSequencer`\(_timestamp\_column: str_, _category\_column: str = None_, _overwrite: Dict\[str, str\] = None_, _resampling\_freq: str = '1D'_, _gap\_threshold: int = 60000_, _sequence\_length: int = 4_, _sequence\_shift: int = 1_, _\*\*kwargs_\)[¶](./#zenml.steps.sequencer.standard_sequencer.standard_sequencer.StandardSequencer)

Bases: [`zenml.steps.sequencer.base_sequencer.BaseSequencerStep`](../#zenml.steps.sequencer.base_sequencer.BaseSequencerStep) `get_category_do_fn`\(\)[¶](./#zenml.steps.sequencer.standard_sequencer.standard_sequencer.StandardSequencer.get_category_do_fn)

Creates a class which inherits from beam.DoFn to add a categorical key to each datapointReturns

an instance of the beam.DoFn `get_combine_fn`\(\)[¶](./#zenml.steps.sequencer.standard_sequencer.standard_sequencer.StandardSequencer.get_combine_fn)

Creates a class which inherits from beam.CombineFn which processes sessions and extracts sequences from itReturns

an instance of the beam.CombineFn `get_timestamp_do_fn`\(\)[¶](./#zenml.steps.sequencer.standard_sequencer.standard_sequencer.StandardSequencer.get_timestamp_do_fn)

Creates a class which inherits from beam.DoFn to add the timestamp to each datapointReturns

an instance of the beam.DoFn `get_window`\(\)[¶](./#zenml.steps.sequencer.standard_sequencer.standard_sequencer.StandardSequencer.get_window)

Returns a selected beam windowing strategyReturns

the selected windowing strategy

### zenml.steps.sequencer.standard\_sequencer.utils module[¶](./#module-zenml.steps.sequencer.standard_sequencer.utils)

 `zenml.steps.sequencer.standard_sequencer.utils.array_to_value`\(_value_\)[¶](./#zenml.steps.sequencer.standard_sequencer.utils.array_to_value) `zenml.steps.sequencer.standard_sequencer.utils.convert_datetime_to_secs`\(_dt_\)[¶](./#zenml.steps.sequencer.standard_sequencer.utils.convert_datetime_to_secs) `zenml.steps.sequencer.standard_sequencer.utils.extract_sequences`\(_session_, _seq\_length_, _freq_, _shift_\)[¶](./#zenml.steps.sequencer.standard_sequencer.utils.extract_sequences) `zenml.steps.sequencer.standard_sequencer.utils.fill_defaults`\(_config_, _default\_config_, _schema_\)[¶](./#zenml.steps.sequencer.standard_sequencer.utils.fill_defaults) `zenml.steps.sequencer.standard_sequencer.utils.get_function_dict`\(_config_, _methods_\)[¶](./#zenml.steps.sequencer.standard_sequencer.utils.get_function_dict) `zenml.steps.sequencer.standard_sequencer.utils.get_output_dtype`\(_input\_dtype_, _method_, _params_\)[¶](./#zenml.steps.sequencer.standard_sequencer.utils.get_output_dtype) `zenml.steps.sequencer.standard_sequencer.utils.get_resample_output_dtype`\(_resampling\_config_, _schema_\)[¶](./#zenml.steps.sequencer.standard_sequencer.utils.get_resample_output_dtype) `zenml.steps.sequencer.standard_sequencer.utils.infer_schema`\(_schema_\)[¶](./#zenml.steps.sequencer.standard_sequencer.utils.infer_schema)

Function to infer a schema from input data. :param schema: Input dict mapping features to tf.Tensors.Returns

Dict mapping features to their respective data types.Return type

schema\_dict

### Module contents[¶](./#module-zenml.steps.sequencer.standard_sequencer)

 [Back to top](./)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


