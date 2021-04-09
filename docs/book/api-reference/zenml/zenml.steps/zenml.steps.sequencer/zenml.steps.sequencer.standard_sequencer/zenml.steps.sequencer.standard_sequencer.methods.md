# Methods

&lt;!DOCTYPE html&gt;

zenml.steps.sequencer.standard\_sequencer.methods package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.steps.sequencer.standard_sequencer.methods.md)
  * * [zenml.steps.sequencer.standard\_sequencer.methods package](zenml.steps.sequencer.standard_sequencer.methods.md)
      * [Submodules](zenml.steps.sequencer.standard_sequencer.methods.md#submodules)
      * [zenml.steps.sequencer.standard\_sequencer.methods.methods\_filling module](zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods.methods_filling)
      * [zenml.steps.sequencer.standard\_sequencer.methods.methods\_resampling module](zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods.methods_resampling)
      * [zenml.steps.sequencer.standard\_sequencer.methods.standard\_methods module](zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods.standard_methods)
      * [Module contents](zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods)
* [ « zenml.steps.s...](./)
* [ zenml.steps.s... »](../../zenml.steps.split.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.steps.sequencer.standard_sequencer.methods.rst.txt)

## zenml.steps.sequencer.standard\_sequencer.methods package[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml-steps-sequencer-standard-sequencer-methods-package)

### Submodules[¶](zenml.steps.sequencer.standard_sequencer.methods.md#submodules)

### zenml.steps.sequencer.standard\_sequencer.methods.methods\_filling module[¶](zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods.methods_filling)

 `zenml.steps.sequencer.standard_sequencer.methods.methods_filling.backwards_f`\(\)[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.methods_filling.backwards_f) `zenml.steps.sequencer.standard_sequencer.methods.methods_filling.custom_f`\(_custom\_value_\)[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.methods_filling.custom_f) `zenml.steps.sequencer.standard_sequencer.methods.methods_filling.forward_f`\(\)[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.methods_filling.forward_f) `zenml.steps.sequencer.standard_sequencer.methods.methods_filling.infer_default_value`\(_x_\)[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.methods_filling.infer_default_value) `zenml.steps.sequencer.standard_sequencer.methods.methods_filling.max_f`\(\)[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.methods_filling.max_f) `zenml.steps.sequencer.standard_sequencer.methods.methods_filling.mean_f`\(\)[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.methods_filling.mean_f) `zenml.steps.sequencer.standard_sequencer.methods.methods_filling.min_f`\(\)[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.methods_filling.min_f)

### zenml.steps.sequencer.standard\_sequencer.methods.methods\_resampling module[¶](zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods.methods_resampling)

 `zenml.steps.sequencer.standard_sequencer.methods.methods_resampling.get_output_dtype`\(_input\_dtype_, _method_, _params_\)[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.methods_resampling.get_output_dtype) `zenml.steps.sequencer.standard_sequencer.methods.methods_resampling.resample_mean`\(\)[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.methods_resampling.resample_mean) `zenml.steps.sequencer.standard_sequencer.methods.methods_resampling.resample_median`\(\)[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.methods_resampling.resample_median) `zenml.steps.sequencer.standard_sequencer.methods.methods_resampling.resample_mode`\(\)[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.methods_resampling.resample_mode) `zenml.steps.sequencer.standard_sequencer.methods.methods_resampling.resample_thresholding`\(_cond_, _c\_value_, _threshold_, _set\_value_\)[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.methods_resampling.resample_thresholding)

### zenml.steps.sequencer.standard\_sequencer.methods.standard\_methods module[¶](zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods.standard_methods)

 _class_ `zenml.steps.sequencer.standard_sequencer.methods.standard_methods.FillingMethods`[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.standard_methods.FillingMethods)

Bases: [`zenml.utils.preprocessing_utils.MethodDescriptions`](../../../zenml.utils/#zenml.utils.preprocessing_utils.MethodDescriptions) `MODES` _= {'backwards': \(&lt;function backwards\_f&gt;, \[\]\), 'custom': \(&lt;function custom\_f&gt;, \['custom\_value'\]\), 'forward': \(&lt;function forward\_f&gt;, \[\]\), 'max': \(&lt;function max\_f&gt;, \[\]\), 'mean': \(&lt;function mean\_f&gt;, \[\]\), 'min': \(&lt;function min\_f&gt;, \[\]\)}_[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.standard_methods.FillingMethods.MODES) _class_ `zenml.steps.sequencer.standard_sequencer.methods.standard_methods.ResamplingMethods`[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.standard_methods.ResamplingMethods)

Bases: [`zenml.utils.preprocessing_utils.MethodDescriptions`](../../../zenml.utils/#zenml.utils.preprocessing_utils.MethodDescriptions) `MODES` _= {'mean': \(&lt;function resample\_mean&gt;, \[\]\), 'median': \(&lt;function resample\_median&gt;, \[\]\), 'mode': \(&lt;function resample\_mode&gt;, \[\]\), 'threshold': \(&lt;function resample\_thresholding&gt;, \['cond', 'c\_value', 'threshold', 'set\_value'\]\)}_[¶](zenml.steps.sequencer.standard_sequencer.methods.md#zenml.steps.sequencer.standard_sequencer.methods.standard_methods.ResamplingMethods.MODES)

### Module contents[¶](zenml.steps.sequencer.standard_sequencer.methods.md#module-zenml.steps.sequencer.standard_sequencer.methods)

 [Back to top](zenml.steps.sequencer.standard_sequencer.methods.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


