# Standard preprocesser

&lt;!DOCTYPE html&gt;

zenml.steps.preprocesser.standard\_preprocesser package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](./)
  * * [zenml.steps.preprocesser.standard\_preprocesser package](./)
      * [Subpackages](./#subpackages)
      * [Submodules](./#submodules)
      * [zenml.steps.preprocesser.standard\_preprocesser.standard\_preprocesser module](./#module-zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser)
      * [Module contents](./#module-zenml.steps.preprocesser.standard_preprocesser)
* [ « zenml.steps.p...](../)
* [ zenml.steps.p... »](zenml.steps.preprocesser.standard_preprocesser.methods.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.steps.preprocesser.standard_preprocesser.rst.txt)

## zenml.steps.preprocesser.standard\_preprocesser package[¶](./#zenml-steps-preprocesser-standard-preprocesser-package)

### Subpackages[¶](./#subpackages)

* [zenml.steps.preprocesser.standard\_preprocesser.methods package](zenml.steps.preprocesser.standard_preprocesser.methods.md)
  * [Submodules](zenml.steps.preprocesser.standard_preprocesser.methods.md#submodules)
  * [zenml.steps.preprocesser.standard\_preprocesser.methods.methods\_nonseq\_filling module](zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods.methods_nonseq_filling)
  * [zenml.steps.preprocesser.standard\_preprocesser.methods.methods\_transform module](zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods.methods_transform)
  * [zenml.steps.preprocesser.standard\_preprocesser.methods.standard\_methods module](zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods.standard_methods)
  * [Module contents](zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods)

### Submodules[¶](./#submodules)

### zenml.steps.preprocesser.standard\_preprocesser.standard\_preprocesser module[¶](./#module-zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser)

 _class_ `zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser`\(_features: List\[str\] = None_, _labels: List\[str\] = None_, _overwrite: Dict\[str, Any\] = None_, _\*\*unused\_kwargs_\)[¶](./#zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser)

Bases: [`zenml.steps.preprocesser.base_preprocesser.BasePreprocesserStep`](../#zenml.steps.preprocesser.base_preprocesser.BasePreprocesserStep)

Standard Preprocessor step. This step can be used to apply a variety of standard preprocessing techniques from the field of Machine Learning, which are predefined in ZenML, to the data. _static_ `apply_filling`\(_data_, _filling\_list_\)[¶](./#zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser.apply_filling)

Apply a list of fillings to input data. :param data: Data to be input into the transform functions. :param filling\_list: List of fillings to apply to the data. As of now,

> only the first filling in the list will be applied.

Returns

Imputed data after the first filling in filling\_list has been applied.Return type

data _static_ `apply_transform`\(_key_, _data_, _transform\_list_\)[¶](./#zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser.apply_transform)

Apply a list of transformations to input data. :param key: Key argument specific to vocabulary computation. :param data: Data to be input into the transform functions. :param transform\_list: List of transforms to apply to the data.Returns

Transformed data after each of the transforms in

transform\_list have been applied.

Return type

data `get_preprocessing_fn`\(\)[¶](./#zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser.get_preprocessing_fn) `preprocessing_fn`\(_inputs: Dict_\)[¶](./#zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.StandardPreprocesser.preprocessing_fn)

Standard preprocessing function. :param inputs: Dict mapping features to their respective data.Returns

Dict mapping transformed features to their respective

transformed data.

Return type

output `zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.infer_schema`\(_schema_\)[¶](./#zenml.steps.preprocesser.standard_preprocesser.standard_preprocesser.infer_schema)

Function to infer a schema from input data. :param schema: Input dict mapping features to tf.Tensors.Returns

Dict mapping features to their respective data types.Return type

schema\_dict

### Module contents[¶](./#module-zenml.steps.preprocesser.standard_preprocesser)

 [Back to top](./)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


