# Sequencer

&lt;!DOCTYPE html&gt;

zenml.steps.sequencer package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](./)
  * * [zenml.steps.sequencer package](./)
      * [Subpackages](./#subpackages)
      * [Submodules](./#submodules)
      * [zenml.steps.sequencer.base\_sequencer module](./#module-zenml.steps.sequencer.base_sequencer)
      * [Module contents](./#module-zenml.steps.sequencer)
* [ « zenml.steps.p...](../zenml.steps.preprocesser/zenml.steps.preprocesser.standard_preprocesser/zenml.steps.preprocesser.standard_preprocesser.methods.md)
* [ zenml.steps.s... »](zenml.steps.sequencer.standard_sequencer/)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.steps.sequencer.rst.txt)

## zenml.steps.sequencer package[¶](./#zenml-steps-sequencer-package)

### Subpackages[¶](./#subpackages)

* [zenml.steps.sequencer.standard\_sequencer package](zenml.steps.sequencer.standard_sequencer/)
  * [Subpackages](zenml.steps.sequencer.standard_sequencer/#subpackages)
    * [zenml.steps.sequencer.standard\_sequencer.methods package](zenml.steps.sequencer.standard_sequencer/zenml.steps.sequencer.standard_sequencer.methods.md)
      * [Submodules](zenml.steps.sequencer.standard_sequencer/zenml.steps.sequencer.standard_sequencer.methods.md#submodules)
      * [zenml.steps.sequencer.standard\_sequencer.methods.methods\_filling module](zenml.steps.sequencer.standard_sequencer/zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods.methods_filling)
      * [zenml.steps.sequencer.standard\_sequencer.methods.methods\_resampling module](zenml.steps.sequencer.standard_sequencer/zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods.methods_resampling)
      * [zenml.steps.sequencer.standard\_sequencer.methods.standard\_methods module](zenml.steps.sequencer.standard_sequencer/zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods.standard_methods)
      * [Module contents](zenml.steps.sequencer.standard_sequencer/zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods)
  * [Submodules](zenml.steps.sequencer.standard_sequencer/#submodules)
  * [zenml.steps.sequencer.standard\_sequencer.standard\_sequencer module](zenml.steps.sequencer.standard_sequencer/#module-zenml.steps.sequencer.standard_sequencer.standard_sequencer)
  * [zenml.steps.sequencer.standard\_sequencer.utils module](zenml.steps.sequencer.standard_sequencer/#module-zenml.steps.sequencer.standard_sequencer.utils)
  * [Module contents](zenml.steps.sequencer.standard_sequencer/#module-zenml.steps.sequencer.standard_sequencer)

### Submodules[¶](./#submodules)

### zenml.steps.sequencer.base\_sequencer module[¶](./#module-zenml.steps.sequencer.base_sequencer)

 _class_ `zenml.steps.sequencer.base_sequencer.BaseSequencerStep`\(_statistics: tensorflow\_metadata.proto.v0.statistics\_pb2.DatasetFeatureStatisticsList = None_, _schema: tensorflow\_metadata.proto.v0.schema\_pb2.Schema = None_, _\*\*kwargs_\)[¶](./#zenml.steps.sequencer.base_sequencer.BaseSequencerStep)

Bases: [`zenml.steps.base_step.BaseStep`](../#zenml.steps.base_step.BaseStep)

Base class for all sequencer steps. These steps are used to specify transformation and filling operations on timeseries datasets that occur before the data preprocessing takes place. `STEP_TYPE` _= 'sequencer'_[¶](./#zenml.steps.sequencer.base_sequencer.BaseSequencerStep.STEP_TYPE) _abstract_ `get_category_do_fn`\(\)[¶](./#zenml.steps.sequencer.base_sequencer.BaseSequencerStep.get_category_do_fn)

In ZenML, you have the option to split your data based on a categorical feature before the actual sequencing happens. This is especially helpful if you are dealing with a joint dataset \(i.e dataset featuring multiple assets in the field, but you want to sequence on an asset-level\)

Similar to get\_timestamp\_do\_fn, you need to implement a method, which returns an instance of a beam.DoFn class. This beam.DoFn should be responsible for extracting the category of a datapoint and add it to the datapoint and return it. For a practical example, you can check our StandardSequencer. _abstract_ `get_combine_fn`\(\)[¶](./#zenml.steps.sequencer.base_sequencer.BaseSequencerStep.get_combine_fn)

Once the data is split into sessions \(and possibly categories too\), it needs to be processed in order to extract sequences from the sessions.

This method needs to return an instance of beam.CombineFn class, which processes the accumulated datapoints and extracts desired sequences. You can check out our StandardSequencer for a practical example. _abstract_ `get_timestamp_do_fn`\(\)[¶](./#zenml.steps.sequencer.base_sequencer.BaseSequencerStep.get_timestamp_do_fn)

The process of sequencing is highly dependent on the format of your data. For instance, the timestamp of a single datapoint can be infused within the datapoint in various shapes or forms.

It is impossible to find THE one solution which would be able to parse all the different variants of timestamps and that is why we exposed this method.

Through this method, you have access to all of the instance variables of your step and all you have to do is to return an instance of a beam.DoFn which returns a TimestampedValue. You can check our StandardSequencer for a practical example. _abstract_ `get_window`\(\)[¶](./#zenml.steps.sequencer.base_sequencer.BaseSequencerStep.get_window)

This method needs to return the desired windowing strategy for the beam pipeline.

### Module contents[¶](./#module-zenml.steps.sequencer)

 [Back to top](./)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


