# Tensorflow trainers

&lt;!DOCTYPE html&gt;

zenml.steps.trainer.tensorflow\_trainers package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.steps.trainer.tensorflow_trainers.md)
  * * [zenml.steps.trainer.tensorflow\_trainers package](zenml.steps.trainer.tensorflow_trainers.md)
      * [Submodules](zenml.steps.trainer.tensorflow_trainers.md#submodules)
      * [zenml.steps.trainer.tensorflow\_trainers.tf\_base\_trainer module](zenml.steps.trainer.tensorflow_trainers.md#module-zenml.steps.trainer.tensorflow_trainers.tf_base_trainer)
      * [zenml.steps.trainer.tensorflow\_trainers.tf\_ff\_trainer module](zenml.steps.trainer.tensorflow_trainers.md#module-zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer)
      * [Module contents](zenml.steps.trainer.tensorflow_trainers.md#module-zenml.steps.trainer.tensorflow_trainers)
* [ « zenml.steps.t...](zenml.steps.trainer.pytorch_trainers.md)
* [ zenml.utils package »](../../zenml.utils/)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.steps.trainer.tensorflow_trainers.rst.txt)

## zenml.steps.trainer.tensorflow\_trainers package[¶](zenml.steps.trainer.tensorflow_trainers.md#zenml-steps-trainer-tensorflow-trainers-package)

### Submodules[¶](zenml.steps.trainer.tensorflow_trainers.md#submodules)

### zenml.steps.trainer.tensorflow\_trainers.tf\_base\_trainer module[¶](zenml.steps.trainer.tensorflow_trainers.md#module-zenml.steps.trainer.tensorflow_trainers.tf_base_trainer)

 _class_ `zenml.steps.trainer.tensorflow_trainers.tf_base_trainer.TFBaseTrainerStep`\(_input\_patterns: Dict\[str, str\] = None_, _output\_patterns: Dict\[str, str\] = None_, _serving\_model\_dir: str = None_, _transform\_output: str = None_, _split\_mapping: Dict\[str, List\[str\]\] = None_, _\*\*kwargs_\)[¶](zenml.steps.trainer.tensorflow_trainers.md#zenml.steps.trainer.tensorflow_trainers.tf_base_trainer.TFBaseTrainerStep)

Bases: [`zenml.steps.trainer.base_trainer.BaseTrainerStep`](./#zenml.steps.trainer.base_trainer.BaseTrainerStep)

Base class for all Tensorflow-based trainer steps. All tensorflow based trainings should use this as the base class. An example is available with tf\_ff\_trainer.FeedForwardTrainer.

### zenml.steps.trainer.tensorflow\_trainers.tf\_ff\_trainer module[¶](zenml.steps.trainer.tensorflow_trainers.md#module-zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer)

 _class_ `zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer`\(_batch\_size: int = 8_, _lr: float = 0.001_, _epochs: int = 1_, _dropout\_chance: int = 0.2_, _loss: str = 'mse'_, _metrics: List\[str\] = None_, _hidden\_layers: List\[int\] = None_, _hidden\_activation: str = 'relu'_, _last\_activation: str = 'sigmoid'_, _output\_units: int = 1_, _\*\*kwargs_\)[¶](zenml.steps.trainer.tensorflow_trainers.md#zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer)

Bases: [`zenml.steps.trainer.tensorflow_trainers.tf_base_trainer.TFBaseTrainerStep`](zenml.steps.trainer.tensorflow_trainers.md#zenml.steps.trainer.tensorflow_trainers.tf_base_trainer.TFBaseTrainerStep)

Basic Feedforward Neural Network trainer. This step serves as an example of how to define your training logic to integrate well with TFX and Tensorflow Serving. `input_fn`\(_file\_pattern: List\[str\]_\)[¶](zenml.steps.trainer.tensorflow_trainers.md#zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer.input_fn)

Feedforward input\_fn for loading data from TFRecords saved to a location on disk.Parameters

**file\_pattern** – File pattern matching saved TFRecords on disk.Returns

tf.data.Dataset created out of the input files.Return type

dataset `model_fn`\(_train\_dataset: tensorflow.python.data.ops.dataset\_ops.DatasetV2_, _eval\_dataset: tensorflow.python.data.ops.dataset\_ops.DatasetV2_\)[¶](zenml.steps.trainer.tensorflow_trainers.md#zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer.model_fn)

Function defining the training flow of the feedforward neural network model.Parameters

* **train\_dataset** – tf.data.Dataset containing the training data.
* **eval\_dataset** – tf.data.Dataset containing the evaluation data.

Returns

A trained feedforward neural network model.Return type

model `run_fn`\(\)[¶](zenml.steps.trainer.tensorflow_trainers.md#zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer.run_fn)

Method defining the control flow of the training process inside the TFX Trainer Component Executor. Override this method in subclasses to define your own custom training flow. `test_fn`\(_model_, _dataset_\)[¶](zenml.steps.trainer.tensorflow_trainers.md#zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer.FeedForwardTrainer.test_fn)

Optional method for defining a test flow of the model. The goal of this method is to give the user an interface to provide a testing function, where the results \(if given in the right format with features, labels and predictions\) will be ultimately saved to disk using an output artifact. Once defined, it allows the user to utilize the model agnostic evaluator in their training pipeline.

### Module contents[¶](zenml.steps.trainer.tensorflow_trainers.md#module-zenml.steps.trainer.tensorflow_trainers)

 [Back to top](zenml.steps.trainer.tensorflow_trainers.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


