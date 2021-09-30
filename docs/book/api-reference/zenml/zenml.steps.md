# Steps

&lt;!DOCTYPE html&gt;

zenml.steps package — ZenML documentation  [ZenML](https://github.com/zenml-io/zenml/tree/f72adcd1e42495f4df75b34799ad8ac19cae3e95/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/zenml-io/zenml/tree/f72adcd1e42495f4df75b34799ad8ac19cae3e95/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/zenml-io/zenml/tree/f72adcd1e42495f4df75b34799ad8ac19cae3e95/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.steps.md)
  * * [zenml.steps package](zenml.steps.md)
      * [Submodules](zenml.steps.md#submodules)
      * [zenml.steps.base\_step module](zenml.steps.md#module-zenml.steps.base_step)
      * [zenml.steps.step\_decorator module](zenml.steps.md#module-zenml.steps.step_decorator)
      * [zenml.steps.utils module](zenml.steps.md#module-zenml.steps.utils)
      * [Module contents](zenml.steps.md#module-zenml.steps)
* [ « zenml.stacks package](zenml.stacks.md)
* [ zenml.utils package »](zenml.utils.md)
*  [Source](https://github.com/zenml-io/zenml/tree/f72adcd1e42495f4df75b34799ad8ac19cae3e95/docs/sphinx_docs/_build/html/_sources/zenml.steps.rst.txt)

## zenml.steps package[¶](zenml.steps.md#zenml-steps-package)

### Submodules[¶](zenml.steps.md#submodules)

### zenml.steps.base\_step module[¶](zenml.steps.md#module-zenml.steps.base_step)

 _class_ zenml.steps.base\_step.BaseStep\(_\*args_, _\*\*kwargs_\)[¶](zenml.steps.md#zenml.steps.base_step.BaseStep)

Bases: `object`

The base implementation of a ZenML Step which will be inherited by all the other step implementations INPUT\_SPEC _= {}_[¶](zenml.steps.md#zenml.steps.base_step.BaseStep.INPUT_SPEC) OUTPUT\_SPEC _= {}_[¶](zenml.steps.md#zenml.steps.base_step.BaseStep.OUTPUT_SPEC) PARAM\_DEFAULTS _= {}_[¶](zenml.steps.md#zenml.steps.base_step.BaseStep.PARAM_DEFAULTS) PARAM\_SPEC _= {}_[¶](zenml.steps.md#zenml.steps.base_step.BaseStep.PARAM_SPEC) _property_ component[¶](zenml.steps.md#zenml.steps.base_step.BaseStep.component) get\_outputs\(\)[¶](zenml.steps.md#zenml.steps.base_step.BaseStep.get_outputs) _abstract_ process\(_\*args_, _\*\*kwargs_\)[¶](zenml.steps.md#zenml.steps.base_step.BaseStep.process) set\_inputs\(_\*\*artifacts_\)[¶](zenml.steps.md#zenml.steps.base_step.BaseStep.set_inputs) _class_ zenml.steps.base\_step.BaseStepMeta\(_name_, _bases_, _dct_\)[¶](zenml.steps.md#zenml.steps.base_step.BaseStepMeta)

Bases: `type`

### zenml.steps.step\_decorator module[¶](zenml.steps.md#module-zenml.steps.step_decorator)

 zenml.steps.step\_decorator.step\(_name: Optional\[str\] = None_\)[¶](zenml.steps.md#zenml.steps.step_decorator.step)

Outer decorator function for the creation of a ZenML step

In order to be able work with parameters such as “name”, it features a nested decorator structure.Parameters

**name** – str, the given name for the stepReturns

the inner decorator which creates the step class based on the ZenML BaseStep

### zenml.steps.utils module[¶](zenml.steps.md#module-zenml.steps.utils)

The collection of utility functions/classes are inspired by their original implementation of the Tensorflow Extended team, which can be found here:

[https://github.com/tensorflow/tfx/blob/master/tfx/dsl/component/experimental/decorators.py](https://github.com/tensorflow/tfx/blob/master/tfx/dsl/component/experimental/decorators.py)

This version is heavily adjusted to work with the Pipeline-Step paradigm which is proposed by ZenML. zenml.steps.utils.generate\_component\(_step_\) → Callable\[\[...\], Any\][¶](zenml.steps.md#zenml.steps.utils.generate_component)

### Module contents[¶](zenml.steps.md#module-zenml.steps)

 [Back to top](zenml.steps.md)

 © Copyright 2021, ZenML GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 4.2.0.  


