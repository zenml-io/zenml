# Trainer

&lt;!DOCTYPE html&gt;

zenml.steps.trainer package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](./)
  * * [zenml.steps.trainer package](./)
      * [Subpackages](./#subpackages)
      * [Submodules](./#submodules)
      * [zenml.steps.trainer.base\_trainer module](./#module-zenml.steps.trainer.base_trainer)
      * [zenml.steps.trainer.utils module](./#module-zenml.steps.trainer.utils)
      * [Module contents](./#module-zenml.steps.trainer)
* [ « zenml.steps.t...](../zenml.steps.tokenizer.md)
* [ zenml.steps.t... »](zenml.steps.trainer.pytorch_trainers.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.steps.trainer.rst.txt)

## zenml.steps.trainer package[¶](./#zenml-steps-trainer-package)

### Subpackages[¶](./#subpackages)

* [zenml.steps.trainer.pytorch\_trainers package](zenml.steps.trainer.pytorch_trainers.md)
  * [Submodules](zenml.steps.trainer.pytorch_trainers.md#submodules)
  * [zenml.steps.trainer.pytorch\_trainers.torch\_base\_trainer module](zenml.steps.trainer.pytorch_trainers.md#module-zenml.steps.trainer.pytorch_trainers.torch_base_trainer)
  * [zenml.steps.trainer.pytorch\_trainers.torch\_ff\_trainer module](zenml.steps.trainer.pytorch_trainers.md#module-zenml.steps.trainer.pytorch_trainers.torch_ff_trainer)
  * [zenml.steps.trainer.pytorch\_trainers.utils module](zenml.steps.trainer.pytorch_trainers.md#module-zenml.steps.trainer.pytorch_trainers.utils)
  * [Module contents](zenml.steps.trainer.pytorch_trainers.md#module-zenml.steps.trainer.pytorch_trainers)
* [zenml.steps.trainer.tensorflow\_trainers package](zenml.steps.trainer.tensorflow_trainers.md)
  * [Submodules](zenml.steps.trainer.tensorflow_trainers.md#submodules)
  * [zenml.steps.trainer.tensorflow\_trainers.tf\_base\_trainer module](zenml.steps.trainer.tensorflow_trainers.md#module-zenml.steps.trainer.tensorflow_trainers.tf_base_trainer)
  * [zenml.steps.trainer.tensorflow\_trainers.tf\_ff\_trainer module](zenml.steps.trainer.tensorflow_trainers.md#module-zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer)
  * [Module contents](zenml.steps.trainer.tensorflow_trainers.md#module-zenml.steps.trainer.tensorflow_trainers)

### Submodules[¶](./#submodules)

### zenml.steps.trainer.base\_trainer module[¶](./#module-zenml.steps.trainer.base_trainer)

 _class_ `zenml.steps.trainer.base_trainer.BaseTrainerStep`\(_input\_patterns: Dict\[str, str\] = None_, _output\_patterns: Dict\[str, str\] = None_, _serving\_model\_dir: str = None_, _transform\_output: str = None_, _split\_mapping: Dict\[str, List\[str\]\] = None_, _\*\*kwargs_\)[¶](./#zenml.steps.trainer.base_trainer.BaseTrainerStep)

Bases: [`zenml.steps.base_step.BaseStep`](../#zenml.steps.base_step.BaseStep)

Base step interface for all Trainer steps. All of your code concerning model training should leverage subclasses of this class. `STEP_TYPE` _= 'trainer'_[¶](./#zenml.steps.trainer.base_trainer.BaseTrainerStep.STEP_TYPE) `input_fn`\(_file\_pattern: List\[str\]_, _tf\_transform\_output: tensorflow\_transform.output\_wrapper.TFTransformOutput_\)[¶](./#zenml.steps.trainer.base_trainer.BaseTrainerStep.input_fn)

Method for loading data from TFRecords saved to a location on disk. Override this method in subclasses to define your own custom data preparation flow.Parameters

* **file\_pattern** – File pattern matching saved TFRecords on disk.
* **tf\_transform\_output** – Output of the preceding Transform / Preprocessing component.

Returns

A tf.data.Dataset constructed from the input file

pattern and transform.

Return type

dataset _static_ `model_fn`\(_train\_dataset_, _eval\_dataset_\)[¶](./#zenml.steps.trainer.base_trainer.BaseTrainerStep.model_fn)

Method defining the training flow of the model. Override this in subclasses to define your own custom training flow.Parameters

* **train\_dataset** – tf.data.Dataset containing the training data.
* **eval\_dataset** – tf.data.Dataset containing the evaluation data.

Returns

A trained machine learning model.Return type

model `run_fn`\(\)[¶](./#zenml.steps.trainer.base_trainer.BaseTrainerStep.run_fn)

Method defining the control flow of the training process inside the TFX Trainer Component Executor. Override this method in subclasses to define your own custom training flow. `test_fn`\(_\*args_, _\*\*kwargs_\)[¶](./#zenml.steps.trainer.base_trainer.BaseTrainerStep.test_fn)

Optional method for defining a test flow of the model. The goal of this method is to give the user an interface to provide a testing function, where the results \(if given in the right format with features, labels and predictions\) will be ultimately saved to disk using an output artifact. Once defined, it allows the user to utilize the model agnostic evaluator in their training pipeline.

### zenml.steps.trainer.utils module[¶](./#module-zenml.steps.trainer.utils)

 `zenml.steps.trainer.utils.combine_batch_results`\(_x_\)[¶](./#zenml.steps.trainer.utils.combine_batch_results) `zenml.steps.trainer.utils.save_test_results`\(_results_, _output\_path_\)[¶](./#zenml.steps.trainer.utils.save_test_results) `zenml.steps.trainer.utils.to_serialized_examples`\(_instance_\) → tensorflow.core.example.example\_pb2.Example[¶](./#zenml.steps.trainer.utils.to_serialized_examples)

### Module contents[¶](./#module-zenml.steps.trainer)

 [Back to top](./)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


