# Pusher

&lt;!DOCTYPE html&gt;

zenml.components.pusher package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.components.pusher.md)
  * * [zenml.components.pusher package](zenml.components.pusher.md)
      * [Submodules](zenml.components.pusher.md#submodules)
      * [zenml.components.pusher.cortex\_executor module](zenml.components.pusher.md#module-zenml.components.pusher.cortex_executor)
      * [Module contents](zenml.components.pusher.md#module-zenml.components.pusher)
* [ « zenml.compone...](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.components.evaluator.html)
* [ zenml.compone... »](zenml.components.sequencer.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.components.pusher.rst.txt)

## zenml.components.pusher package[¶](zenml.components.pusher.md#zenml-components-pusher-package)

### Submodules[¶](zenml.components.pusher.md#submodules)

### zenml.components.pusher.cortex\_executor module[¶](zenml.components.pusher.md#module-zenml.components.pusher.cortex_executor)

Cortex pusher executor. _class_ `zenml.components.pusher.cortex_executor.Executor`\(_context: Optional\[tfx.dsl.components.base.base\_executor.BaseExecutor.Context\] = None_\)[¶](zenml.components.pusher.md#zenml.components.pusher.cortex_executor.Executor)

Bases: `tfx.components.pusher.executor.Executor`

Deploy a model to Cortex serving. `Do`\(_input\_dict: Dict\[str, List\[tfx.types.artifact.Artifact\]\]_, _output\_dict: Dict\[str, List\[tfx.types.artifact.Artifact\]\]_, _exec\_properties: Dict\[str, Any\]_\)[¶](zenml.components.pusher.md#zenml.components.pusher.cortex_executor.Executor.Do)

Overrides the tfx\_pusher\_executor.Parameters

* **input\_dict** – Input dict from input key to a list of artifacts,
* **including** –
  * model\_export: exported model from trainer.
  * model\_blessing: model blessing path from evaluator.
* **output\_dict** –

  Output dict from key to a list of artifacts, including: - model\_push: A list of ‘ModelPushPath’ artifact of size one. It will

  > include the model in this push execution if the model was pushed.

* **exec\_properties** – Mostly a passthrough input dict for tfx.components.Pusher.executor.custom\_config

Raises

* **ValueError** – if custom config not present or not a dict.
* **RuntimeError** – if

### Module contents[¶](zenml.components.pusher.md#module-zenml.components.pusher)

 [Back to top](zenml.components.pusher.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


