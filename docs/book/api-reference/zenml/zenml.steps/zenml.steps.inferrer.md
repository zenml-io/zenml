# Inferrer

&lt;!DOCTYPE html&gt;

zenml.steps.inferrer package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.steps.inferrer.md)
  * * [zenml.steps.inferrer package](zenml.steps.inferrer.md)
      * [Submodules](zenml.steps.inferrer.md#submodules)
      * [zenml.steps.inferrer.base\_inferrer\_step module](zenml.steps.inferrer.md#module-zenml.steps.inferrer.base_inferrer_step)
      * [zenml.steps.inferrer.inference\_file\_writer\_step module](zenml.steps.inferrer.md#module-zenml.steps.inferrer.inference_file_writer_step)
      * [zenml.steps.inferrer.tensorflow\_inferrer\_step module](zenml.steps.inferrer.md#module-zenml.steps.inferrer.tensorflow_inferrer_step)
      * [Module contents](zenml.steps.inferrer.md#module-zenml.steps.inferrer)
* [ « zenml.steps.e...](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/zenml.steps.evaluator.html)
* [ zenml.steps.p... »](zenml.steps.preprocesser/)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.steps.inferrer.rst.txt)

## zenml.steps.inferrer package[¶](zenml.steps.inferrer.md#zenml-steps-inferrer-package)

### Submodules[¶](zenml.steps.inferrer.md#submodules)

### zenml.steps.inferrer.base\_inferrer\_step module[¶](zenml.steps.inferrer.md#module-zenml.steps.inferrer.base_inferrer_step)

 _class_ `zenml.steps.inferrer.base_inferrer_step.BaseInferrer`\(_labels: List\[str\]_, _\*\*kwargs_\)[¶](zenml.steps.inferrer.md#zenml.steps.inferrer.base_inferrer_step.BaseInferrer)

Bases: [`zenml.steps.base_step.BaseStep`](./#zenml.steps.base_step.BaseStep)

Base inferrer class. This step is responsible for inference \(batch\). `get_labels`\(\)[¶](zenml.steps.inferrer.md#zenml.steps.inferrer.base_inferrer_step.BaseInferrer.get_labels) `set_output_uri`\(_output\_uri_\)[¶](zenml.steps.inferrer.md#zenml.steps.inferrer.base_inferrer_step.BaseInferrer.set_output_uri) `write_inference_results`\(\)[¶](zenml.steps.inferrer.md#zenml.steps.inferrer.base_inferrer_step.BaseInferrer.write_inference_results)

### zenml.steps.inferrer.inference\_file\_writer\_step module[¶](zenml.steps.inferrer.md#module-zenml.steps.inferrer.inference_file_writer_step)

 _class_ `zenml.steps.inferrer.inference_file_writer_step.FileWriterInferrer`\(_labels: List\[str\]_, _output\_path: str_, _output\_ext: str = '.csv'_, _num\_shards: int = 0_, _\*\*kwargs_\)[¶](zenml.steps.inferrer.md#zenml.steps.inferrer.inference_file_writer_step.FileWriterInferrer)

Bases: [`zenml.steps.inferrer.base_inferrer_step.BaseInferrer`](zenml.steps.inferrer.md#zenml.steps.inferrer.base_inferrer_step.BaseInferrer)

File Writer Inferrer step, writing inference results to a text file. `get_destination`\(\)[¶](zenml.steps.inferrer.md#zenml.steps.inferrer.inference_file_writer_step.FileWriterInferrer.get_destination)

### zenml.steps.inferrer.tensorflow\_inferrer\_step module[¶](zenml.steps.inferrer.md#module-zenml.steps.inferrer.tensorflow_inferrer_step)

 _class_ `zenml.steps.inferrer.tensorflow_inferrer_step.TensorflowInferrer`\(_labels: List\[str\]_, _\*\*kwargs_\)[¶](zenml.steps.inferrer.md#zenml.steps.inferrer.tensorflow_inferrer_step.TensorflowInferrer)

Bases: [`zenml.steps.inferrer.base_inferrer_step.BaseInferrer`](zenml.steps.inferrer.md#zenml.steps.inferrer.base_inferrer_step.BaseInferrer)

Tensorflow Inferrer.

### Module contents[¶](zenml.steps.inferrer.md#module-zenml.steps.inferrer)

 [Back to top](zenml.steps.inferrer.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


