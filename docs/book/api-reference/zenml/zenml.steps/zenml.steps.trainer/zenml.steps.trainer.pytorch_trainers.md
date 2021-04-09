# Pytorch trainers

&lt;!DOCTYPE html&gt;

zenml.steps.trainer.pytorch\_trainers package — ZenML documentation  [ZenML](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)

*  [Site](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/index.html)
  * Contents:
    * [zenml](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/modules.html)
*  [Page](zenml.steps.trainer.pytorch_trainers.md)
  * * [zenml.steps.trainer.pytorch\_trainers package](zenml.steps.trainer.pytorch_trainers.md)
      * [Submodules](zenml.steps.trainer.pytorch_trainers.md#submodules)
      * [zenml.steps.trainer.pytorch\_trainers.torch\_base\_trainer module](zenml.steps.trainer.pytorch_trainers.md#module-zenml.steps.trainer.pytorch_trainers.torch_base_trainer)
      * [zenml.steps.trainer.pytorch\_trainers.torch\_ff\_trainer module](zenml.steps.trainer.pytorch_trainers.md#module-zenml.steps.trainer.pytorch_trainers.torch_ff_trainer)
      * [zenml.steps.trainer.pytorch\_trainers.utils module](zenml.steps.trainer.pytorch_trainers.md#module-zenml.steps.trainer.pytorch_trainers.utils)
      * [Module contents](zenml.steps.trainer.pytorch_trainers.md#module-zenml.steps.trainer.pytorch_trainers)
* [ « zenml.steps.t...](./)
* [ zenml.steps.t... »](zenml.steps.trainer.tensorflow_trainers.md)
*  [Source](https://github.com/maiot-io/zenml/tree/e2cf3eb9599a3b31a4ee646048d90127dfdbb178/docs/sphinx_docs/_build/html/_sources/zenml.steps.trainer.pytorch_trainers.rst.txt)

## zenml.steps.trainer.pytorch\_trainers package[¶](zenml.steps.trainer.pytorch_trainers.md#zenml-steps-trainer-pytorch-trainers-package)

### Submodules[¶](zenml.steps.trainer.pytorch_trainers.md#submodules)

### zenml.steps.trainer.pytorch\_trainers.torch\_base\_trainer module[¶](zenml.steps.trainer.pytorch_trainers.md#module-zenml.steps.trainer.pytorch_trainers.torch_base_trainer)

 _class_ `zenml.steps.trainer.pytorch_trainers.torch_base_trainer.TorchBaseTrainerStep`\(_input\_patterns: Dict\[str, str\] = None_, _output\_patterns: Dict\[str, str\] = None_, _serving\_model\_dir: str = None_, _transform\_output: str = None_, _split\_mapping: Dict\[str, List\[str\]\] = None_, _\*\*kwargs_\)[¶](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.torch_base_trainer.TorchBaseTrainerStep)

Bases: [`zenml.steps.trainer.base_trainer.BaseTrainerStep`](./#zenml.steps.trainer.base_trainer.BaseTrainerStep)

Base class for all PyTorch based trainer steps. All pytorch based trainings should use this as the base class. An example is available with torch\_ff\_trainer.FeedForwardTrainer.

### zenml.steps.trainer.pytorch\_trainers.torch\_ff\_trainer module[¶](zenml.steps.trainer.pytorch_trainers.md#module-zenml.steps.trainer.pytorch_trainers.torch_ff_trainer)

 _class_ `zenml.steps.trainer.pytorch_trainers.torch_ff_trainer.BinaryClassifier`[¶](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.torch_ff_trainer.BinaryClassifier)

Bases: `torch.nn.modules.module.Module` `forward`\(_inputs_\)[¶](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.torch_ff_trainer.BinaryClassifier.forward)

Defines the computation performed at every call.

Should be overridden by all subclasses.

Note

Although the recipe for forward pass needs to be defined within this function, one should call the `Module` instance afterwards instead of this since the former takes care of running the registered hooks while the latter silently ignores them. `training`_: bool_[¶](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.torch_ff_trainer.BinaryClassifier.training) _class_ `zenml.steps.trainer.pytorch_trainers.torch_ff_trainer.FeedForwardTrainer`\(_batch\_size: int = 32_, _lr: float = 0.0001_, _epochs: int = 10_, _dropout\_chance: int = 0.2_, _loss: str = 'mse'_, _metrics: List\[str\] = None_, _hidden\_layers: List\[int\] = None_, _hidden\_activation: str = 'relu'_, _last\_activation: str = 'sigmoid'_, _input\_units: int = 8_, _output\_units: int = 1_, _\*\*kwargs_\)[¶](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.torch_ff_trainer.FeedForwardTrainer)

Bases: [`zenml.steps.trainer.pytorch_trainers.torch_base_trainer.TorchBaseTrainerStep`](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.torch_base_trainer.TorchBaseTrainerStep) `input_fn`\(_file\_patterns: List\[str\]_\)[¶](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.torch_ff_trainer.FeedForwardTrainer.input_fn)

Method for loading data from TFRecords saved to a location on disk. Override this method in subclasses to define your own custom data preparation flow.Parameters

* **file\_pattern** – File pattern matching saved TFRecords on disk.
* **tf\_transform\_output** – Output of the preceding Transform / Preprocessing component.

Returns

A tf.data.Dataset constructed from the input file

pattern and transform.

Return type

dataset `model_fn`\(_train\_dataset_, _eval\_dataset_\)[¶](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.torch_ff_trainer.FeedForwardTrainer.model_fn)

Method defining the training flow of the model. Override this in subclasses to define your own custom training flow.Parameters

* **train\_dataset** – tf.data.Dataset containing the training data.
* **eval\_dataset** – tf.data.Dataset containing the evaluation data.

Returns

A trained machine learning model.Return type

model `run_fn`\(\)[¶](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.torch_ff_trainer.FeedForwardTrainer.run_fn)

Method defining the control flow of the training process inside the TFX Trainer Component Executor. Override this method in subclasses to define your own custom training flow. `test_fn`\(_model_, _dataset_\)[¶](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.torch_ff_trainer.FeedForwardTrainer.test_fn)

Optional method for defining a test flow of the model. The goal of this method is to give the user an interface to provide a testing function, where the results \(if given in the right format with features, labels and predictions\) will be ultimately saved to disk using an output artifact. Once defined, it allows the user to utilize the model agnostic evaluator in their training pipeline. `zenml.steps.trainer.pytorch_trainers.torch_ff_trainer.binary_acc`\(_y\_pred_, _y\_test_\)[¶](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.torch_ff_trainer.binary_acc)

### zenml.steps.trainer.pytorch\_trainers.utils module[¶](zenml.steps.trainer.pytorch_trainers.md#module-zenml.steps.trainer.pytorch_trainers.utils)

 _class_ `zenml.steps.trainer.pytorch_trainers.utils.TFRecordTorchDataset`\(_file\_pattern_, _spec_\)[¶](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.utils.TFRecordTorchDataset)

Bases: `torch.utils.data.dataset.IterableDataset`, `abc.ABC` `zenml.steps.trainer.pytorch_trainers.utils.create_tf_dataset`\(_file\_pattern_, _spec_, _num\_epochs=1_, _shuffle=False_, _shuffle\_seed=None_, _shuffle\_buffer\_size=None_, _reader\_num\_threads=None_, _prefetch\_buffer\_size=None_\)[¶](zenml.steps.trainer.pytorch_trainers.md#zenml.steps.trainer.pytorch_trainers.utils.create_tf_dataset)

### Module contents[¶](zenml.steps.trainer.pytorch_trainers.md#module-zenml.steps.trainer.pytorch_trainers)

 [Back to top](zenml.steps.trainer.pytorch_trainers.md)

 © Copyright 2021, maiot GmbH.  
 Created using [Sphinx](http://sphinx-doc.org/) 3.3.1.  


