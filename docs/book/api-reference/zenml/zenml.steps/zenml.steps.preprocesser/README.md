# Preprocesser

&lt;!DOCTYPE html&gt;

zenml.steps.preprocesser package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](./)
  * * [zenml.steps.preprocesser package](./)
      * [Subpackages](./#subpackages)
      * [Submodules](./#submodules)
      * [zenml.steps.preprocesser.base\_preprocesser module](./#module-zenml.steps.preprocesser.base_preprocesser)
      * [Module contents](./#module-zenml.steps.preprocesser)
* [ « zenml.steps.i...](../zenml.steps.inferrer.md)
* [ zenml.steps.p... »](zenml.steps.preprocesser.standard_preprocesser/)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.steps.preprocesser.rst.txt)

## zenml.steps.preprocesser package[¶](./#zenml-steps-preprocesser-package)

### Subpackages[¶](./#subpackages)

* [zenml.steps.preprocesser.standard\_preprocesser package](zenml.steps.preprocesser.standard_preprocesser/)
  * [Subpackages](zenml.steps.preprocesser.standard_preprocesser/#subpackages)
    * [zenml.steps.preprocesser.standard\_preprocesser.methods package](zenml.steps.preprocesser.standard_preprocesser/zenml.steps.preprocesser.standard_preprocesser.methods.md)
      * [Submodules](zenml.steps.preprocesser.standard_preprocesser/zenml.steps.preprocesser.standard_preprocesser.methods.md#submodules)
      * [zenml.steps.preprocesser.standard\_preprocesser.methods.methods\_nonseq\_filling module](zenml.steps.preprocesser.standard_preprocesser/zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods.methods_nonseq_filling)
      * [zenml.steps.preprocesser.standard\_preprocesser.methods.methods\_transform module](zenml.steps.preprocesser.standard_preprocesser/zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods.methods_transform)
      * [zenml.steps.preprocesser.standard\_preprocesser.methods.standard\_methods module](zenml.steps.preprocesser.standard_preprocesser/zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods.standard_methods)
      * [Module contents](zenml.steps.preprocesser.standard_preprocesser/zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods)
  * [Submodules](zenml.steps.preprocesser.standard_preprocesser/#submodules)
  * [zenml.steps.preprocesser.standard\_preprocesser.standard\_preprocesser module](zenml.steps.preprocesser.standard_preprocesser/#module-zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser)
  * [Module contents](zenml.steps.preprocesser.standard_preprocesser/#module-zenml.steps.preprocesser.standard_preprocesser)

### Submodules[¶](./#submodules)

### zenml.steps.preprocesser.base\_preprocesser module[¶](./#module-zenml.steps.preprocesser.base_preprocesser)

 _class_ `zenml.steps.preprocesser.base_preprocesser.BasePreprocesserStep`\(_split\_mapping: Dict\[str, List\[str\]\] = None_, _\*\*kwargs_\)[¶](./#zenml.steps.preprocesser.base_preprocesser.BasePreprocesserStep)

Bases: [`zenml.steps.base_step.BaseStep`](../#zenml.steps.base_step.BaseStep)

Base class for all preprocessing steps. These steps are used to specify transformation and filling operations on data that occur before the machine learning model is trained. `STEP_TYPE` _= 'preprocesser'_[¶](./#zenml.steps.preprocesser.base_preprocesser.BasePreprocesserStep.STEP_TYPE) `preprocessing_fn`\(_inputs: Dict_\)[¶](./#zenml.steps.preprocesser.base_preprocesser.BasePreprocesserStep.preprocessing_fn)

Function used in the Transform component. Override this to do custom preprocessing logic.Parameters

* **inputs** \(_dict_\) – Inputs where keys are feature names and values are
* **which represent the values of the features.** \(_tensors_\) –

Returns

Inputs where keys are transformed feature names

and values are tensors with the transformed values of the features.

Return type

outputs \(dict\) `zenml.steps.preprocesser.base_preprocesser.build_split_mapping`\(_args_\)[¶](./#zenml.steps.preprocesser.base_preprocesser.build_split_mapping)

### Module contents[¶](./#module-zenml.steps.preprocesser)

 [Back to top](./)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


