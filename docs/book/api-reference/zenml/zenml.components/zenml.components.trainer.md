# Trainer

&lt;!DOCTYPE html&gt;

zenml.components.trainer package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.components.trainer.md)
  * * [zenml.components.trainer package](zenml.components.trainer.md)
      * [Submodules](zenml.components.trainer.md#submodules)
      * [zenml.components.trainer.component module](zenml.components.trainer.md#module-zenml.components.trainer.component)
      * [zenml.components.trainer.constants module](zenml.components.trainer.md#module-zenml.components.trainer.constants)
      * [zenml.components.trainer.executor module](zenml.components.trainer.md#module-zenml.components.trainer.executor)
      * [zenml.components.trainer.trainer\_module module](zenml.components.trainer.md#module-zenml.components.trainer.trainer_module)
      * [Module contents](zenml.components.trainer.md#module-zenml.components.trainer)
* [ « zenml.compone...](zenml.components.tokenizer.md)
* [ zenml.compone... »](zenml.components.transform.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.components.trainer.rst.txt)

## zenml.components.trainer package[¶](zenml.components.trainer.md#zenml-components-trainer-package)

### Submodules[¶](zenml.components.trainer.md#submodules)

### zenml.components.trainer.component module[¶](zenml.components.trainer.md#module-zenml.components.trainer.component)

 _class_ `zenml.components.trainer.component.Trainer`\(_examples: tfx.types.channel.Channel = None_, _transformed\_examples: Optional\[tfx.types.channel.Channel\] = None_, _transform\_graph: Optional\[tfx.types.channel.Channel\] = None_, _schema: Optional\[tfx.types.channel.Channel\] = None_, _base\_model: Optional\[tfx.types.channel.Channel\] = None_, _hyperparameters: Optional\[tfx.types.channel.Channel\] = None_, _run\_fn: Optional\[Union\[str, tfx.orchestration.data\_types.RuntimeParameter\]\] = None_, _custom\_config: Optional\[Dict\[str, Any\]\] = None_, _custom\_executor\_spec: Optional\[tfx.dsl.components.base.executor\_spec.ExecutorSpec\] = None_, _output: Optional\[tfx.types.channel.Channel\] = None_, _model\_run: Optional\[tfx.types.channel.Channel\] = None_, _test\_results: Optional\[tfx.types.channel.Channel\] = None_, _instance\_name: Optional\[str\] = None_\)[¶](zenml.components.trainer.md#zenml.components.trainer.component.Trainer)

Bases: `tfx.dsl.components.base.base_component.BaseComponent`

A slightly adjusted version of the TFX Trainer Component. It features an additional output artifact to save the test results in. `EXECUTOR_SPEC` _= &lt;tfx.dsl.components.base.executor\_spec.ExecutorClassSpec object&gt;_[¶](zenml.components.trainer.md#zenml.components.trainer.component.Trainer.EXECUTOR_SPEC) `SPEC_CLASS`[¶](zenml.components.trainer.md#zenml.components.trainer.component.Trainer.SPEC_CLASS)

alias of [`ZenMLTrainerSpec`](zenml.components.trainer.md#zenml.components.trainer.component.ZenMLTrainerSpec) _class_ `zenml.components.trainer.component.ZenMLTrainerSpec`\(_\*\*kwargs_\)[¶](zenml.components.trainer.md#zenml.components.trainer.component.ZenMLTrainerSpec)

Bases: `tfx.types.component_spec.ComponentSpec` `INPUTS` _= {'base\_model': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Model'&gt;\), 'examples': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Examples'&gt;\), 'hyperparameters': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.HyperParameters'&gt;\), 'schema': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Schema'&gt;\), 'transform\_graph': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.TransformGraph'&gt;\)}_[¶](zenml.components.trainer.md#zenml.components.trainer.component.ZenMLTrainerSpec.INPUTS) `OUTPUTS` _= {'model': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Model'&gt;\), 'model\_run': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.ModelRun'&gt;\), 'test\_results': ChannelParameter\(type: &lt;class 'tfx.types.standard\_artifacts.Examples'&gt;\)}_[¶](zenml.components.trainer.md#zenml.components.trainer.component.ZenMLTrainerSpec.OUTPUTS) `PARAMETERS` _= {'custom\_config': ExecutionParameter\(type: \(&lt;class 'str'&gt;, &lt;class 'str'&gt;\), optional: True\), 'run\_fn': ExecutionParameter\(type: \(&lt;class 'str'&gt;, &lt;class 'str'&gt;\), optional: True\)}_[¶](zenml.components.trainer.md#zenml.components.trainer.component.ZenMLTrainerSpec.PARAMETERS)

### zenml.components.trainer.constants module[¶](zenml.components.trainer.md#module-zenml.components.trainer.constants)

### zenml.components.trainer.executor module[¶](zenml.components.trainer.md#module-zenml.components.trainer.executor)

 _class_ `zenml.components.trainer.executor.ZenMLTrainerArgs`\(_working\_dir: str = None_, _train\_files: List\[str\] = None_, _eval\_files: List\[str\] = None_, _train\_steps: int = None_, _eval\_steps: int = None_, _schema\_path: str = None_, _schema\_file: str = None_, _transform\_graph\_path: str = None_, _transform\_output: str = None_, _data\_accessor: tfx.components.trainer.fn\_args\_utils.DataAccessor = None_, _serving\_model\_dir: str = None_, _eval\_model\_dir: str = None_, _model\_run\_dir: str = None_, _base\_model: str = None_, _hyperparameters: str = None_, _custom\_config: Dict\[str, Any\] = None_\)[¶](zenml.components.trainer.md#zenml.components.trainer.executor.ZenMLTrainerArgs)

Bases: `tfx.components.trainer.fn_args_utils.FnArgs` `input_patterns` _= \_CountingAttr\(counter=131, \_default=None, repr=True, eq=True, order=True, hash=None, init=True, on\_setattr=None, metadata={}\)_[¶](zenml.components.trainer.md#zenml.components.trainer.executor.ZenMLTrainerArgs.input_patterns) `output_patterns` _= \_CountingAttr\(counter=132, \_default=None, repr=True, eq=True, order=True, hash=None, init=True, on\_setattr=None, metadata={}\)_[¶](zenml.components.trainer.md#zenml.components.trainer.executor.ZenMLTrainerArgs.output_patterns) _class_ `zenml.components.trainer.executor.ZenMLTrainerExecutor`\(_context: Optional\[tfx.dsl.components.base.base\_executor.BaseExecutor.Context\] = None_\)[¶](zenml.components.trainer.md#zenml.components.trainer.executor.ZenMLTrainerExecutor)

Bases: `tfx.components.trainer.executor.GenericExecutor`

An adjusted version of the TFX Trainer Generic executor, which also handles an additional output artifact while managing the fn\_args

### zenml.components.trainer.trainer\_module module[¶](zenml.components.trainer.md#module-zenml.components.trainer.trainer_module)

 `zenml.components.trainer.trainer_module.run_fn`\(_fn\_args_\)[¶](zenml.components.trainer.md#zenml.components.trainer.trainer_module.run_fn)

### Module contents[¶](zenml.components.trainer.md#module-zenml.components.trainer)

 [Back to top](zenml.components.trainer.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


