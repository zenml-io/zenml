# Transform simple

&lt;!DOCTYPE html&gt;

zenml.components.transform\_simple package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.components.transform_simple.md)
  * * [zenml.components.transform\_simple package](zenml.components.transform_simple.md)
      * [Submodules](zenml.components.transform_simple.md#submodules)
      * [zenml.components.transform\_simple.component module](zenml.components.transform_simple.md#module-zenml.components.transform_simple.component)
      * [zenml.components.transform\_simple.constants module](zenml.components.transform_simple.md#module-zenml.components.transform_simple.constants)
      * [zenml.components.transform\_simple.executor module](zenml.components.transform_simple.md#module-zenml.components.transform_simple.executor)
      * [zenml.components.transform\_simple.utils module](zenml.components.transform_simple.md#module-zenml.components.transform_simple.utils)
      * [Module contents](zenml.components.transform_simple.md#module-zenml.components.transform_simple)
* [ « zenml.compone...](zenml.components.transform.md)
* [ zenml.datasou... »](../zenml.datasources.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.components.transform_simple.rst.txt)

## zenml.components.transform\_simple package[¶](zenml.components.transform_simple.md#zenml-components-transform-simple-package)

### Submodules[¶](zenml.components.transform_simple.md#submodules)

### zenml.components.transform\_simple.component module[¶](zenml.components.transform_simple.md#module-zenml.components.transform_simple.component)

 _class_ `zenml.components.transform_simple.component.SimpleTransform`\(_name: str_, _source: str_, _source\_args: Dict\[str, Any\]_, _instance\_name: Optional\[str\] = None_, _examples: Optional\[tfx.types.component\_spec.ChannelParameter\] = None_\)[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.component.SimpleTransform)

Bases: `tfx.components.transform.component.Transform` `EXECUTOR_SPEC` _= &lt;tfx.dsl.components.base.executor\_spec.ExecutorClassSpec object&gt;_[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.component.SimpleTransform.EXECUTOR_SPEC) `SPEC_CLASS`[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.component.SimpleTransform.SPEC_CLASS)

alias of [`SimpleTransformSpec`](zenml.components.transform_simple.md#zenml.components.transform_simple.component.SimpleTransformSpec) _class_ `zenml.components.transform_simple.component.SimpleTransformSpec`\(_\*\*kwargs_\)[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.component.SimpleTransformSpec)

Bases: `tfx.types.component_spec.ComponentSpec` `INPUTS` _= {}_[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.component.SimpleTransformSpec.INPUTS) `OUTPUTS` _= {'examples': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Examples'&gt;\)}_[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.component.SimpleTransformSpec.OUTPUTS) `PARAMETERS` _= {'args': ExecutionParameter\(type: typing.Dict\[str, typing.Any\], optional: False\), 'name': ExecutionParameter\(type: &lt;class 'str'&gt;, optional: False\), 'source': ExecutionParameter\(type: &lt;class 'str'&gt;, optional: False\)}_[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.component.SimpleTransformSpec.PARAMETERS)

### zenml.components.transform\_simple.constants module[¶](zenml.components.transform_simple.md#module-zenml.components.transform_simple.constants)

### zenml.components.transform\_simple.executor module[¶](zenml.components.transform_simple.md#module-zenml.components.transform_simple.executor)

 _class_ `zenml.components.transform_simple.executor.DataExecutor`\(_context: Optional\[tfx.dsl.components.base.base\_executor.BaseExecutor.Context\] = None_\)[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.executor.DataExecutor)

Bases: `tfx.dsl.components.base.base_executor.BaseExecutor` `Do`\(_input\_dict: Dict\[str, List\[tfx.types.artifact.Artifact\]\]_, _output\_dict: Dict\[str, List\[tfx.types.artifact.Artifact\]\]_, _exec\_properties: Dict\[str, Any\]_\) → None[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.executor.DataExecutor.Do)Parameters

* **input\_dict** –
* **output\_dict** –
* **exec\_properties** –

 `zenml.components.transform_simple.executor.WriteToTFRecord`\(_datapoints: Dict\[str, Any\]_, _schema: Dict\[str, Any\]_, _output\_split\_path: str_\) → apache\_beam.pvalue.PDone[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.executor.WriteToTFRecord)

Infers schema and writes to TFRecord

### zenml.components.transform\_simple.utils module[¶](zenml.components.transform_simple.md#module-zenml.components.transform_simple.utils)

Utils for data\_gen _class_ `zenml.components.transform_simple.utils.DataType`\(_value_\)[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DataType)

Bases: `enum.IntEnum`

An enumeration. `BYTES` _= 2_[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DataType.BYTES) `FLOAT` _= 1_[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DataType.FLOAT) `INT` _= 0_[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DataType.INT) `UNKNOWN` _= -1_[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DataType.UNKNOWN) _class_ `zenml.components.transform_simple.utils.DtypeInferrer`\(_\*unused\_args_, _\*\*unused\_kwargs_\)[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DtypeInferrer)

Bases: `apache_beam.transforms.core.CombineFn`, `abc.ABC`

A beam.CombineFn to infer data types `add_input`\(_accumulator: Dict\[str,_ [_zenml.components.transform\_simple.utils.DataType_](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DataType)_\]_, _element: Dict\[str, bytes\]_, _\*\*kwargs_\) → Dict\[str, [zenml.components.transform\_simple.utils.DataType](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DataType)\][¶](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DtypeInferrer.add_input)

Return result of folding element into accumulator.

CombineFn implementors must override add\_input.Parameters

* **mutable\_accumulator** – the current accumulator, may be modified and returned for efficiency
* **element** – the element to add, should not be mutated
* **\*args** – Additional arguments and side inputs.
* **\*\*kwargs** – Additional arguments and side inputs.

 `create_accumulator`\(_\*\*kwargs_\) → Dict\[str, [zenml.components.transform\_simple.utils.DataType](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DataType)\][¶](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DtypeInferrer.create_accumulator)

Return a fresh, empty accumulator for the combine operation.Parameters

* **\*args** – Additional arguments and side inputs.
* **\*\*kwargs** – Additional arguments and side inputs.

 `extract_output`\(_accumulator: Dict\[str, Any\]_, _\*\*kwargs_\) → Dict\[str, str\][¶](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DtypeInferrer.extract_output)

Return result of converting accumulator into the output value.Parameters

* **accumulator** – the final accumulator value computed by this CombineFn for the entire input key or PCollection. Can be modified for efficiency.
* **\*args** – Additional arguments and side inputs.
* **\*\*kwargs** – Additional arguments and side inputs.

 `merge_accumulators`\(_accumulators: List\[Dict\[str,_ [_zenml.components.transform\_simple.utils.DataType_](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DataType)_\]\]_, _\*\*kwargs_\) → Dict\[str, [zenml.components.transform\_simple.utils.DataType](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DataType)\][¶](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.DtypeInferrer.merge_accumulators)

Returns the result of merging several accumulators to a single accumulator value.Parameters

* **accumulators** – the accumulators to merge. Only the first accumulator may be modified and returned for efficiency; the other accumulators should not be mutated, because they may be shared with other code and mutating them could lead to incorrect results or data corruption.
* **\*args** – Additional arguments and side inputs.
* **\*\*kwargs** – Additional arguments and side inputs.

 `zenml.components.transform_simple.utils.append_tf_example`\(_data: Dict\[str, Any\]_, _schema: Dict\[str, Any\]_\) → tensorflow.core.example.example\_pb2.Example[¶](zenml.components.transform_simple.md#zenml.components.transform_simple.utils.append_tf_example)

Add tf example to row

### Module contents[¶](zenml.components.transform_simple.md#module-zenml.components.transform_simple)

 [Back to top](zenml.components.transform_simple.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


