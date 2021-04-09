# Methods

&lt;!DOCTYPE html&gt;

zenml.steps.preprocesser.standard\_preprocesser.methods package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.steps.preprocesser.standard_preprocesser.methods.md)
  * * [zenml.steps.preprocesser.standard\_preprocesser.methods package](zenml.steps.preprocesser.standard_preprocesser.methods.md)
      * [Submodules](zenml.steps.preprocesser.standard_preprocesser.methods.md#submodules)
      * [zenml.steps.preprocesser.standard\_preprocesser.methods.methods\_nonseq\_filling module](zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods.methods_nonseq_filling)
      * [zenml.steps.preprocesser.standard\_preprocesser.methods.methods\_transform module](zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods.methods_transform)
      * [zenml.steps.preprocesser.standard\_preprocesser.methods.standard\_methods module](zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods.standard_methods)
      * [Module contents](zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods)
* [ « zenml.steps.p...](./)
* [ zenml.steps.s... »](../../zenml.steps.sequencer/)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.steps.preprocesser.standard_preprocesser.methods.rst.txt)

## zenml.steps.preprocesser.standard\_preprocesser.methods package[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#zenml-steps-preprocesser-standard-preprocesser-methods-package)

### Submodules[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#submodules)

### zenml.steps.preprocesser.standard\_preprocesser.methods.methods\_nonseq\_filling module[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods.methods_nonseq_filling)

 `zenml.steps.preprocesser.standard_preprocesser.methods.methods_nonseq_filling.custom_f`\(_custom\_value_\)[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#zenml.steps.preprocesser.standard_preprocesser.methods.methods_nonseq_filling.custom_f)Parameters

**custom\_value** – `zenml.steps.preprocesser.standard_preprocesser.methods.methods_nonseq_filling.max_f`\(\)[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#zenml.steps.preprocesser.standard_preprocesser.methods.methods_nonseq_filling.max_f) `zenml.steps.preprocesser.standard_preprocesser.methods.methods_nonseq_filling.mean_f`\(\)[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#zenml.steps.preprocesser.standard_preprocesser.methods.methods_nonseq_filling.mean_f) `zenml.steps.preprocesser.standard_preprocesser.methods.methods_nonseq_filling.min_f`\(\)[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#zenml.steps.preprocesser.standard_preprocesser.methods.methods_nonseq_filling.min_f)

### zenml.steps.preprocesser.standard\_preprocesser.methods.methods\_transform module[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods.methods_transform)

 `zenml.steps.preprocesser.standard_preprocesser.methods.methods_transform.decode_and_reshape_image`\(_input\__\)[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#zenml.steps.preprocesser.standard_preprocesser.methods.methods_transform.decode_and_reshape_image)Parameters

**input** – bytes feature, bytes representation of input image `zenml.steps.preprocesser.standard_preprocesser.methods.methods_transform.load_binary_image`\(_image_\)[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#zenml.steps.preprocesser.standard_preprocesser.methods.methods_transform.load_binary_image)Parameters

**image** – `zenml.steps.preprocesser.standard_preprocesser.methods.methods_transform.one_hot_encode`\(_custom\_value_\)[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#zenml.steps.preprocesser.standard_preprocesser.methods.methods_transform.one_hot_encode)Parameters

**custom\_value** –

### zenml.steps.preprocesser.standard\_preprocesser.methods.standard\_methods module[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods.standard_methods)

 _class_ `zenml.steps.preprocesser.standard_preprocesser.methods.standard_methods.NonSeqFillingMethods`[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#zenml.steps.preprocesser.standard_preprocesser.methods.standard_methods.NonSeqFillingMethods)

Bases: [`zenml.utils.preprocessing_utils.MethodDescriptions`](../../../zenml.utils/#zenml.utils.preprocessing_utils.MethodDescriptions) `MODES` _= {'custom': \(&lt;function custom\_f&gt;, \['custom\_value'\]\), 'max': \(&lt;function max\_f&gt;, \[\]\), 'mean': \(&lt;function mean\_f&gt;, \[\]\), 'min': \(&lt;function min\_f&gt;, \[\]\)}_[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#zenml.steps.preprocesser.standard_preprocesser.methods.standard_methods.NonSeqFillingMethods.MODES) _class_ `zenml.steps.preprocesser.standard_preprocesser.methods.standard_methods.TransformMethods`[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#zenml.steps.preprocesser.standard_preprocesser.methods.standard_methods.TransformMethods)

Bases: [`zenml.utils.preprocessing_utils.MethodDescriptions`](../../../zenml.utils/#zenml.utils.preprocessing_utils.MethodDescriptions) `MODES` _= {'bucketize': \(&lt;function bucketize&gt;, \['num\_buckets'\]\), 'compute\_and\_apply\_vocabulary': \(&lt;function compute\_and\_apply\_vocabulary&gt;, \[\]\), 'hash\_strings': \(&lt;function hash\_strings&gt;, \['hash\_buckets'\]\), 'image\_reshape': \(&lt;function decode\_and\_reshape\_image&gt;, \[\]\), 'load\_binary\_image': \(&lt;function load\_binary\_image&gt;, \[\]\), 'ngrams': \(&lt;function ngrams&gt;, \['ngram\_range', 'separator'\]\), 'no\_transform': \(&lt;function TransformMethods.&lt;lambda&gt;&gt;, \[\]\), 'one\_hot\_encode': \(&lt;function one\_hot\_encode&gt;, \['depth'\]\), 'pca': \(&lt;function pca&gt;, \['output\_dim', 'dtype'\]\), 'scale\_by\_min\_max': \(&lt;function scale\_by\_min\_max&gt;, \['min', 'max'\]\), 'scale\_to\_0\_1': \(&lt;function scale\_to\_0\_1&gt;, \[\]\), 'scale\_to\_z\_score': \(&lt;function scale\_to\_z\_score&gt;, \[\]\), 'tfidf': \(&lt;function tfidf&gt;, \['vocab\_size'\]\)}_[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#zenml.steps.preprocesser.standard_preprocesser.methods.standard_methods.TransformMethods.MODES)

### Module contents[¶](zenml.steps.preprocesser.standard_preprocesser.methods.md#module-zenml.steps.preprocesser.standard_preprocesser.methods)

 [Back to top](zenml.steps.preprocesser.standard_preprocesser.methods.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


