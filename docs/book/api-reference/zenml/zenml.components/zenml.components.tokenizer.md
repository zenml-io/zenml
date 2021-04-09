# Tokenizer

&lt;!DOCTYPE html&gt;

zenml.components.tokenizer package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.components.tokenizer.md)
  * * [zenml.components.tokenizer package](zenml.components.tokenizer.md)
      * [Submodules](zenml.components.tokenizer.md#submodules)
      * [zenml.components.tokenizer.component module](zenml.components.tokenizer.md#module-zenml.components.tokenizer.component)
      * [zenml.components.tokenizer.constants module](zenml.components.tokenizer.md#module-zenml.components.tokenizer.constants)
      * [zenml.components.tokenizer.executor module](zenml.components.tokenizer.md#module-zenml.components.tokenizer.executor)
      * [Module contents](zenml.components.tokenizer.md#module-zenml.components.tokenizer)
* [ « zenml.compone...](zenml.components.split_gen.md)
* [ zenml.compone... »](zenml.components.trainer.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.components.tokenizer.rst.txt)

## zenml.components.tokenizer package[¶](zenml.components.tokenizer.md#zenml-components-tokenizer-package)

### Submodules[¶](zenml.components.tokenizer.md#submodules)

### zenml.components.tokenizer.component module[¶](zenml.components.tokenizer.md#module-zenml.components.tokenizer.component)

 _class_ `zenml.components.tokenizer.component.Tokenizer`\(_source: str_, _source\_args: Dict\[str, Any\]_, _examples: Optional\[tfx.types.component\_spec.ChannelParameter\] = None_, _tokenizer: Optional\[tfx.types.component\_spec.ChannelParameter\] = None_, _output\_examples: Optional\[tfx.types.component\_spec.ChannelParameter\] = None_, _instance\_name: Optional\[str\] = None_\)[¶](zenml.components.tokenizer.md#zenml.components.tokenizer.component.Tokenizer)

Bases: `tfx.dsl.components.base.base_component.BaseComponent` `EXECUTOR_SPEC` _= &lt;tfx.dsl.components.base.executor\_spec.ExecutorClassSpec object&gt;_[¶](zenml.components.tokenizer.md#zenml.components.tokenizer.component.Tokenizer.EXECUTOR_SPEC) `SPEC_CLASS`[¶](zenml.components.tokenizer.md#zenml.components.tokenizer.component.Tokenizer.SPEC_CLASS)

alias of [`TokenizerSpec`](zenml.components.tokenizer.md#zenml.components.tokenizer.component.TokenizerSpec) _class_ `zenml.components.tokenizer.component.TokenizerSpec`\(_\*\*kwargs_\)[¶](zenml.components.tokenizer.md#zenml.components.tokenizer.component.TokenizerSpec)

Bases: `tfx.types.component_spec.ComponentSpec` `INPUTS` _= {'examples': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Examples'&gt;\)}_[¶](zenml.components.tokenizer.md#zenml.components.tokenizer.component.TokenizerSpec.INPUTS) `OUTPUTS` _= {'output\_examples': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Examples'&gt;\), 'tokenizer': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Model'&gt;\)}_[¶](zenml.components.tokenizer.md#zenml.components.tokenizer.component.TokenizerSpec.OUTPUTS) `PARAMETERS` _= {'args': ExecutionParameter\(type: typing.Dict\[str, typing.Any\], optional: False\), 'source': ExecutionParameter\(type: &lt;class 'str'&gt;, optional: False\)}_[¶](zenml.components.tokenizer.md#zenml.components.tokenizer.component.TokenizerSpec.PARAMETERS)

### zenml.components.tokenizer.constants module[¶](zenml.components.tokenizer.md#module-zenml.components.tokenizer.constants)

### zenml.components.tokenizer.executor module[¶](zenml.components.tokenizer.md#module-zenml.components.tokenizer.executor)

 _class_ `zenml.components.tokenizer.executor.TokenizerExecutor`\(_context: Optional\[tfx.dsl.components.base.base\_executor.BaseExecutor.Context\] = None_\)[¶](zenml.components.tokenizer.md#zenml.components.tokenizer.executor.TokenizerExecutor)

Bases: `tfx.dsl.components.base.base_executor.BaseExecutor`

Tokenizer executor. This component uses a tokenizer, either already trained or newly instantiated, and uses it to transform the input data. `Do`\(_input\_dict: Dict\[str, List\[tfx.types.artifact.Artifact\]\]_, _output\_dict: Dict\[str, List\[tfx.types.artifact.Artifact\]\]_, _exec\_properties: Dict\[str, Any\]_\) → None[¶](zenml.components.tokenizer.md#zenml.components.tokenizer.executor.TokenizerExecutor.Do)

Execute underlying component implementation.Parameters

* **input\_dict** – Input dict from input key to a list of Artifacts. These are often outputs of another component in the pipeline and passed to the component by the orchestration system.
* **output\_dict** – Output dict from output key to a list of Artifacts. These are often consumed by a dependent component.
* **exec\_properties** – A dict of execution properties. These are inputs to pipeline with primitive types \(int, string, float\) and fully materialized when a pipeline is constructed. No dependency to other component or later injection from orchestration systems is necessary or possible on these values.

Returns

execution\_result\_pb2.ExecutorOutput or None. `zenml.components.tokenizer.executor.append_tf_example`\(_ex: tensorflow.core.example.example\_pb2.Example_, _tokenizer\_step:_ [_zenml.steps.tokenizer.base\_tokenizer.BaseTokenizer_](../zenml.steps/zenml.steps.tokenizer.md#zenml.steps.tokenizer.base_tokenizer.BaseTokenizer)\)[¶](zenml.components.tokenizer.md#zenml.components.tokenizer.executor.append_tf_example)

Append the tokenizer encoding outputs as features to the existing data in tf.train.Example format.Parameters

* **ex** – tf.train.Example with the raw input features.
* **tokenizer\_step** – Local tokenizer step used in the NLP pipeline.

Returns

A tf.train.Example with all of the features from the ex input,

plus two features input\_ids and attention\_mask holding the word IDs and attention mask outputs from the tokenizer.

### Module contents[¶](zenml.components.tokenizer.md#module-zenml.components.tokenizer)

 [Back to top](zenml.components.tokenizer.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


