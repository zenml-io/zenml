# Split gen

&lt;!DOCTYPE html&gt;

zenml.components.split\_gen package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.components.split_gen.md)
  * * [zenml.components.split\_gen package](zenml.components.split_gen.md)
      * [Submodules](zenml.components.split_gen.md#submodules)
      * [zenml.components.split\_gen.component module](zenml.components.split_gen.md#module-zenml.components.split_gen.component)
      * [zenml.components.split\_gen.constants module](zenml.components.split_gen.md#module-zenml.components.split_gen.constants)
      * [zenml.components.split\_gen.executor module](zenml.components.split_gen.md#module-zenml.components.split_gen.executor)
      * [zenml.components.split\_gen.utils module](zenml.components.split_gen.md#module-zenml.components.split_gen.utils)
      * [Module contents](zenml.components.split_gen.md#module-zenml.components.split_gen)
* [ « zenml.compone...](zenml.components.sequencer.md)
* [ zenml.compone... »](zenml.components.tokenizer.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.components.split_gen.rst.txt)

## zenml.components.split\_gen package[¶](zenml.components.split_gen.md#zenml-components-split-gen-package)

### Submodules[¶](zenml.components.split_gen.md#submodules)

### zenml.components.split\_gen.component module[¶](zenml.components.split_gen.md#module-zenml.components.split_gen.component)

 _class_ `zenml.components.split_gen.component.SplitGen`\(_source: str_, _source\_args: Dict\[str, Any\]_, _input\_examples: tfx.types.channel.Channel_, _examples: tfx.types.channel.Channel = None_, _statistics: tfx.types.channel.Channel = None_, _schema: tfx.types.channel.Channel = None_\)[¶](zenml.components.split_gen.md#zenml.components.split_gen.component.SplitGen)

Bases: `tfx.dsl.components.base.base_component.BaseComponent` `EXECUTOR_SPEC` _= &lt;tfx.dsl.components.base.executor\_spec.ExecutorClassSpec object&gt;_[¶](zenml.components.split_gen.md#zenml.components.split_gen.component.SplitGen.EXECUTOR_SPEC) `SPEC_CLASS`[¶](zenml.components.split_gen.md#zenml.components.split_gen.component.SplitGen.SPEC_CLASS)

alias of [`SplitGenComponentSpec`](zenml.components.split_gen.md#zenml.components.split_gen.component.SplitGenComponentSpec) _class_ `zenml.components.split_gen.component.SplitGenComponentSpec`\(_\*\*kwargs_\)[¶](zenml.components.split_gen.md#zenml.components.split_gen.component.SplitGenComponentSpec)

Bases: `tfx.types.component_spec.ComponentSpec`

SplitGen ExampleGen component spec. `INPUTS` _= {'input\_examples': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Examples'&gt;\), 'schema': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Schema'&gt;\), 'statistics': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.ExampleStatistics'&gt;\)}_[¶](zenml.components.split_gen.md#zenml.components.split_gen.component.SplitGenComponentSpec.INPUTS) `OUTPUTS` _= {'examples': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Examples'&gt;\)}_[¶](zenml.components.split_gen.md#zenml.components.split_gen.component.SplitGenComponentSpec.OUTPUTS) `PARAMETERS` _= {'args': ExecutionParameter\(type: typing.Dict\[str, typing.Any\], optional: False\), 'source': ExecutionParameter\(type: &lt;class 'str'&gt;, optional: False\)}_[¶](zenml.components.split_gen.md#zenml.components.split_gen.component.SplitGenComponentSpec.PARAMETERS)

### zenml.components.split\_gen.constants module[¶](zenml.components.split_gen.md#module-zenml.components.split_gen.constants)

### zenml.components.split\_gen.executor module[¶](zenml.components.split_gen.md#module-zenml.components.split_gen.executor)

 _class_ `zenml.components.split_gen.executor.Executor`\(_context: Optional\[tfx.dsl.components.base.base\_executor.BaseExecutor.Context\] = None_\)[¶](zenml.components.split_gen.md#zenml.components.split_gen.executor.Executor)

Bases: `tfx.dsl.components.base.base_executor.BaseExecutor` `Do`\(_input\_dict: Dict\[str, List\[tfx.types.artifact.Artifact\]\]_, _output\_dict: Dict\[str, List\[tfx.types.artifact.Artifact\]\]_, _exec\_properties: Dict\[str, Any\]_\) → None[¶](zenml.components.split_gen.md#zenml.components.split_gen.executor.Executor.Do)

Write description regarding this beautiful executor.Parameters

* **input\_dict** –
* **output\_dict** –
* **exec\_properties** –

 `zenml.components.split_gen.executor.WriteSplit`\(_example\_split: apache\_beam.pvalue.PCollection_, _output\_split\_path: str_\) → apache\_beam.pvalue.PDone[¶](zenml.components.split_gen.md#zenml.components.split_gen.executor.WriteSplit)

Shuffles and writes output split.

### zenml.components.split\_gen.utils module[¶](zenml.components.split_gen.md#module-zenml.components.split_gen.utils)

 `zenml.components.split_gen.utils.parse_schema`\(_input\_dict: Dict\[str, List\[tfx.types.artifact.Artifact\]\]_\)[¶](zenml.components.split_gen.md#zenml.components.split_gen.utils.parse_schema) `zenml.components.split_gen.utils.parse_statistics`\(_split\_name: str_, _statistics: List\[tfx.types.artifact.Artifact\]_\) → Dict\[str, int\][¶](zenml.components.split_gen.md#zenml.components.split_gen.utils.parse_statistics)

### Module contents[¶](zenml.components.split_gen.md#module-zenml.components.split_gen)

 [Back to top](zenml.components.split_gen.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


