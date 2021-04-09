# Sequencer

&lt;!DOCTYPE html&gt;

zenml.components.sequencer package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.components.sequencer.md)
  * * [zenml.components.sequencer package](zenml.components.sequencer.md)
      * [Submodules](zenml.components.sequencer.md#submodules)
      * [zenml.components.sequencer.component module](zenml.components.sequencer.md#module-zenml.components.sequencer.component)
      * [zenml.components.sequencer.constants module](zenml.components.sequencer.md#module-zenml.components.sequencer.constants)
      * [zenml.components.sequencer.executor module](zenml.components.sequencer.md#module-zenml.components.sequencer.executor)
      * [zenml.components.sequencer.utils module](zenml.components.sequencer.md#module-zenml.components.sequencer.utils)
      * [Module contents](zenml.components.sequencer.md#module-zenml.components.sequencer)
* [ « zenml.compone...](zenml.components.pusher.md)
* [ zenml.compone... »](zenml.components.split_gen.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.components.sequencer.rst.txt)

## zenml.components.sequencer package[¶](zenml.components.sequencer.md#zenml-components-sequencer-package)

### Submodules[¶](zenml.components.sequencer.md#submodules)

### zenml.components.sequencer.component module[¶](zenml.components.sequencer.md#module-zenml.components.sequencer.component)

 _class_ `zenml.components.sequencer.component.Sequencer`\(_source: str_, _source\_args: Dict\[str, Any\]_, _input\_examples: tfx.types.channel.Channel_, _statistics: tfx.types.channel.Channel = None_, _schema: tfx.types.channel.Channel = None_\)[¶](zenml.components.sequencer.md#zenml.components.sequencer.component.Sequencer)

Bases: `tfx.dsl.components.base.base_component.BaseComponent` `EXECUTOR_SPEC` _= &lt;tfx.dsl.components.base.executor\_spec.ExecutorClassSpec object&gt;_[¶](zenml.components.sequencer.md#zenml.components.sequencer.component.Sequencer.EXECUTOR_SPEC) `SPEC_CLASS`[¶](zenml.components.sequencer.md#zenml.components.sequencer.component.Sequencer.SPEC_CLASS)

alias of [`SequencerComponentSpec`](zenml.components.sequencer.md#zenml.components.sequencer.component.SequencerComponentSpec) _class_ `zenml.components.sequencer.component.SequencerComponentSpec`\(_\*\*kwargs_\)[¶](zenml.components.sequencer.md#zenml.components.sequencer.component.SequencerComponentSpec)

Bases: `tfx.types.component_spec.ComponentSpec`

Sequencer component spec. `INPUTS` _= {'input\_examples': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Examples'&gt;\), 'schema': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Schema'&gt;\), 'statistics': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.ExampleStatistics'&gt;\)}_[¶](zenml.components.sequencer.md#zenml.components.sequencer.component.SequencerComponentSpec.INPUTS) `OUTPUTS` _= {'output\_examples': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Examples'&gt;\)}_[¶](zenml.components.sequencer.md#zenml.components.sequencer.component.SequencerComponentSpec.OUTPUTS) `PARAMETERS` _= {'args': ExecutionParameter\(type: typing.Dict\[str, typing.Any\], optional: False\), 'source': ExecutionParameter\(type: &lt;class 'str'&gt;, optional: False\)}_[¶](zenml.components.sequencer.md#zenml.components.sequencer.component.SequencerComponentSpec.PARAMETERS)

### zenml.components.sequencer.constants module[¶](zenml.components.sequencer.md#module-zenml.components.sequencer.constants)

### zenml.components.sequencer.executor module[¶](zenml.components.sequencer.md#module-zenml.components.sequencer.executor)

 _class_ `zenml.components.sequencer.executor.Executor`\(_context: Optional\[tfx.dsl.components.base.base\_executor.BaseExecutor.Context\] = None_\)[¶](zenml.components.sequencer.md#zenml.components.sequencer.executor.Executor)

Bases: `tfx.dsl.components.base.base_executor.BaseExecutor` `Do`\(_input\_dict: Dict\[str, List\[tfx.types.artifact.Artifact\]\]_, _output\_dict: Dict\[str, List\[tfx.types.artifact.Artifact\]\]_, _exec\_properties: Dict\[str, Any\]_\) → None[¶](zenml.components.sequencer.md#zenml.components.sequencer.executor.Executor.Do)

Main execution logic for the Sequencer componentParameters

* **input\_dict** – input channels
* **output\_dict** – output channels
* **exec\_properties** – the execution properties defined in the spec

 _class_ `zenml.components.sequencer.executor.RemoveKey`\(_\*unused\_args_, _\*\*unused\_kwargs_\)[¶](zenml.components.sequencer.md#zenml.components.sequencer.executor.RemoveKey)

Bases: `apache_beam.transforms.core.DoFn` `process`\(_element_\)[¶](zenml.components.sequencer.md#zenml.components.sequencer.executor.RemoveKey.process)

Remove the key from the output of the CombineFn and return the resulting datapoints

### zenml.components.sequencer.utils module[¶](zenml.components.sequencer.md#module-zenml.components.sequencer.utils)

 _class_ `zenml.components.sequencer.utils.ConvertToDataframe`\(_\*unused\_args_, _\*\*unused\_kwargs_\)[¶](zenml.components.sequencer.md#zenml.components.sequencer.utils.ConvertToDataframe)

Bases: `apache_beam.transforms.core.DoFn`

Beam PTransform responsible for converting the incoming Arrow table into a pandas dataframe `process`\(_element_, _\*args_, _\*\*kwargs_\)[¶](zenml.components.sequencer.md#zenml.components.sequencer.utils.ConvertToDataframe.process)

Method to use for processing elements.

This is invoked by `DoFnRunner` for each element of a input `PCollection`.

The following parameters can be used as default values on `process` arguments to indicate that a DoFn accepts the corresponding parameters. For example, a DoFn might accept the element and its timestamp with the following signature:

```text
def process(element=DoFn.ElementParam, timestamp=DoFn.TimestampParam):
  ...
```

The full set of parameters is:

* `DoFn.ElementParam`: element to be processed, should not be mutated.
* `DoFn.SideInputParam`: a side input that may be used when processing.
* `DoFn.TimestampParam`: timestamp of the input element.
* `DoFn.WindowParam`: `Window` the input element belongs to.
* `DoFn.TimerParam`: a `userstate.RuntimeTimer` object defined by the spec of the parameter.
* `DoFn.StateParam`: a `userstate.RuntimeState` object defined by the spec of the parameter.
* `DoFn.KeyParam`: key associated with the element.
* `DoFn.RestrictionParam`: an `iobase.RestrictionTracker` will be provided here to allow treatment as a Splittable `DoFn`. The restriction tracker will be derived from the restriction provider in the parameter.
* `DoFn.WatermarkEstimatorParam`: a function that can be used to track output watermark of Splittable `DoFn` implementations.

Parameters

* **element** – The element to be processed
* **\*args** – side inputs
* **\*\*kwargs** – other keyword arguments.

Returns

An Iterable of output elements or None. `zenml.components.sequencer.utils.df_to_example`\(_instance_\) → tensorflow.core.example.example\_pb2.Example[¶](zenml.components.sequencer.md#zenml.components.sequencer.utils.df_to_example)

Auxiliary function to create a tf.train.Example from a pandas dataframeParameters

**instance** – pd.DataFrame, the datapointReturns

tf.train.Example, the result `zenml.components.sequencer.utils.serialize`\(_instance_\)[¶](zenml.components.sequencer.md#zenml.components.sequencer.utils.serialize)

Helper function to serialize a tf.train.Example in the beam pipelineParameters

**instance** – the input, tf.train.ExampleReturns

serialized version of the input

### Module contents[¶](zenml.components.sequencer.md#module-zenml.components.sequencer)

 [Back to top](zenml.components.sequencer.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


